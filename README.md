# CoreLink

GPU Cluster Communication Framework — v0.00.1

CoreLink discovers NVIDIA GPUs on every machine in your LAN, shares the
information via a lightweight gossip protocol, and presents it through a
secure HTTPS web console.

## Prerequisites

| Requirement | Details |
|---|---|
| **OS** | Ubuntu 20.04, 22.04, or 24.04 (Desktop, Server, or Minimal) |
| **GPU** | One or more NVIDIA GPUs visible via `nvidia-smi` |
| **Container Toolkit** | [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) |
| **Docker** | Docker Engine (user must be in `docker` group or run with `sudo`) |

No third-party Python packages are required on the host — the script uses
only the Python 3 standard library.  All third-party dependencies run
inside the Docker container.

## Quick Start

### From a cloned repo

```bash
git clone https://github.com/MachoDrone/CoreLink.git
cd CoreLink
python3 corelink.py --start
```

### One-liner (no clone needed)

```bash
python3 <(curl -sL https://raw.githubusercontent.com/MachoDrone/CoreLink/main/corelink.py) --start
# or
python3 <(wget -qO- https://raw.githubusercontent.com/MachoDrone/CoreLink/main/corelink.py) --start
```

Then open **https://\<hostname\>** in a browser and log in with your
Ubuntu username and password.

## Usage

```
python3 corelink.py [options]

Options:
  --check          Check prerequisites only
  --build          Build the Docker image
  --start          Build (if needed) and start CoreLink
  --stop           Stop CoreLink
  --restart        Restart CoreLink
  --status         Show container status
  --logs           Show container logs
  --logs-follow    Follow container logs (live)
  --port PORT      HTTPS port (default: 443)
  --version        Show version
```

## How It Works

1. **corelink.py** verifies host prerequisites, builds the `corelink`
   Docker image, and starts the container with `--gpus all` and
   `--network host`.

2. Inside the container, a **Flask** web application serves an HTTPS
   console.  Authentication is handled via **PAM** against the host's
   `/etc/passwd` and `/etc/shadow` (bind-mounted read-only).

3. A **gossip protocol** (UDP multicast on `239.77.77.77:47100`)
   broadcasts each node's hostname, GPU IDs, GPU models, and local
   timestamp.  Anti-entropy digest exchanges ensure all nodes converge
   even if some multicast packets are lost.

4. The web console's **Test** tab displays a live-updating table of
   every discovered node and its GPUs.  Updates arrive via WebSocket
   (Socket.IO) every 3 seconds.

## Network Requirements

- All nodes must be on the **same subnet** (up to 254 machines).
- **UDP multicast** must be enabled on the switch (port 47100–47101).
- **HTTPS** on port 443 (configurable via `--port`).

## Security

- HTTPS only (self-signed certificate generated on first run).
- PAM authentication — credentials are verified by the host OS.
- Secure session cookies (`Secure`, `HttpOnly`, `SameSite=Lax`).
- Login rate limiting (5 attempts, then 30-second cooldown).
- Gossip TTL=1 — multicast never leaves the local subnet.
- Host files are mounted read-only into the container.

## Web Console Tabs

| Tab | Description |
|---|---|
| **Test** | Live cluster view: computer name, GPU ID, GPU model, timestamp |
| **Reserved** | Placeholder for future functionality |

## Notes

- The container must be restarted after host password changes
  (`python3 corelink.py --restart`).
- A self-signed TLS certificate is generated automatically and persisted
  in the `corelink-data` Docker volume.  Accept the browser warning on
  first visit.
