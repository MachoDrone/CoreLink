# Changelog

## v0.01.7 — 2026-02-20
- Fix gossip thread starvation caused by eventlet cooperative scheduling
- Increase UDP receive buffer to 2 MB on multicast and unicast gossip sockets
- Reduce gossip receive loop select() timeout from 1.0s to 0.1s for faster heartbeat processing
- Add yield point (socketio.sleep(0)) after push loop emit to unblock gossip threads
- Relax NTP sync threshold from 2s to 5s (SNTP implementation doesn't account for RTT)
- Update NTP Sync tooltip to reflect 5-second threshold
- Bump version to 0.01.7 in corelink.py, server.py, and README.md

## v0.01.6 — 2026-02-20
- Rename column headers: "GPU Limit" → "Bottleneck", "Time Synch?" → "NTP Sync", "AppComm" → "CoreLink I/O"
- Add info tooltip icons (ⓘ) to all seven column headers with descriptive hover text
- New `.cl-info` CSS class for subtle tooltip icon styling (half-opacity, full on hover)
- Initialize Bootstrap tooltips in app.js for header info icons
- Bump version to 0.01.6 in corelink.py, server.py, and README.md

## v0.01.5 — 2026-02-20
- Fix versioning scheme: correct all historical versions (0.02.0→0.01.1, 0.03.0→0.01.2, 0.04.0→0.01.3, 0.05.0→0.01.4)
- Add permanent versioning rules to ~/.claude/CLAUDE.md and project CLAUDE.md
- Scheme: `X.YY.Z` — increment Z for each release; Z rolls 0–9 then bump YY
- Bump version to 0.01.5 in corelink.py, server.py, and README.md

## v0.01.4 — 2026-02-20
- Remove third-party data relay from gossip anti-entropy responses
- Anti-entropy now only sends the responder's own fresh data, never cached third-party state
- Eliminates stale data oscillation where peers re-broadcast old values after node restart
- Revert v0.01.3 `direct` flag logic in `_process_heartbeat` back to simpler `seq > existing` check
- Bump version to 0.01.4 in corelink.py, server.py, and README.md

## v0.01.3 — 2026-02-20
- Fix gossip anti-entropy replaying stale data after node restart
- Direct heartbeats now always accepted (handles seq reset on restart)
- Anti-entropy relayed updates only accepted if seq advances (prevents stale overwrite)
- Bump version to 0.01.3 in corelink.py, server.py, and README.md

## v0.01.2 — 2026-02-20
- Fix GPU Limit showing GPU-only max instead of actual PCIe bottleneck
- Replace nvidia-smi `pcie.link.gen.max`/`pcie.link.width.max` with sysfs-based detection
- Read both GPU and parent slot capabilities via `/sys/bus/pci/devices/`, take minimum
- Correctly reports slot-limited lanes (e.g., x1, x4) instead of always showing x16
- Pure sysfs — no additional packages needed (no lspci/pciutils)
- Bump version to 0.01.2 in corelink.py, server.py, and README.md

## v0.01.1 — 2026-02-19
- Add "GPU Limit" column showing PCIe bottleneck as `X.0 x Y` (gen x width)
- Query `pcie.link.gen.max` and `pcie.link.width.max` from nvidia-smi (effective max considering GPU + slot)
- Graceful fallback to `0.0 x 0` if PCIe fields are missing or unparseable
- New column appears between GPUid and NIC in the cluster table
- Data propagates automatically through gossip protocol — no gossip.py changes needed
- Bump version to 0.01.1 in corelink.py, server.py, and README.md

## v0.01.0 — 2026-02-19
- Fix WebSocket 500 error (`write() before start_response`) on every page load
- Switch Flask-SocketIO backend from `simple-websocket` (threading) to `eventlet` for native WebSocket support
- Remove `allow_unsafe_werkzeug=True` — eventlet provides its own WSGI server
- Replace `simple-websocket` with `eventlet>=0.33.0` in requirements.txt
- Update CLAUDE.md to reflect new async mode convention
- Bump version to 0.01.0 in corelink.py, server.py, and README.md

## v0.00.9 — 2026-02-19
- Replace browser-based time sync check with real NTP verification against `pool.ntp.org`
- New SNTP client in `monitor.py`: 48-byte UDP query, refreshes drift every 60s
- Add `ntp_drift` field to gossip heartbeat, cluster state, and anti-entropy exchanges
- Frontend `timeSyncIndicator()` now uses `ntp_drift` instead of comparing `epoch` vs browser clock
- Tighten sync threshold from 15s (browser-relative) to 2s (NTP-verified)
- `ntp_drift=None` (NTP unreachable) shows no indicator — graceful degradation
- Backward compatible: older v0.00.8 nodes default to `None` for `ntp_drift`; `epoch` still gossiped
- Bump version to 0.00.9 in corelink.py, server.py, and README.md

## v0.00.8 — 2026-02-19
- Rename status line from "Cluster Status" to "Fleet" with PC/Host counts and singular/plural logic
- Add NIC column between GPUid and Model showing color-coded negotiated link speed (red ≤1G, yellow <max, green =max)
- Detect default-route interface via `/proc/net/route` instead of "first physical up NIC" heuristic
- Detect max NIC speed via `ethtool` (new Dockerfile package); graceful fallback if unavailable
- Add "Time Synch?" column showing timestamp plus green ✓ or red ✗ based on 15-second epoch drift
- Add `epoch`, `link_speed`, `link_speed_max` fields to gossip heartbeat, cluster state, and anti-entropy
- Merge hostname into connection badge (e.g. "myhost connected") — remove standalone hostname text
- Show `---` on subsequent GPU rows for NIC and AppComm columns (was blank)
- Reorder server.py init: monitor created before gossip so link speeds can be passed to GossipNode
- Backward compatible: older v0.00.7 nodes default to 0 for new fields; UI shows "?" / empty for unknowns
- Bump version to 0.00.8 in corelink.py, server.py, and README.md

## v0.00.7 — 2026-02-18
- Add AppComm column to GPU table showing per-node CoreLink network throughput (Kbps)
- Add LAN Saturation metric summing all online nodes' AppComm values (displayed in Mbps)
- Gossip heartbeat now includes `net_kbps` field; propagated via anti-entropy digest exchanges
- New `set_net_kbps()` method on GossipNode, fed by server push loop every 3s
- Merge CoreLink Resources line into Cluster Status line (removed standalone div)
- Drop `Net: x / y Mbps` format; replaced with `LAN Saturation: x.xxx Mbps`
- Increase monitor precision: CPU 1→2 dp, RAM 1→2 dp, Net 1→3 dp
- Bump version to 0.00.7 in corelink.py, server.py, and README.md

## v0.00.6 — 2026-02-18
- Add self-monitoring resource display above cluster status line
- New `monitor.py` module: collects app-only CPU %, RAM %, network Mbps, and disk %
- CPU tracks container threads via `/proc/1/task/*/stat` with delta-based sampling
- RAM reads cgroup memory (v2 with v1 fallback) as % of host MemTotal
- Network estimates throughput from `/proc/1/io` non-disk I/O deltas
- Link speed auto-detected from `/sys/class/net/<iface>/speed`
- Disk shows sum of `/app` + `/data` files as % of root filesystem
- Metrics bundled into existing `cluster_state` SocketIO event (no new events)
- Frontend displays monitor line at 0.7rem above cluster status
- All stdlib — no new pip dependencies
- Bump version to 0.00.6 in corelink.py, server.py, and README.md

## v0.00.5 — 2026-02-18
- Remove CSS `text-transform: uppercase` from table headers; headers now render as written in HTML
- Rename "PC Name" column header to "PC"
- Fix timestamp suffix from uppercase "UTC" to lowercase "utc" (3 occurrences in gossip.py)
- Strip "NVIDIA " prefix from GPU model names in gpu.py
- Shrink cluster status text and connection badge to 0.7rem (matches table cell font size)
- Display hostname next to connection status badge in console
- Pass `hostname` from server.py to console.html template
- Bump version to 0.00.5 in corelink.py, server.py, and README.md

## v0.00.4 — 2026-02-18
- Local CA for warning-free HTTPS across cluster

## v0.00.3 — 2026-02-18
- Rename columns, add UTC suffix, shrink table text

## v0.00.2 — 2026-02-18
- Initial working implementation

## v0.00.1 — 2026-02-18
- Project scaffolding
