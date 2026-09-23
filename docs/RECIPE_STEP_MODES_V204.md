# Recipe step cooking modes — v204

The shared step renderer now shows the recipe's cooking mode alongside each
instruction. It applies to expanded recipe cards and fullscreen recipes opened
from Today, Week, Discover, the recipe book and personal recipes. Modes are
informational: displaying them does not send, change or start a cooker program.
They describe the recipe, not the device's live state.

## Evidence and labels

Previously, the provider normalizer already retained `programKey` and
`programName`, but the shared `_v66Body` renderer displayed only instruction text.
This change exposes that evidence using interface-language labels. English,
German, Greek and French are supported, independent of the recipe or supermarket
language. Examples include Pressure cooking, Browning, Steaming, Simmering,
Reheating and Keep warm. Explicit high/low-pressure names remain distinct.

Only recognized complete program names or descriptive keys are localized. Opaque
keys such as `PROGRAM_1` are never assigned a guessed meaning. An unknown program
name remains visible as source text; without a usable name, the step says that
the cooking mode is not specified. Explicit preparation/serving types are shown
as such. Instruction prose and recipe-level modes do not supply missing step
metadata. No temperature, duration, pressure setting or extra step is invented.

The normalizer also retains multiple source operations in their original order.
It prefers `APPLIANCE_GROUP_15` sequences and no longer falls back to a program
explicitly belonging to another appliance. Older unscoped sequences remain
supported only when no explicit Cook4Me sequence exists. Legacy flattened
program fields remain available for current consumers and cached recipes. Old
cached recipes that lack the new operation list can show only their existing
first-program evidence until refreshed through the existing detail workflow.

Text translation reapplies current source step objects, so program metadata,
step IDs and numbering survive translations without changing the cached text
translation contract. Steps without program data remain usable and do not cause
extra network requests merely to populate a badge.

## Interface and safety boundaries

Badges use Home Assistant theme variables and wrap at mobile widths. Original
instructions, step numbers, order, active-step highlighting, previous/next controls
and action handlers remain intact. Repeated rendering does not duplicate badges.
Source names are inserted with `textContent`, not interpreted as HTML.

The active panel composes a new `RecipeStepModesMixin` around the v203 design and
all preceding modules. Runtime URL, query and active element advance to v204;
manifest and HACS update-channel settings remain unchanged. Catalog, ingredients,
pricing, stock, generation, scanner, receipt persistence and device transport are
not modified.

## Validation

The new tests cover multilingual labels, missing/opaque metadata, multiple modes,
appliance isolation, translation retention, unchanged source data, escaping,
numbering, repeat rendering and UI-language changes. The backend regression was
run against the old normalizer first: foreign-appliance fallback failed, and the
new operation-list assertions failed until implementation. The frontend tests
also failed before the new module existed.

Local validation uses the verified current provider normalizer and shared step
renderer in a retained repository checkout. It is not a full-current-catalog
benchmark or a live Home Assistant test. The new CI workflow runs the browser
suite with `--full-chain`, loading the current repository's actual frontend graph
through the retained v203 offline loader and its controlled HA/API/icon/data
boundaries. All existing validation workflows remain enabled.

```sh
python tests/test_recipe_step_modes_v204.py
node --test tests/test_recipe_step_modes_v204.mjs
python tests/browser_recipe_step_modes_v204.py --full-chain
```

Manufacturer mode terminology was checked against the official Tefal Cook4Me+
product/manual page; it is not used to infer numeric SEB program IDs:
https://www.tefal.com/Rice-%2526-Multicookers/Cook4Me/COOK4ME-%252B-/p/7211002894

No live Home Assistant deployment or physical cooker action was performed.
