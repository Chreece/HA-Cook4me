# Recipe actions and multilingual shopping, v68

Active panel: `cook4me-panel-v68-bundle.js`, build `2026.9.15.10`.

The missing Translate action had two backend causes. Local AI capability fields
were added to the old v8 response, but the live panel uses v11 and the v28 cached
seed. Both active paths now include the proven Ollama task IDs. Old capability
snapshots are refreshed when their recipe section opens, including Week and the
recipe book. A new, unused AI Task is also usable: its `unknown` state means no
last-activity timestamp. Actual availability, data-generation support and local
platform provenance still govern the backend check.

The AI Task state behavior follows the [Home Assistant entity implementation](https://github.com/home-assistant/core/blob/dev/homeassistant/components/ai_task/entity.py).
The button remains absent without an available local task or when a UI-language
edition/translation already exists. A cloud default does not replace the local
provider. Availability updates affect the button without reloading the page.

On explicit click, Cook4Me loads the selected edition's instructions if necessary
and asks the local model for only the title and cooking steps. Complete cached
translations can be reused. Step count, order and instruction numbers must be
preserved; incomplete output is rejected. The translated title and steps stay
visible after expansion and update both the result card and fullscreen dialog.
Device identity, quantities and source language remain intact. Development and
shopping-label work do not invoke the user's model.

The weekly calendar and recipe icons now remain under their own renderer's
control during the delayed icon pass. The old pass omitted Week from its table,
replaced the calendar with `circle-small`, and prepended a pot icon to Send.
Week retains its calendar when selected or unselected, and Send has one arrow.

Shopping requests include the UI language; the server obtains the country from
Home Assistant. Bundled ingredient names produce labels such as
`100 g Καρότο (Karotten; Carottes)` for a Greek UI, German country and French
recipe. Repeated names are omitted. Shortage rows retain original ingredient
identity/name metadata, and the calculated missing quantity and unit are kept.
Legacy description text cannot override that amount. Weekly shopping applies
the same formatting and retains distinct original names when aggregating recipes
from different catalogs. Manually entered free text is kept as entered.

Regression checks execute the actual active capability and shopping handlers,
feed the capability response into the panel, and run the queued icon decorator.
They cover unused/available/unavailable local tasks, a cloud default, no implicit
translation calls, translated title/steps in both views and after expansion,
three-language shopping labels, weekly aggregation and exact shortage amounts.
The shared controls, rolling-week layout and real catalog flow also run against
the active bundle. Physical-device and graphical-browser confirmation remains
pending; automated UI checks use a DOM.
