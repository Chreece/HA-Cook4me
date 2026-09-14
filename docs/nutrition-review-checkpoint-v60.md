# Resumable offline nutrition reviews

`tools/snapshot_nutrition_review_checkpoint_v60.py` reads **all** committed
`release_catalog_reviewed_nutrition_targets*.v1.json` files, rather than
reconstructing a baseline from chat history or the last downloaded batch.

The checkpoint contains every full target ID, its exact recorded FDC binding,
its source filename and SHA-256, and fingerprints of the complete file set and
binding set. It rejects duplicate IDs even when the FDC IDs agree, invalid rows,
unsafe policies, non-integer FDC IDs, symlink inputs, and duplicate JSON keys.
No source files are changed. Output requires a new directory.

## Local checkpoint and resume

Use the existing Cook4Me project virtual environment:

```sh
REPO="$HOME/project/cook4me/repo"
OUT="$HOME/project/cook4me/logs/nutrition-checkpoint-$(date +%Y%m%d-%H%M%S)"
"$REPO/.venv/bin/python" "$REPO/tools/snapshot_nutrition_review_checkpoint_v60.py" \
  --review-root "$REPO/tools" \
  --output "$OUT"
```

Add `--evidence /path/to/existing/fdc-target-candidates-offline.v60.json` to
reconcile an already-saved offline candidate snapshot. Do not recrawl a provider
or query FDC to recreate available evidence. Only supply `--source-commit` for a
known clean checkout; the optional label is caller-supplied, not independently
verified by the script. The file-content fingerprints always describe the bytes
actually read.

Outputs:

- `checkpoint.json`: complete recorded binding set and input-file fingerprints.
- `resume.json`: optional exact-ID subtraction, untouched remaining candidates,
  and provenance discrepancies against the supplied evidence.
- `summary.json`: counts only; the same compact summary is printed to the terminal.

Exit status is `0` for structural success, `1` for invalid input/output or duplicate
IDs, and `2` when reconciliation finds provenance mismatches. A status-2 report
is diagnostic: it does not authorize a new review batch. Recorded targets with
mismatches are never silently returned to the unreviewed queue.

## Two separate gates

A recorded binding or successful metadata check is **not** semantic nutrition
proof. The tool deliberately reports `semanticApprovalPerformed=false` and never
selects a search result, rewrites an identity, resolves nutrients, or activates a
catalog. A food-form mismatch (for example a dry powder bound to prepared liquid)
needs separate review even when the chosen FDC ID exists in the candidate list.

Reference-manifest SHA-256 identifies the frozen nutrient reference, not the
exact candidate-search output. The resume report also pins the candidate file's
own SHA-256. Different candidate snapshots can share a reference manifest while
having different ranks or candidates. Preserve both artifacts and investigate
such differences instead of silently changing historic evidence metadata.

Counts distinguish recorded targets present in the supplied evidence from those
outside it. A partial evidence snapshot must never be treated as the entire
review universe, and total remaining work must not be guessed from filenames.

Before adding reviews, compare the checkpoint's file fingerprint with a fresh
snapshot of the actual base, explicitly assess each candidate, and require a
regression test proving full target-ID disjointness against every earlier source
file. Do not fill a batch quota with approximate foods.

## CI checkpoint

The `Nutrition review checkpoint` PR workflow checks out the exact PR head,
runs the checkpoint tests, and uploads the complete checkpoint and a tracked
source archive. Checkout credentials are not persisted and the job has only
read permission. This makes the accepted-ID baseline recoverable without
fetching hundreds of files individually. The artifact contains repository
source only, not `.git`, local provider captures, credentials, or nutrient caches.
CI without the local offline evidence performs structural checks only.
