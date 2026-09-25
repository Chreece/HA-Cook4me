# Keep the user's place during interaction

Runtime v220 preserves the position of ordinary controls in the product editor
and the surrounding Cook4Me views. It does not add a setting or change inventory
requests, quantities, nutrition, ingredient identity or package accounting.

## Audit findings and changes

- The full ingredient picker rebuilt every checkbox and sorted selected rows to
  the beginning after each selection. It now keeps alphabetical order and reuses
  checkbox nodes by ingredient identity. Selecting or deselecting a row preserves
  the list offset and keyboard focus, allowing adjacent ingredients to be added.
- Tab state saved only `#content.scrollTop`, although Home Assistant can scroll
  the document or an ancestor inside another shadow root. Rendering now captures
  the actual scroll owners, including dialogs and nested lists, and restores them
  after replacement. Returning to a visited tab restores its current-session
  position independently of the other tabs.
- Existing product form redraws retain open disclosures, the ingredient search
  field and its caret, nested list offsets and dialog position. A fresh draft
  still starts a new form. Deferred layout restoration is cancelled by subsequent
  user interaction, a different draft/view/account or explicit validation focus.
- Native summaries and weekly fold buttons retain the clicked position when
  opened. Browser scroll anchoring is disabled within the managed Cook4Me content
  so it cannot move a focused row after our restoration or footer resizing.
- The same rendering guard covers profile/inventory, stock-summary refreshes,
  recipe grids/dialogs and weekly sections. Capture happens when a render starts,
  so late network results preserve where the user has moved in the meantime.

Intentional destinations remain: opening a new product or recipe, moving to a
requested editor field, revealing required ingredient assignment after a scan,
validation errors, and following cooking steps. Position is naturally clamped
when collapsing or filtering leaves less scrollable content. Existing persisted
fold, filter and recipe state remains in place.

## Verification

`tests/browser_interaction_position_v220.py` loads the actual frontend module
graph with mocked Home Assistant/network boundaries. It exercises a 3,293-row
picker at 390px and 1440px with document scrolling and a nested Home Assistant
shadow scroll host. It checks repeated assignment, keyboard deselection,
suggestions, open sections, full form refresh, search focus, validation, late
refreshes after scrolling, tab return, inventory folds and weekly folds.

The regression runs in the existing interface CI workflow alongside the desktop/
mobile interface, full-catalog responsiveness and navigation/focus regressions.
