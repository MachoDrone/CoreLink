# Changelog

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
