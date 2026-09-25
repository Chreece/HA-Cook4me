# Dialog header and footer audit — runtime v234

Announcements previously scrolled the whole card and used a sticky footer inside
the form. Theme padding left a gap beneath the buttons, negative footer margins
could cause horizontal overflow, and fields could pass behind the buttons.

Dialogs now use a fixed header, a scrolling content area, and a separate action
footer flush with the card edge. Existing controls and event listeners are moved,
not recreated; announcement submit buttons remain inside their original form.
Filter selection follows its existing anchor after the layout moves the controls.

| Menu | Result |
| --- | --- |
| Announcements | Header and Test/Save footer stay visible, including after language changes. |
| All eight filters and household source | Header and Apply footer stay visible; bulk selection and selected-first ordering are preserved. |
| Meal history | Header and Save/Close footer stay visible; usage fields fit phone and tablet widths. |
| Package weighing | Header and Apply/Cancel controls stay visible in landscape. |
| Saved receipts | Header stays visible while receipt rows scroll; per-line actions stay with their products. |
| Device information and ingredient details | Header and close control stay visible. |
| Product editor, scanner, and recipe menus | Existing fixed controls retained and covered by the full frontend regression suite. |

Validation uses the actual frontend module chain with local Home Assistant/API
fixtures. `browser_dialog_footers_v234.py` checks card bounds, horizontal overflow,
header/footer positions before and after scrolling, original action bindings,
keyboard focus, rerenders, themes, and rotation at 360, 390, 680, 844, and 1440 px.
The receipt queue browser suite, 284-check frontend suite, design/menu unit tests,
runtime tests, and legacy bundle consistency check also pass. No live Home
Assistant instance, speaker, scale, or receipt service is needed for these checks.
