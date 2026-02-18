# CoreLink

## Overview
GPU cluster communication framework. Host launcher script, Docker container 
with HTTPS web console, PAM auth, GPU discovery, and UDP gossip protocol 
for LAN-wide node status across up to 254 machines.

## Tech Stack
- Host script: Pure Python 3.8+ stdlib (no pip)
- Container: nvidia/cuda:12.2.0-base-ubuntu22.04
- Web: Flask + Flask-SocketIO (threading mode)
- Auth: python-pam + Flask-Login
- Frontend: Bootstrap 5 (bundled)
- Gossip: UDP multicast 239.77.77.77:47100

## Build & Test
- Prereq check: python3 corelink.py --check
- Build: python3 corelink.py --build
- Start: python3 corelink.py --start
- Stop/Restart: --stop, --restart
- Logs: --logs, --logs-follow

## Project Tracking
- See IMPLEMENTATION_PLAN.md for current roadmap. Update it as tasks are completed.
- See CHANGELOG.md for version history. Append to it with each delivery.
- See TODO.md for outstanding items.
