# Weekly variety and photo actions, v69

Active panel: `cook4me-panel-v69-bundle.js`, build `2026.9.15.11`.

All shared recipe cards put their title and language above the photo. The action
buttons and expand/collapse control sit over the bottom of the photo, with 50%
opacity. Hovering a control or focusing within the action area makes the controls
fully visible. Touch activation also reveals the active control. Buttons remain
separate from the photo button, so choosing an action cannot accidentally open
the fullscreen recipe. Fullscreen keeps its title above the photo and the same
action overlay. The steps and manual cooking controls remain in their section.
Missing images retain a photo placeholder and usable action buttons.

Weekly selection now treats alternate language/serving editions and closely
related regional publications as repeated choices. The catalog examples behind
the report have separate grouping IDs, varying English canonical wording, and
sometimes different image URLs. The planner therefore compares both family/ID
and canonical title/ingredient evidence. It does not change catalog grouping,
source recipe IDs, edition selection, quantities or device-send proof.

The planner's variety rule is generic:
- An existing display family or recipe identity counts as already selected.
- Equal nonempty canonical title and ingredient sets also cover simple dishes.
- Otherwise, at least three foods and 80% of the smaller ingredient set must
  overlap, plus either 50% canonical-title term overlap or the same image URL.
- A generic title or reused image alone cannot exclude a different dish.

Canonical names come from the bundled catalog. The rule uses no AI and contains
no special cases for crumble, porridge, ramen or any named dish. Similarity here
is a weekly variety decision, not a claim that regional ingredient quantities
or provider identities are interchangeable. Deliberately planned leftovers keep
their existing behavior.

A regenerated slot avoids the dish being replaced and the dishes on other
current days. If selected filters leave too few different dishes, generation
leaves the remaining days empty rather than filling them with translated copies.
Existing saved plans are not silently edited on page load: generate the next
seven days once after installing to replace their repeated selections.

Regression checks use the three real crumble editions and two real porridge
editions from the reported screenshot, execute the production weekly generation
loop, and cover seven unique selections, replacement, limited choices, simple
dishes, and reused-image/title counterexamples. The DOM checks cover title/photo
order and overlay controls in Today, Week, Official, saved recipes and the book,
plus expansion, fullscreen cooking and delayed icon decoration. The active
bundle also runs the shared controls, real catalog flow, previous layout and
local-translation/shopping checks. Graphical-browser and device confirmation
remain pending; automated frontend checks use a DOM.
