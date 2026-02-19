# TODO

## Outstanding
- Revert `REPO_RAW_URL` in corelink.py from feature branch URL back to `main` before merging PR
- Merge PR `claude/add-usage-examples-fh9kU` into `main`
- Populate "Reserved" tab with future functionality
- Add more GPU metrics (temperature, utilization, memory) to cluster table
- Add sorting/filtering to GPU table
- Consider adding node uptime or last-seen column
- Consider per-node monitor metrics (show each node's resource usage in the cluster table)
- Consider collapsing repeated PC/Timestamp columns for multi-GPU nodes (rowspan or first-row-only)
- Fix WebSocket 500 error on initial connect (Werkzeug `write() before start_response` with simple-websocket)

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
