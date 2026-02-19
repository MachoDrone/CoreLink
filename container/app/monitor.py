"""CoreLink - Application resource monitor.

Collects app-only metrics (CPU, RAM, network, disk) using /proc and /sys.
No external dependencies — stdlib only.
"""

import os
import re
import socket
import struct
import subprocess
import time


class AppMonitor:
    """Tracks CoreLink container resource usage via delta-based sampling."""

    def __init__(self):
        self._prev_cpu_app = 0
        self._prev_cpu_total = 0
        self._prev_io_net = 0
        self._prev_time = 0.0
        self._default_iface = self._get_default_iface()
        self._link_speed = self._detect_link_speed()
        self._link_speed_max = self._detect_max_speed(self._default_iface)
        # Graceful degradation: if ethtool failed but negotiated > 0, treat as max
        if self._link_speed_max == 0 and self._link_speed > 0:
            self._link_speed_max = self._link_speed
        self._ntp_drift = self._query_ntp()
        self._ntp_last_check = time.monotonic()
        self._ntp_interval = 60
        self._metrics = {
            "cpu": 0.0,
            "ram": 0.0,
            "net_mbps": 0.0,
            "link_speed": self._link_speed,
            "link_speed_max": self._link_speed_max,
            "disk": 0.0,
            "ntp_drift": self._ntp_drift,
        }
        # Prime the deltas with an initial read
        self._read_cpu()
        self._read_net_io()
        self._prev_time = time.monotonic()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def collect(self):
        """Sample all metrics (call every ~3s from the push loop)."""
        now = time.monotonic()
        dt = now - self._prev_time if self._prev_time else 0.0
        self._prev_time = now

        self._metrics["cpu"] = self._calc_cpu()
        self._metrics["ram"] = self._calc_ram()
        self._metrics["net_mbps"] = self._calc_net(dt)
        self._metrics["disk"] = self._calc_disk()

        if now - self._ntp_last_check >= self._ntp_interval:
            self._ntp_drift = self._query_ntp()
            self._ntp_last_check = now
        self._metrics["ntp_drift"] = self._ntp_drift

    def get_metrics(self):
        """Return a copy of the latest metrics dict."""
        return dict(self._metrics)

    # ------------------------------------------------------------------
    # NTP — query pool.ntp.org for local clock drift
    # ------------------------------------------------------------------

    @staticmethod
    def _query_ntp(server="pool.ntp.org", timeout=2):
        """Query NTP server, return local clock drift in seconds or None."""
        NTP_EPOCH = 2208988800  # 1900-01-01 to 1970-01-01
        try:
            msg = b'\x1b' + 47 * b'\0'  # NTP v3 client request
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(timeout)
            sock.sendto(msg, (server, 123))
            data, _ = sock.recvfrom(1024)
            sock.close()
            if len(data) < 48:
                return None
            # Transmit timestamp: seconds since 1900
            ntp_secs = struct.unpack('!I', data[40:44])[0]
            ntp_time = ntp_secs - NTP_EPOCH
            return round(time.time() - ntp_time, 3)
        except Exception:
            return None

    # ------------------------------------------------------------------
    # CPU — app threads vs total system ticks
    # ------------------------------------------------------------------

    def _read_cpu(self):
        """Return (app_ticks, total_ticks)."""
        app_ticks = 0
        try:
            task_dir = "/proc/1/task"
            for tid in os.listdir(task_dir):
                stat_path = os.path.join(task_dir, tid, "stat")
                try:
                    with open(stat_path) as f:
                        parts = f.read().split()
                    # utime=13, stime=14 (0-indexed)
                    app_ticks += int(parts[13]) + int(parts[14])
                except (IOError, IndexError, ValueError):
                    continue
        except (IOError, OSError):
            pass

        total_ticks = 0
        try:
            with open("/proc/stat") as f:
                line = f.readline()
            # cpu  user nice system idle iowait irq softirq steal ...
            fields = line.split()[1:]
            total_ticks = sum(int(x) for x in fields)
        except (IOError, ValueError):
            pass

        return app_ticks, total_ticks

    def _calc_cpu(self):
        """Delta-based CPU % for the app."""
        app, total = self._read_cpu()
        d_app = app - self._prev_cpu_app
        d_total = total - self._prev_cpu_total
        self._prev_cpu_app = app
        self._prev_cpu_total = total
        if d_total <= 0:
            return 0.0
        return round(100.0 * d_app / d_total, 2)

    # ------------------------------------------------------------------
    # RAM — cgroup memory vs host MemTotal
    # ------------------------------------------------------------------

    def _calc_ram(self):
        """Container memory as % of host MemTotal."""
        mem_bytes = 0
        # cgroup v2
        try:
            with open("/sys/fs/cgroup/memory.current") as f:
                mem_bytes = int(f.read().strip())
        except (IOError, ValueError):
            # cgroup v1 fallback
            try:
                with open("/sys/fs/cgroup/memory/memory.usage_in_bytes") as f:
                    mem_bytes = int(f.read().strip())
            except (IOError, ValueError):
                return 0.0

        mem_total = 0
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        # Value is in kB
                        mem_total = int(line.split()[1]) * 1024
                        break
        except (IOError, ValueError):
            return 0.0

        if mem_total <= 0:
            return 0.0
        return round(100.0 * mem_bytes / mem_total, 2)

    # ------------------------------------------------------------------
    # Network — delta of non-disk I/O from /proc/1/io
    # ------------------------------------------------------------------

    def _read_net_io(self):
        """Return approximate network bytes from /proc/1/io.

        (rchar - read_bytes) + (wchar - write_bytes) captures non-disk I/O,
        which is predominantly network traffic for this app.
        """
        try:
            with open("/proc/1/io") as f:
                vals = {}
                for line in f:
                    key, val = line.split(":", 1)
                    vals[key.strip()] = int(val.strip())
            rchar = vals.get("rchar", 0)
            wchar = vals.get("wchar", 0)
            read_bytes = vals.get("read_bytes", 0)
            write_bytes = vals.get("write_bytes", 0)
            return (rchar - read_bytes) + (wchar - write_bytes)
        except (IOError, ValueError, KeyError):
            return 0

    def _calc_net(self, dt):
        """Network throughput in Mbps (megabits/sec) over the sample interval."""
        current = self._read_net_io()
        delta = current - self._prev_io_net
        self._prev_io_net = current
        if dt <= 0 or delta <= 0:
            return 0.0
        bytes_per_sec = delta / dt
        mbps = (bytes_per_sec * 8) / 1_000_000
        return round(mbps, 3)

    # ------------------------------------------------------------------
    # Link speed — default-route interface
    # ------------------------------------------------------------------

    @staticmethod
    def _get_default_iface():
        """Return the interface carrying the default route (cluster traffic)."""
        try:
            with open("/proc/net/route") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2 and parts[1] == "00000000":
                        return parts[0]
        except (IOError, OSError):
            pass
        return None

    def _detect_link_speed(self):
        """Auto-detect negotiated link speed (Mbps) of default-route NIC."""
        iface = self._default_iface
        if not iface:
            return 0
        try:
            with open("/sys/class/net/%s/speed" % iface) as f:
                speed = int(f.read().strip())
            if speed > 0:
                return speed
        except (IOError, ValueError, OSError):
            pass
        return 0

    @staticmethod
    def _detect_max_speed(iface):
        """Detect max supported link speed (Mbps) via ethtool."""
        if not iface:
            return 0
        try:
            result = subprocess.run(
                ["ethtool", iface],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode != 0:
                return 0
            speeds = re.findall(r"(\d+)base", result.stdout)
            if speeds:
                return max(int(s) for s in speeds)
        except (OSError, subprocess.TimeoutExpired, ValueError):
            pass
        return 0

    # ------------------------------------------------------------------
    # Disk — app files as % of root filesystem
    # ------------------------------------------------------------------

    @staticmethod
    def _calc_disk():
        """Sum of /app + /data files as % of root filesystem capacity."""
        app_bytes = 0
        for scan_dir in ("/app", "/data"):
            try:
                for dirpath, _dirnames, filenames in os.walk(scan_dir):
                    for fname in filenames:
                        try:
                            app_bytes += os.path.getsize(
                                os.path.join(dirpath, fname)
                            )
                        except OSError:
                            continue
            except OSError:
                continue

        try:
            st = os.statvfs("/")
            total = st.f_frsize * st.f_blocks
        except OSError:
            return 0.0

        if total <= 0:
            return 0.0
        return round(100.0 * app_bytes / total, 2)
