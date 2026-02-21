# TODO

## Outstanding
- Add more GPU metrics (temperature, utilization, memory) to cluster table
- Add sorting/filtering to GPU table
- Consider adding node uptime or last-seen column
- Consider per-node monitor metrics (show each node's resource usage in the cluster table)
- Consider collapsing repeated PC/Timestamp columns for multi-GPU nodes (rowspan or first-row-only)

## Completed — v0.01.8
- Integrate @nosana/kit for Nosana node discovery and blockchain status in new "Nosana" tab
- Replace "Reserved" tab placeholder with live Nosana container/wallet/status table
- Hosts counter populated from discovered Nosana nodes
- Node.js 22.x added to container, Docker socket mounted for container discovery

## Completed — v0.01.7
- Fix gossip thread starvation from eventlet cooperative scheduling (UDP buffer, select timeout, yield point)
- Relax NTP sync threshold from 2s to 5s to match SNTP precision

## Completed — v0.01.6
- Rename columns: "GPU Limit" → "Bottleneck", "Time Synch?" → "NTP Sync", "AppComm" → "CoreLink I/O"
- Add info tooltip icons to all seven column headers with descriptive hover text

## Completed — v0.01.5
- Fix versioning scheme: correct all historical version numbers and add permanent versioning rules

## Completed — v0.01.4
- Remove third-party data relay from anti-entropy — only send self data, eliminates stale oscillation

## Completed — v0.01.3
- Fix gossip anti-entropy replaying stale cached data after node restart

## Completed — v0.01.2
- Fix GPU Limit to show true PCIe bottleneck (min of GPU and slot capability) via sysfs
- Replaces nvidia-smi-only approach that missed slot lane restrictions

## Completed — v0.01.1
- Add "GPU Limit" column showing PCIe bottleneck (gen x width) from nvidia-smi
- Graceful fallback to `0.0 x 0` for missing/unparseable PCIe fields

## Completed — v0.01.0
- Fix WebSocket 500 error by switching from simple-websocket to eventlet
- Replace `ssl_context` with eventlet-compatible `certfile`/`keyfile` params
- ~15-30% reduction in per-node AppComm kbps (expected: WebSocket has less overhead than HTTP long-polling)

## Completed — v0.00.9
- Replace browser-based time sync with real NTP verification (SNTP query to pool.ntp.org)
- Add `ntp_drift` field to gossip heartbeat, cluster state, and anti-entropy
- Tighten sync threshold from 15s to 2s (NTP-verified)
- Graceful degradation: NTP unreachable shows no indicator

## Completed — v0.00.8
- Fleet status with PC/Host counts and singular/plural logic
- NIC column with color-coded negotiated link speed
- Time Synch column with epoch drift indicator (now superseded by NTP in v0.00.9)
- Merge hostname into connection badge
- Show `---` on subsequent GPU rows for NIC and AppComm

## Completed — v0.00.7
- Add AppComm column with per-node net_kbps via gossip
- Add LAN Saturation aggregate metric to status line
- Merge CoreLink Resources into Cluster Status line
- Increase CPU/RAM/Net decimal precision in monitor.py
