"""CoreLink - Nosana node discovery and status probe."""

import json
import os
import shutil
import subprocess
import threading
import time


class NosanaProbe:
    """Discovers Nosana containers and queries blockchain status.

    Runs a Node.js probe script as a subprocess, caches results in a
    thread-safe dict.  Designed to be called from an eventlet background
    task every 30 seconds.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._state = {"nodes": [], "error": None, "last_probe": None}

        # Check prerequisites
        self._node_bin = shutil.which("node")
        self._probe_script = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "nosana", "nosana_probe.mjs"
        )
        self._docker_sock = "/var/run/docker.sock"

        self.enabled = True
        if not self._node_bin:
            self._state["error"] = "Node.js not found"
            self.enabled = False
        elif not os.path.isfile(self._probe_script):
            self._state["error"] = "Probe script not found"
            self.enabled = False
        elif not os.path.exists(self._docker_sock):
            self._state["error"] = "Docker socket not mounted"
            self.enabled = False

    def collect(self):
        """Run the probe and update cached state.  Safe to call from any thread."""
        if not self.enabled:
            return

        try:
            result = subprocess.run(
                [self._node_bin, self._probe_script],
                capture_output=True,
                text=True,
                timeout=45,
                cwd=os.path.dirname(self._probe_script),
            )

            stdout = result.stdout.strip()
            if not stdout:
                with self._lock:
                    self._state = {
                        "nodes": [],
                        "error": "Probe returned no output",
                        "last_probe": time.strftime("%H:%M:%S"),
                    }
                return

            data = json.loads(stdout)
            with self._lock:
                self._state = {
                    "nodes": data.get("nodes", []),
                    "error": data.get("error"),
                    "last_probe": time.strftime("%H:%M:%S"),
                }

        except subprocess.TimeoutExpired:
            with self._lock:
                self._state["error"] = "Probe timed out"
                self._state["last_probe"] = time.strftime("%H:%M:%S")

        except json.JSONDecodeError as exc:
            with self._lock:
                self._state["error"] = "Invalid JSON: %s" % exc
                self._state["last_probe"] = time.strftime("%H:%M:%S")

        except Exception as exc:
            with self._lock:
                self._state["error"] = str(exc)
                self._state["last_probe"] = time.strftime("%H:%M:%S")

    def get_state(self):
        """Return cached probe state (thread-safe, instant read)."""
        with self._lock:
            return dict(self._state)
