# Package opening and expiry

The product editor uses manual package-label days or an applicable reviewed offline
catalog rule. Selecting a catalog rule requires confirmation of its displayed
refrigeration temperature and handling conditions. Exact ingredient identity,
brand and verified barcode constraints are checked again by the server. Choosing
manual entry clears catalog provenance and uses the label's entered duration.

For a known duration, **Apply the opening deadline as the expiry date** and
**Package opened** are separate checkboxes. New products default to not applying
the deadline until selected. Marking a package opened fills today's opening date;
the date remains editable. Multiple packages added together share these settings.
Receipt drafts retain the same choices. Existing records without an application
flag keep their earlier behavior.

`bestBefore` remains the printed date. `effectiveBestBefore` is the earlier of that
date and `openedAt + useWithinDays` when application is selected. With application
off, the printed date remains effective. “No expiry” suppresses only the printed
date; an explicitly selected opening deadline still applies. Inventory lists,
storage-place lists, FEFO selection and existing expiry notifications use the
effective date. The printed date is never extended.

The finished-cooking review offers opening controls per eligible package. Users
choose the actual lot in the existing package selector when automatic FEFO would
use a different one. Opening changes are committed with stock deduction, only for
packages actually consumed. An unavailable or unconsumed selected package rejects
the change for review. Previously opened packages keep their first opening date;
untouched opened packages are not sent as new opening changes. Deduction reports
retain the opening settings so restoring a depleted package from meal history
preserves its deadline.

No catalog durations or evidence were broadened in this batch. Seasonal metadata
and the notification dismissal ledger are unchanged. This is an explicit way to
apply catalog guidance, not an assessment of a food's actual condition.

Local checks include package expiry and restoration regressions, actual product
and receipt save routes, editor request tests, and the delivered browser module
chain at 390 px and 1440 px. Interaction-position checks also exercise Home
Assistant's outer shadow-host scroll container.
