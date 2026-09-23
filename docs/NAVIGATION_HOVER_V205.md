# Navigation hover clipping — v205

The inherited `.tab:hover { transform: translateY(-1px) }` moves the top
border outside the v203 `#tabs` horizontal scrollport, which has zero padding.
`overflow-x: auto` also establishes clipping on the other axis; setting only
`overflow-y: visible` would not fix that combination.

The active panel's existing stylesheet now keeps navigation tabs untransformed.
Hover still changes their theme-aware background/border; it does not move them.
Keyboard focus uses the retained two-pixel outline with an inset offset, keeping
it inside the strip without increasing header height. Reduced-motion mode has
no transition. The rule is scoped to `.v100-navigation #tabs .tab`; other buttons,
recipe actions and camera controls are untouched. Dimensions, tab order, handlers,
selection, per-view filters and horizontal touch scrolling are unchanged.

No new mixin, module, dependency, API call or data change is introduced. Only CSS
in the active panel and runtime delivery identifiers change. Runtime URL, query
and element advance together to v205; all earlier mixins, including the v204
recipe cooking-mode badges, remain composed. Manifest and HACS packaging remain
unchanged.

Local isolated Chromium reproduction uses the inherited hover rules from the
retained v126 bundle and inspected current navigation CSS. At 390x844, 844x390
and 1749x800 the old top border is -1 pixel outside the strip; with the fix it is
0 pixels outside and the keyboard ring is inside the border. This is not a live
HA or full-chain local test. Both original files modified here were verified
against the current GitHub blob hashes before applying the small delta.

`tests/browser_navigation_hover_v205.py` uses the existing offline loader and
actual delivered frontend constructor. It exercises all seven navigation buttons,
portrait, landscape and desktop, light/dark themes and normal/reduced motion.
It checks hover/focus geometry, retained scrolling and original click handlers.
The existing App-wide interface refresh workflow runs it after the retained UI
suite, avoiding an extra workflow. All other existing checks remain enabled.
Full-chain results are available in the PR checks. HA/API/icon/sample-data
boundaries remain controlled; no live Home Assistant was accessed or deployed.

CSS overflow reference:
https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/overflow
