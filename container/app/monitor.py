"""CoreLink - Application resource monitor.

Collects app-only metrics (CPU, RAM, network, disk) using /proc and /sys.
No external dependencies — stdlib only.
"""

import os
import time


class AppMonitor:
    """Tracks CoreLink container resource usage via delta-based sampling."""

    def __init__(self):
        self._prev_cpu_app = 0
        self._prev_cpu_total = 0
        self._prev_io_net = 0
        self._prev_time = 0.0
        self._link_speed = self._detect_link_speed()
        self._metrics = {
            "cpu": 0.0,
            "ram": 0.0,
            "net_mbps": 0.0,
            "link_speed": self._link_speed,
            "disk": 0.0,
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

    def get_metrics(self):
        """Return a copy of the latest metrics dict."""
        return dict(self._metrics)

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
        return round(100.0 * d_app / d_total, 1)

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
        return round(100.0 * mem_bytes / mem_total, 1)

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
        return round(mbps, 1)

    # ------------------------------------------------------------------
    # Link speed — first physical up interface
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_link_speed():
        """Auto-detect negotiated link speed (Mbps) of first physical NIC."""
        try:
            net_dir = "/sys/class/net"
            for iface in sorted(os.listdir(net_dir)):
                # Skip loopback and virtual interfaces
                if iface == "lo" or iface.startswith("veth") or iface.startswith("docker") or iface.startswith("br-"):
                    continue
                # Must be up
                try:
                    with open(os.path.join(net_dir, iface, "operstate")) as f:
                        if f.read().strip() != "up":
                            continue
                except IOError:
                    continue
                # Read speed
                try:
                    with open(os.path.join(net_dir, iface, "speed")) as f:
                        speed = int(f.read().strip())
                    if speed > 0:
                        return speed
                except (IOError, ValueError):
                    continue
        except OSError:
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
