# Cook4Me bug audit — v115

Panel build: `2026.9.17.19`. Audited from the published v114 product-links build.

## Confirmed defects and fixes

| Area | Reproduced problem | Fix |
| --- | --- | --- |
| Reservations and shopping | Spending an early shared package on rice left an oats shortage even when a later rice-only package could cover the rice. | Joint physical-lot allocation can reassign flexible packages to meet all possible demand. |
| Consumption | A linked product stored in both mass and volume could skip the compatible package. | Allocate using the requested measurement and preserve the actual owner and lot ID when deducting stock. |
| Expiry priority | One package linked to two recipe ingredients counted twice. | Deduplicate physical lot IDs. |
| Nutrition prediction | A partial exact label could supply its full amount repeatedly through different catalogue links. | Share one temporary label pool across the recipe. |
| Nutrition reconciliation | A removed package's exact label could survive against a sibling with the same expiry. | Explicit lot IDs must still exist; date fallback is reserved for legacy records without IDs. |
| Nutrition consumption | Another package's label could match by barcode or expiry despite conflicting explicit lot IDs. | Conflicting IDs never match. |
| Nutrition capacity | Exact-ID and legacy records could together exceed the remaining physical quantity. | Reserve capacity for exact-ID records first, then cap legacy quantities against the remainder. |
| Barcode persistence | A failed mapping save changed the mapping in memory. | Publish staged data only after the write succeeds. |
| Concurrent barcode saves | Interleaved writes could lose a saved mapping. | Serialize staged writes with a per-store lock. |
| Nutrition persistence | A failed reconciliation or consumption write changed in-memory label quantities. | Stage the updates and preserve the previous data on failure. |
| Concurrent nutrition saves | Overlapping consumption reports could lose a deduction, and reconciliation could overwrite a newly saved reference. | Serialize all nutrition mutation entry points around the complete read, modify and save operation. |
| Scanner storage | Changing the inline storage field left the product summary showing the previous location. | Refresh the summary together with the amount. |
| Remembered products | A missing primary catalogue link made a saved product unusable even when another valid link survived. | Restore the primary selection from the remaining valid links. |
| Camera restart | A delayed permission rejection could update the discarded scan draft after Restart. | Apply the camera error to the active draft. |

The shared allocator is used by reservations, quantity feasibility, both recipe
cost calculators, nutrition prediction and physical consumption. It preserves
unit compatibility, explicit package selection, unlimited staples and unknown
stock. Expiry order remains deterministic; satisfying feasible demand takes
precedence over assigning a flexible package to an ingredient that has another
source. Physical inventory is never expanded into copies for catalogue links.
The recipe price cache version changes so old allocations are recalculated.

## Verification

- Sixteen new backend regression tests reproduce the affected stock, label and
  persistence cases. Allocation is also compared against exhaustive solutions
  for small overlapping-link inventories and checked through a multi-step
  reassignment case. Controlled concurrent writes reproduce both lost-update
  failures; failed consumption is also retried without a double deduction.
- Three new Chromium checks exercise the actual v115 bundle: storage summary,
  recovery of remembered links, and a delayed camera failure after Restart.
  The existing product-links browser suite passes against v115, covering scan
  cancellation, multiple links, additive packages, exact retries, product-name
  grouping, expiry editing and narrow/wide layouts.
- Targeted existing suites cover inventory, reservations, food feasibility,
  nutrition, automatic prices, weekly selection, package creation, product
  capture, recipe delivery, runtime persistence and announcements.
- Updated the v75 stale-announcement test to delay on the delivery lock. Its old
  AI hook no longer ran because fixed state messages have been deterministic
  since v105. No speech behavior was changed.
- Frontend bundle freshness, JavaScript syntax and whitespace checks pass.

This is a focused audit of the recent scanner and shared-stock changes plus
their dependent calculations and relevant delivery regressions. It is not a
claim that every historical suite or every system is bug-free. A previously
documented v86 seasoning-status assertion expects the older status value; it is
unrelated to this update. Browser providers and installer hosts are simulated;
no live cooker, phone camera or Home Assistant installation was available.
