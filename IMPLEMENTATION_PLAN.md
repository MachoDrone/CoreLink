CoreLink Implementation PlanContext
CoreLink is a GPU cluster communication framework. An empty corelink.py and stub README.md exist in the repo. We need to build the complete system from scratch: a host launcher script, a Docker container with an HTTPS web console, PAM authentication, GPU discovery, and a gossip protocol for LAN-wide node status sharing across up to 254 machines.
Architecture Decisions
DecisionChoiceRationaleHost scriptPure Python 3.8+ stdlibNo pip on host; must work via python3 <(curl ...)Container basenvidia/cuda:12.2.0-base-ubuntu22.04Provides nvidia-smi; base variant keeps image smallWeb frameworkFlask + Flask-SocketIO (threading mode)Well-tested, extensible, async Socket.IO for real-time UIWebSocketsimple-websocketReplaces deprecated eventlet; recommended by Flask-SocketIO maintainerAuthpython-pam + Flask-LoginPAM delegates to host OS; Flask-Login handles sessions/remember-meFrontendBootstrap 5 (bundled in container)No CDN calls at runtime; offline-capableGossipUDP multicast heartbeats + anti-entropy digest exchangeLow bandwidth, fast convergence, single-subnet optimizedNetworking--network hostRequired for UDP multicast; container shares host networkHTTPSSelf-signed cert via openssl in entrypointGenerated on first run, persisted in Docker volumeWSGI serverFlask dev server via socketio.run()Simple, handles WebSocket natively with simple-websocket; adequate for admin panel with few concurrent users
Files to Create/Modify
1. /home/user/CoreLink/corelink.py — Host Launcher (~300 lines)

Argument parsing: --check, --build, --start, --stop, --restart, --status, --logs, --port
Prerequisite checks: Ubuntu 20-24 (parse /etc/os-release), NVIDIA GPU (nvidia-smi), NVIDIA Container Toolkit (nvidia-ctk), Docker (docker info)
Curl-pipe detection: check if __file__ resolves to /dev/fd/*; if so, download container files from GitHub via urllib.request
Docker image build and container lifecycle management
Container run flags: --gpus all, --network host, bind-mount /etc/passwd, /etc/shadow, /etc/pam.d (all :ro), named volume corelink-data:/data

2. /home/user/CoreLink/container/Dockerfile

Base: nvidia/cuda:12.2.0-base-ubuntu22.04
Install: python3, python3-pip, libpam0g-dev, openssl, curl
pip install from requirements.txt
Download Bootstrap 5.3.3 CSS/JS and Socket.IO 4.7.5 client JS via curl during build
Copy app code, set entrypoint

3. /home/user/CoreLink/container/requirements.txt
flask
flask-socketio
flask-login
simple-websocket
python-pam
4. /home/user/CoreLink/container/entrypoint.sh

Generate self-signed TLS cert if not exists (stored in /data/ssl/)
Generate Flask secret key if not exists (stored in /data/secret_key)
Launch python3 /app/server.py

5. /home/user/CoreLink/container/app/server.py — Flask App (~120 lines)

Flask + SocketIO setup with threading async mode
Flask-Login integration with user_loader reading /etc/passwd
Routes: / (console, login_required), /login, /logout
SocketIO events: connect (reject unauthenticated), background task pushing cluster_state every 3s
Initialize GossipNode and start it
SSL context from /data/ssl/ certs

6. /home/user/CoreLink/container/app/auth.py — PAM Auth (~60 lines)

User(UserMixin) class with username as id
authenticate_pam(username, password) using python-pam with service='login'
Simple rate limiting: track failed attempts per IP, 30s cooldown after 5 failures

7. /home/user/CoreLink/container/app/gossip.py — Gossip Protocol (~200 lines)

Multicast group: 239.77.77.77, port: 47100/udp
Heartbeat loop (every 5s with jitter): broadcast own hostname, GPU list, timestamp, sequence number
Receive loop: listen on multicast + unicast (port 47101) via select(); process heartbeat, digest_req, digest_resp messages
Anti-entropy loop (every 10s): pick random peer, send digest {node_id: seq}, peer responds with missing/newer entries
Reaper loop (every 5s): remove nodes unseen for 60s, mark nodes unseen for 20s as stale
get_cluster_state(): return sorted list of all nodes (self + peers) with status

8. /home/user/CoreLink/container/app/gpu.py — GPU Discovery (~30 lines)

Run nvidia-smi --query-gpu=index,name --format=csv,noheader,nounits
Return list of {"id": 0, "model": "RTX A6000"} dicts

9. /home/user/CoreLink/container/app/templates/base.html

Dark theme layout, Bootstrap 5
Navbar: "CoreLink" title, version "v0.00.1" in small muted text, logout button
Tab navigation: Test, Reserved
Block for tab content

10. /home/user/CoreLink/container/app/templates/login.html

Centered login card on dark background
"CoreLink" title + version
Username/password fields, "Remember me" checkbox, Login button
Error message display area

11. /home/user/CoreLink/container/app/templates/console.html

Extends base.html
Test tab: Table with columns: Computer Name, GPU ID, GPU Model, Timestamp

Rows populated by Socket.IO cluster_state events
Stale nodes get amber/yellow indicator
Node count shown above table


Reserved tab: "Reserved for future use" placeholder text

12. /home/user/CoreLink/container/app/static/css/style.css

Dark theme: background #0d1117, cards #161b22, text #c9d1d9, accent #58a6ff
Login card styling
Table styling with status indicators
Tab content transitions

13. /home/user/CoreLink/container/app/static/js/app.js

Socket.IO connection (WebSocket preferred, polling fallback)
cluster_state handler: rebuild GPU table, apply status styling
Tab switching logic
Connection status indicator
Framework for future command buttons (wired but not populated)

14. /home/user/CoreLink/README.md — Documentation

Overview, prerequisites, installation, usage examples
curl-pipe and cloned-repo modes
Network requirements (multicast, ports)

Gossip Protocol Bandwidth

254 nodes x 200 bytes/heartbeat / 5s = ~10 KB/s multicast (trivial)
Anti-entropy: ~254 KB/s total worst case (still trivial on any LAN)

Security

HTTPS-only, secure session cookies (Secure, HttpOnly, SameSite=Lax)
PAM auth delegates credential verification to host OS
Login rate limiting (5 attempts, 30s cooldown)
Gossip TTL=1 (LAN-only), no sensitive data in gossip messages
All host mounts are read-only

Fix: Update REPO_RAW_URL for feature branch testing
Problem
corelink.py line 25 hardcodes REPO_RAW_URL to point to main. When run via curl one-liners, --start and --build download container files from that URL — but those files only exist on the feature branch, so the download 404s.
Change
In /home/user/CoreLink/corelink.py, line 25 — change:
pythonREPO_RAW_URL = "https://raw.githubusercontent.com/MachoDrone/CoreLink/main"
to:
pythonREPO_RAW_URL = "https://raw.githubusercontent.com/MachoDrone/CoreLink/claude/add-usage-examples-fh9kU"
Also update the branch reference in the docstring (lines 7-8) and the help epilog (line 362) to match.
This enables curl-pipe testing from the feature branch. When merged to main, this should be reverted back to main.
Usage Commands (feature branch)
Start (first time — checks prereqs, builds image, runs container)
bash# curl
python3 <(curl -sL https://raw.githubusercontent.com/MachoDrone/CoreLink/claude/add-usage-examples-fh9kU/corelink.py) --start

# wget
python3 <(wget -qO- https://raw.githubusercontent.com/MachoDrone/CoreLink/claude/add-usage-examples-fh9kU/corelink.py) --start

# custom port
python3 <(curl -sL https://raw.githubusercontent.com/MachoDrone/CoreLink/claude/add-usage-examples-fh9kU/corelink.py) --start --port 8443
From a cloned repo
bashgit clone -b claude/add-usage-examples-fh9kU https://github.com/MachoDrone/CoreLink.git
cd CoreLink
python3 corelink.py --start
Stop
bashpython3 <(curl -sL https://raw.githubusercontent.com/MachoDrone/CoreLink/claude/add-usage-examples-fh9kU/corelink.py) --stop
Restart
bashpython3 <(curl -sL https://raw.githubusercontent.com/MachoDrone/CoreLink/claude/add-usage-examples-fh9kU/corelink.py) --restart
Force rebuild
bashpython3 <(curl -sL https://raw.githubusercontent.com/MachoDrone/CoreLink/claude/add-usage-examples-fh9kU/corelink.py) --build
Rebuild and start
bashpython3 <(curl -sL https://raw.githubusercontent.com/MachoDrone/CoreLink/claude/add-usage-examples-fh9kU/corelink.py) --stop
python3 <(curl -sL https://raw.githubusercontent.com/MachoDrone/CoreLink/claude/add-usage-examples-fh9kU/corelink.py) --build --start
Check prerequisites only
bashpython3 <(curl -sL https://raw.githubusercontent.com/MachoDrone/CoreLink/claude/add-usage-examples-fh9kU/corelink.py) --check
Status and logs
bashpython3 <(curl -sL https://raw.githubusercontent.com/MachoDrone/CoreLink/claude/add-usage-examples-fh9kU/corelink.py) --status
python3 <(curl -sL https://raw.githubusercontent.com/MachoDrone/CoreLink/claude/add-usage-examples-fh9kU/corelink.py) --logs
python3 <(curl -sL https://raw.githubusercontent.com/MachoDrone/CoreLink/claude/add-usage-examples-fh9kU/corelink.py) --logs-follow
Verification

Build: python3 corelink.py --check should pass all 4 prereq checks on a properly configured host
Build: python3 corelink.py --build should build the Docker image
Run: python3 corelink.py --start should start the container on port 443
Login: Navigate to https://<hostname> and log in with a host Ubuntu user
Test tab: Should show the local node's GPU info, updating every few seconds
Multi-node: Running on a second machine on the same subnet, both nodes should appear in each other's Test tab within ~15 seconds
