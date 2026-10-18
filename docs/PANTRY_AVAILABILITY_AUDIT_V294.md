# Pantry availability audit — physical stock and recipe coverage

This audit applies to **all ingredients**, not only rice or salt. It reviews the
same read-only identity and quantity pipeline used by Cook4Me recipes.

## Why a location could appear while the quantity chip showed “—”

Three types of evidence were previously handled at different stages:

1. **Physical package identity / storage location:** a recipe ingredient can
   match a stored package via an exact saved ingredient assignment.
2. **Quantity allocation:** the package must be available under the same
   identity when calculating amounts. PR #364 restored explicit row/lot links
   without allowing unconfirmed calculated aliases to spend physical stock.
3. **Live unlimited stock:** PR #367 made an exact unlimited assignment
   authoritative even when an old recipe match said “missing”, with an
   **∞ / Απεριόριστο απόθεμα** chip in the Greek UI.

The backend's unlimited-quantity row still used the *container* identity only
(e.g. `k:salt-bin`), rather than also carrying the recipe source key
(`salt-seb-ja`). A recipe view matching quantity rows by source key could
therefore fail to associate this otherwise correct result with the ingredient.
This contract is now consistent with finite quantity rows.

## Aggregate quantity calculation

A physically **unlimited** package counts as one fully covered ingredient in
the recipe's measured coverage average. If salt is unlimited and rice has
50% of the required quantity, the two measured ingredients yield **75%**
overall coverage, without double counting a physical lot or claiming rice is
fully available.

By contrast, a *conventional* publisher-defined staple whose presence has not
been established as a physical package stays excluded from the measured
quantity average as before. This preserves the longstanding distinction
between an assumed staple and actual recorded stock.

## Coverage and safeguards

| Evidence | Per-ingredient result | Overall result |
| --- | --- | --- |
| Explicitly linked unlimited salt, pepper, water or oil | `enough`, `unlimited`, 100% | Counts once at full coverage |
| Linked finite rice with enough grams | `enough`, measured percent | Actual measured share |
| Linked finite rice with only half the grams | `shortage`, 50% | Actual measured share, without borrowing salt |
| Stock with unknown/incompatible unit | Unknown, not a manufactured zero/100% | Existing conservative unknown behavior |
| Same translated label but unrelated source ID | Missing | Never borrowed from a different food |
| Publisher-declared staple with no verified package | `staple` | Excluded from physical coverage mean |

## Validation

- Read-only Python tests for general unlimited ingredients, foreign-language
  source IDs, quantity averages and conventional staples.
- JavaScript test confirming that an unlimited quantity row indexed by the
  published recipe key resolves to 100% even when the physical container has
  another identity.
- Existing mobile/desktop recipe, seasonal filter, inventory, shopping and
  HACS regression suites remain enabled.

No user pantry entries, physical packages, saved recipes or device commands
are modified by this calculation fix. A current host deployment still needs
HACS installation and Home Assistant refresh; repository checks alone do not
prove which version is running on a user's server.
