# Changelog

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
