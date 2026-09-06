# Release versioning

Format: `YYYY.M.D.BUILD`.

Examples:
- first release on 2026-09-06: `2026.9.6.1`
- second release that day: `2026.9.6.2`
- first release on 2026-09-07: `2026.9.7.1`

Run `python scripts/version.py next --write`, commit the manifest update, then tag the exact same value. The release workflow rejects tag/manifest mismatches.
