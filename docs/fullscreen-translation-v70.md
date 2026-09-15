# Fullscreen and cooking translation (v70)

The regular card and fullscreen use the same Translate handler, but fullscreen
reloads recipe details first. The previous translation cache key included full
ingredient objects, stock shortages and step metadata. Identical title/step text
could therefore miss a successful translation cache entry after opening the
dialog, creating another local-model call. An incomplete model reply immediately
failed the action. The screenshot's generic error cannot identify the exact
model reply; both failure paths were reproduced with the v69 production handler.

## Changes

- Title/step translations use a separate cache namespace keyed by source title,
  source language, ordered instruction text and target language. Ingredient
  labels, stock, presentation metadata and step IDs do not change that key.
  Existing successful entries under the previous key are adopted when found.
- A complete valid model reply is accepted in one request. Incomplete replies
  retry only invalid or missing steps, at most once per step, in smaller prompts.
  When an array has the wrong length, every step is requested separately because
  the missing position is unknown. The UI receives a translation only after the
  full title and ordered steps pass the existing number-preservation checks.
- Current source IDs, amounts, device-send evidence and cooking step indices are
  retained. Source instructions remain available in `originalInstruction`.
- Pending actions are shared across regular cards, weekly slots and fullscreen
  for the same edition. The request uses a snapshot of the recipe.
- The existing bottom-right task popup receives step completion progress.
  Translation still requires available local AI and an explicit button click.

## Verification

- Both cache-miss and truncated-output regression tests fail against the
  unchanged v69 handler and pass against v70.
- Seven focused Python checks exercise the production endpoint, cache keys,
  prompts, validation, bounded retries, old-cache adoption and source preservation.
  AI, HA services/storage and ingredient localization are isolated test boundaries.
- The fullscreen DOM test invokes the actual Python translation handler with
  intentionally incomplete model output. It checks fullscreen cooking first,
  regular-card translation first, current-step highlighting, title/steps shared
  between views, and duplicate pending actions with different view states.
- Active shared UI, catalog flow, recipe layout, actions and photo-overlay suites
  run against the new v70 bundle. The installer retains preflight, backup,
  rollback and exact served-bundle verification.

This workspace cannot access the user's Home Assistant/Ollama or a graphical
browser. The tests simulate model responses; they do not guarantee the quality
of arbitrary output from the configured local model.

## Installation

Use `tools/deploy_offline_runtime_v70.sh` as a standalone root script on the HA
host. It pins the reviewed runtime commit. Reload the Cook4Me panel afterwards;
there is no need to regenerate the weekly plan for this translation fix.
