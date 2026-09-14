# Nutrition review Batch 45 — Curry / Garam masala triage (v60)

Batch 45 stays deliberately small. It creates **no nutrition binding** and changes only five unresolved targets whose labels are generic formulated spice blends: `Curry` and `Garam masala`.

## Frozen baseline

- source evidence SHA-256: `e3b22f9b0834a79ffcc471d7bc61c07f08ce1f63da312c2ac36e84633c2931ac`
- recorded review targets after Batch 44: **5,080**
- unresolved targets: **1,239**
- manual-family lane: **310**
- context-heavy lane: **929**

## Exact small scope

Only five exact targets move from manual-family review to context-heavy review:

- semantic + provider `Curry`;
- semantic + provider `Garam masala`;
- `Garam masala, a little`.

Together they account for **1,419 recorded ingredient usages**.

These names identify formulated spice mixtures, but not a reproducible ingredient composition. The retained candidate evidence illustrates the problem rather than resolving it: generic `Curry` locates prepared curry dishes/sauce, while generic `Garam masala` locates an unrelated branded bean masala soup. Search rank is therefore not identity proof.

## Scope boundaries

The new pattern is fully anchored and intentionally does **not** absorb `Curry paste`, `Curry roux`, green/Thai curry paste, `Tikka masala paste`, `Garam masala (spice mix)`, or `Madras curry blend`; those already carry explicit composition wording and are already context-heavy through the existing classifier.

Named single-food controls such as `Juniper berries`, `Vanilla pod`, `Ground Sichuan pepper`, `Shiso leaves`, `Parsley root`, and `Broad bean` remain manual.

## Result

- recorded review targets: **5,080 → 5,080**
- unresolved targets: **1,239 → 1,239**
- manual-family lane: **310 → 305**
- context-heavy lane: **929 → 934**
- bindings created: **0**
- provider/FDC network requests: **0**

This is triage only. It does not select an FDC candidate, infer provider identity, change a hold, create a bulk rule, or authorize automatic approval.
