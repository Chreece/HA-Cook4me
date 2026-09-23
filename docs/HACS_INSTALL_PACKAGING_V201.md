# HACS download/install packaging — v201

## The reported delay

This change addresses the time between pressing Update and HACS finishing its
download/file installation. It does not change Home Assistant startup, catalog
indexing, weekly generation or device communication.

Cook4Me's `hacs.json` has no `zip_release` setting. HACS's normal integration
installer first downloads the repository source archive and then extracts the
integration directory. It therefore transfers development material that never
gets installed. Cook4Me also keeps older compiled frontend bundles in the
integration directory; the active v127+ chain uses the v126 bundle, which already
contains those earlier layers. The old compiled copies are build/history inputs,
not additional runtime dependencies of the current panel.

References inspected for this audit:
- https://raw.githubusercontent.com/hacs/integration/main/custom_components/hacs/repositories/base.py
  (`download_content`, `download_repository_zip`, `should_try_releases`)
- https://git-scm.com/docs/git-archive (`export-ignore`)
- https://hacs.dev/docs/publish/start/ (`zip_release`, `filename`)

## Distribution change only

A root `.gitattributes` now excludes development-only `tools`, `tests`, `docs`,
`scripts` and `.github` from source archives. It also excludes compiled
`cook4me-panel-vN-bundle.js` copies with N < 126. The current v126 bundle,
all unbundled source modules, all catalog/locale data, translations, images and
other runtime files remain byte-identical. Nothing is deleted from Git history
or normal git clones. The root README, license, HACS metadata and manifest remain.

This works with the current main-branch download model; it does not switch users
to releases, require another updater or set a runtime persistent directory.
Older tags are immutable and keep their existing archive contents. The individual
file fallback in HACS does not use Git export attributes, so this optimization
applies to the successful source-archive download path.

The existing `HA-Cook4me.zip` release artifact is NOT enabled as a HACS zip
release by this change: it currently uses a `custom_components/cook4me/` wrapper,
while HACS extracts zip-release contents directly into the integration directory.
Changing channels without also correcting and validating that layout would be a
separate change. Here, `hacs.json` and the release workflow remain unchanged.

Developers should use `git clone` to obtain the full test/build/evidence tree;
GitHub's automatically generated source archives are now installation-focused.

## Validation and measurements

`python tests/test_hacs_archive_v201.py` runs seven packaging tests. They compare
every retained integration file's SHA-256 with its tracked source; verify full
catalog, locale, translation and asset retention; resolve the active frontend's
static/dynamic literal import graph; reject missing dependencies; and verify
that only the superseded compiled bundles are omitted from the runtime directory.
The tests run on the real repository, not a small runtime catalog fixture.

The HACS installation archive workflow builds before/after ZIPs, reports exact
compressed and extracted sizes/file counts, and downloads the actual public
GitHub archive for the tested commit. Every downloaded file is then checked
against the locally verified archive. Both old and new extraction paths are timed
in a temporary directory; these times measure the CI runner, not Home Assistant.
The workflow has read-only repository permissions and uses no HA credentials.

An initial local check against retained pre-consolidation commit `5223eb462d1e41d51fc1e05b086e810a6ace3e7d`
passed all seven tests: the source archive went from 32,334,256 to 13,443,656 bytes
(58.42% smaller), excluding 62 older bundles totaling 63,983,094 uncompressed bytes.
Current-main results are reported by this PR's HACS installation archive job;
they can differ as the runtime catalog and source have advanced.

This is not a promise that HACS will finish in a fixed number of seconds. Network
transfer, GitHub response time, local disk/backups, and any download fallback can
still contribute. No timing from the user's HA installation was collected.
