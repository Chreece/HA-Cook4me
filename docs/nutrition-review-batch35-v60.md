# Batch 35: unresolved evidence requirements and offline reference navigation

Base: `fa50586c269d4f2a5e3248f4d50e1f5454453df9` (Batch 34 / PR #126).

**No new nutrition bindings are approved in this batch.** A requirement is a
record of missing evidence, not a completed review, a rejection forever, or an
additional historical hold. All 235 historical source files / 4,622 recorded
bindings and the 12-hold registry remain unchanged. The completeness queue still
contains **1,697** never-recorded targets; including the 12 holds, **1,709** targets
remain unresolved or held.

## Why this pass is different

Recent batches have found fewer defensible matches in the same retained file.
Rescanning the same unresolved foods and returning a shorter approval batch does
not establish the missing identities or preparation states. This pass records
**28 explicit target-specific evidence requirements** so the next investigation
can address the requirements rather than rediscovering them.

Examples:

- Salt and pepper needs blend proportions or a matching measured blend profile.
  Neither salt alone nor pepper alone represents the unnamed ratio.
- Rice and stock need their measurement state, preparation or concentration
  established before a dry or prepared reference is chosen.
- Potato starch must not inherit a gluten-free roll recipe just because the
  roll's description contains the words “potato starch”.
- Mascarpone, seitan and creme fraiche need a defensible food-specific reference;
  a nearby dairy, flour or tofu record is not an identity proof.
- Fresh tarragon must not inherit a dried-herb profile. Duck fat must not inherit
  duck sauce or goose fat.

These are scoped, explicit non-selection decisions, **not a claim that every
possible synonym or reference has been exhausted**. A literal zero-result search
is not proof that a food is absent from USDA or even from the retained corpus
under another description. No new provider/FDC query is made.

## New maintenance tool

`tools/prepare_nutrition_review_worklist_v60.py` first runs the existing real
hold/provenance audit against the exact retained file. It validates the manual
ledger's full target IDs, canonical names, usage counts, source-file fingerprint
and complete original target-row fingerprints. Similar names are not merged.

The tool then creates an index of **7,410 distinct FDC IDs / 44,854 original
candidate occurrences** in the full file. Every occurrence retains its actual
source target, rank, description, data type and hash of the complete candidate.
The index is navigation data, not an approved food table. Search is a literal,
case-insensitive AND substring lookup on descriptions; it does not rank foods for
acceptance, choose a candidate, copy another target's review or alter nutrition.
Held source targets are excluded from search locators, not used as evidence
precedent. An independent unheld occurrence of the same FDC record is not globally
blocked merely because that record also appears in a held target's search.

## Output and counts

`remaining.json` preserves all 1,697 original rows and their order. The separate
`untriaged.json` investigation view contains **1,669** rows, excluding the 28
explicitly documented requirements **only from that investigation view**. It is
not a replacement completeness queue and does not claim that the 1,669 rows have
suitable matches. The 28 are still visible in `worklist.json` and the full queue.

If a later batch explicitly binds a requirement's target, the ledger can remain
unchanged and reports `recorded-later-not-certified-by-this-ledger`. An active
hold takes precedence over that status. Only the established review/resolution
and independent catalog-validation paths can establish nutrient readiness.

The original 11 provenance discrepancies remain visible, with zero outside the
unchanged hold set. The global readiness flag remains false. The 446 earlier
recorded targets outside this snapshot remain outside its provenance scope.
Unheld review inspection is not nutrition completion or catalog activation.

## Local use

Run from the existing project checkout with its virtual environment. Use an
already-saved full candidate file, not the compressed CI projection:

```sh
.venv/bin/python tools/prepare_nutrition_review_worklist_v60.py \
  --evidence /path/to/saved/fdc-target-candidates-offline.v60.json \
  --output /path/to/new/project-local/logs/batch35-worklist
```

Add repeated `--query` options to replace the ledger's default literal searches:

```sh
.venv/bin/python tools/prepare_nutrition_review_worklist_v60.py \
  --evidence /path/to/saved/fdc-target-candidates-offline.v60.json \
  --query 'potato starch' --query 'mascarpone' \
  --output /path/to/new/project-local/logs/reference-lookup
```

Only the compact summary is printed. Reports include the complete unchanged
queue, worklist, reference index/search results, original hold audit and recorded
binding checkpoint. The output directory must not already exist. Inputs,
historical reviews and holds are never written.

Exit 1 means an input/output/validation failure. Exit 2 means reports were written
but unresolved targets, holds or unexplained provenance discrepancies remain;
it is expected for the current snapshot. Exit 0 requires all three counts to be
zero, not just successful report generation. No device test or HA restart is
needed.

## Validation and continuation

The compressed CI fixture explicitly contains a subset of exact original rows,
not a reconstructed or complete evidence capture. Regression tests cover source
fingerprints, policy/type/identity drift, duplicates, candidate hashes, lexical
false matches, held locators, later-review status, immutable queue partitions,
audit gates, input changes during audit and CLI exit/no-overwrite behavior.

The full retained file remains pinned at SHA-256
`e3b22f9b0834a79ffcc471d7bc61c07f08ce1f63da312c2ac36e84633c2931ac`.
Reference manifest:
`e135d4235a897688e37f8561602820bb84d186e91c09d9f654f52bf0d8fab29d`.

Continuation should target these explicit evidence requirements and the untriaged
investigation view without shrinking the completeness queue until an actual new
binding is reviewed. Retrieving more source material, when authorized, must pin
it separately; it must not overwrite the current snapshot or historic receipts.
No provider/FDC crawl, nutrient population, release, activation, deployment,
restart or live Home Assistant cache change is included in this batch.
