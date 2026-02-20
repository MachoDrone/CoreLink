# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview
CoreLink is a GPU cluster communication framework. A host launcher script builds and manages a Docker container that runs an HTTPS web console with PAM auth, GPU discovery, and a UDP gossip protocol for LAN-wide node status across up to 254 machines.

## Build & Run Commands
All commands go through the single entry point `corelink.py`:
```
python3 corelink.py --check          # Verify prerequisites (Ubuntu 20-24, nvidia-smi, nvidia-ctk, Docker)
python3 corelink.py --build          # Build Docker image only
python3 corelink.py --start          # Build if needed + start container
python3 corelink.py --stop           # Stop and remove container
python3 corelink.py --restart        # Stop then start
python3 corelink.py --status         # Show container status
python3 corelink.py --logs           # Show container logs
python3 corelink.py --logs-follow    # Stream logs live
python3 corelink.py --start --port 8443  # Custom HTTPS port (default: 443)
python3 corelink.py --version        # Show version
python3 corelink.py --get-ca         # Show CA cert location + install instructions
python3 corelink.py --regen-cert     # Force regenerate this node's TLS cert + start
```
There are no unit tests, linters, or CI pipelines. Validation is manual: build, start, log in via browser, check GPU table populates.

## Git Workflow — MANDATORY
- **NEVER** commit directly to `main`. Always create a feature branch first.
- **NEVER** push to `main`. Code reaches `main` only via merged PRs on GitHub.
- A pre-push hook enforces this — direct pushes to `main` are blocked.
- Branch naming: `git checkout -b <type>/<short-description>` using prefixes: `fix/`, `feat/`, `refactor/`, `docs/`, `chore/`
- Always use `gh pr create` to open PRs. Never merge locally.
- After creating a PR, report the PR URL and **STOP** — do not merge.
- **NEVER merge a PR** unless the user has explicitly confirmed testing on all 3 cluster nodes (nn01, nn03, nn05). If the user says "merge it" without confirming tests, **refuse and remind them** to test first. A casual "merge it" is NOT sufficient — require explicit confirmation like "tested on all nodes, merge it."
- **Verbose git descriptions**: When proposing ANY git action, always name the specific branch and target. Example: "Push branch `fix/gossip-timeout` to origin and create PR targeting main" — never say "push it" or "send it".
- Workflow sequence: `git pull origin main` → `git checkout -b <type>/<desc>` → make changes → `git add` + `git commit` on the branch → `git push -u origin <branch>` → `gh pr create` → report URL.

## Architecture

### Two-Layer Design
- **Host layer** (`corelink.py`): Pure Python 3.8+ stdlib — no pip allowed. Handles prereq checks, Docker image builds, and container lifecycle. Detects curl-pipe execution (`__file__` starting with `/dev/`) and downloads container files from GitHub via `urllib.request` when needed.
- **Container layer** (`container/`): nvidia/cuda:12.2.0-base-ubuntu22.04 base. Flask + Flask-SocketIO web app with all pip dependencies isolated inside the container.

### PAM Authentication Flow
The container authenticates users against the **host OS** by bind-mounting `/etc/passwd`, `/etc/shadow`, and `/etc/pam.d` as read-only. `python-pam` in `auth.py` calls PAM's `login` service. Flask-Login manages sessions with an 8-hour lifetime.

### Gossip Protocol (`gossip.py`)
Runs 4 daemon threads inside `GossipNode`:
1. **Heartbeat** — broadcasts JSON via UDP multicast (`239.77.77.77:47100`) every ~5s with jitter
2. **Receive** — listens on multicast + unicast (`47101`) via `select.select()`; processes heartbeat, digest_req, digest_resp messages
3. **Anti-entropy** — every ~10s picks a random peer, exchanges digest `{node_id: seq}` to fill gaps from lost packets
4. **Reaper** — marks nodes stale after 20s, removes after 60s

Uses dual sockets: multicast (47100) for one-to-many, unicast (47101) for targeted digest responses. TTL=1 keeps traffic on the local subnet.

### Real-Time Web Console
`server.py` runs a background thread that calls `gossip.get_cluster_state()` every 3s and emits `cluster_state` via Socket.IO to all authenticated clients. The frontend (`app.js`) rebuilds the GPU table on each event. Connection uses WebSocket with polling fallback.

### Container Networking
`--network host` is required — the container must share the host network stack for UDP multicast to work. This means the HTTPS port (default 443) binds directly on the host.

### TLS Certificates (Local CA)
On first `--start`, the host script generates a local CA in `~/.corelink/ca/` and signs a per-node cert with SANs for hostname, hostname.local, localhost, and all host IPs. Certs are bind-mounted into the container at `/data/ssl/`. Users install the CA cert once in their browser/OS to trust all nodes. The CA key must be copied to each node so it can sign its own cert. `--get-ca` prints install instructions. `--regen-cert` forces cert regeneration (e.g., after IP change). The container also serves `GET /ca.pem` (unauthenticated) for easy browser download.

### Persistent State
- **Host**: `~/.corelink/ca/` (CA cert + key), `~/.corelink/nodes/<hostname>/` (node cert + key)
- **Container**: Docker named volume `corelink-data` at `/data` stores Flask secret key (`/data/secret_key`). TLS certs are bind-mounted from the host.

## Key Conventions
- **Version string** appears in: `corelink.py` (line ~24, `VERSION`), `container/app/server.py` (line ~20, `VERSION`), and `README.md` header. Update all three when bumping. Versioning scheme is `X.YY.Z` — increment Z for each release; Z rolls 0–9 then bump YY (e.g., 0.01.9 → 0.02.0).
- **REPO_RAW_URL** in `corelink.py` (line ~25) controls where curl-pipe mode fetches container files. Must point to the correct branch.
- **Frontend assets** (Bootstrap, Socket.IO JS) are downloaded during `docker build` and bundled — no CDN calls at runtime.
- **Async mode**: Flask-SocketIO uses `eventlet` backend for native WebSocket support. Eventlet monkey-patches stdlib to use cooperative green threads; existing daemon threads (gossip, monitor) work unchanged.

## Tech Stack
- Host script: Pure Python 3.8+ stdlib (no pip)
- Container base: nvidia/cuda:12.2.0-base-ubuntu22.04
- Web: Flask + Flask-SocketIO (eventlet async mode)
- Auth: python-pam + Flask-Login
- Frontend: Bootstrap 5 (bundled), Socket.IO 4.7.5 client
- Gossip: UDP multicast 239.77.77.77:47100, unicast 47101

## Project Tracking
- See IMPLEMENTATION_PLAN.md for current roadmap. Update it as tasks are completed.
- See CHANGELOG.md for version history. Append to it with each delivery.
- See TODO.md for outstanding items.
- **All tracking docs (CHANGELOG.md, TODO.md, IMPLEMENTATION_PLAN.md) MUST be updated in the same feature branch as the code change, BEFORE creating the PR.** Never create a separate PR just for tracking updates.
