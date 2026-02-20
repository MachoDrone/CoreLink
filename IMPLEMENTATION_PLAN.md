# CoreLink Implementation Plan

## Current Architecture

CoreLink uses a two-layer design:

- **Host layer** (`corelink.py`): Pure Python 3.8+ stdlib script (no pip). Handles prerequisite checks (Ubuntu 20–24, nvidia-smi, nvidia-ctk, Docker), Docker image builds, container lifecycle, and TLS certificate management via a local CA (`~/.corelink/ca/`). Supports curl-pipe execution by detecting `/dev/fd/*` and downloading container files from GitHub.
- **Container layer** (`container/`): Based on `nvidia/cuda:12.2.0-base-ubuntu22.04`. Runs a Flask + Flask-SocketIO (eventlet) web console with PAM authentication against the host OS, GPU discovery via nvidia-smi and sysfs, a self-monitoring module, and a UDP gossip protocol for LAN-wide cluster state.

Key components inside the container:
- `server.py` — Flask app, Socket.IO real-time push, background monitor loop
- `auth.py` — PAM authentication + Flask-Login sessions (8-hour lifetime)
- `gossip.py` — UDP multicast heartbeats (239.77.77.77:47100), unicast anti-entropy (47101), peer reaper
- `gpu.py` — GPU discovery and PCIe bottleneck detection via sysfs
- `monitor.py` — App-only CPU/RAM/network/disk metrics + NTP drift verification
- `app.js` — Frontend: Socket.IO client, cluster table rendering, connection status

Container runs with `--network host` (required for UDP multicast), bind-mounts `/etc/passwd`, `/etc/shadow`, `/etc/pam.d` read-only for PAM, and uses a named volume `corelink-data` for persistent state.

## What's Built (through v0.01.7)

| Version | Highlights |
|---------|-----------|
| v0.00.1 | Project scaffolding |
| v0.00.2 | Initial working implementation — host launcher, Docker container, web console, PAM auth, gossip protocol, GPU table |
| v0.00.3 | Column renames, UTC suffix on timestamps, table text shrink |
| v0.00.4 | Local CA for warning-free HTTPS across cluster |
| v0.00.5 | UI polish: strip "NVIDIA " prefix, hostname in connection badge, 0.7rem sizing |
| v0.00.6 | Self-monitoring module (`monitor.py`): CPU, RAM, network, disk — all stdlib |
| v0.00.7 | AppComm column (per-node net kbps via gossip), LAN Saturation aggregate |
| v0.00.8 | Fleet status line, NIC column (color-coded link speed), Time Synch column, ethtool integration |
| v0.00.9 | Real NTP verification (SNTP client), replaces browser-based time sync, 2s threshold |
| v0.01.0 | Eventlet WebSocket backend — fixes 500 error, reduces overhead |
| v0.01.1 | GPU Limit column (PCIe gen x width) from nvidia-smi |
| v0.01.2 | Fix GPU Limit to use sysfs for true slot-limited bottleneck detection |
| v0.01.3 | Fix gossip anti-entropy replaying stale data after node restart |
| v0.01.4 | Remove third-party data relay from anti-entropy — only send self data |
| v0.01.5 | Fix versioning scheme, correct all historical versions, add permanent versioning rules |
| v0.01.6 | Rename columns (Bottleneck, NTP Sync, CoreLink I/O), add info tooltip icons to all table headers |
| v0.01.7 | Fix gossip thread starvation from eventlet; UDP buffer increase, faster select loop, push loop yield; relax NTP threshold to 5s |

## Roadmap / Next Steps

- **Populate "Reserved" tab** — add future functionality to the currently placeholder tab
- **More GPU metrics** — temperature, utilization, memory usage in the cluster table
- **Table sorting/filtering** — allow users to sort and filter the GPU table columns
- **Node uptime / last-seen column** — show how long each node has been online or when it was last seen
- **Per-node monitor metrics in cluster table** — show each node's CPU/RAM/network/disk alongside its GPUs
- **Collapse repeated columns for multi-GPU nodes** — use rowspan or first-row-only rendering for PC/Timestamp columns
