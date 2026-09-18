# Diet checks and complete ingredient replacements — v76

A selected vegetarian diet previously relied on a short ingredient word list.
Duck, veal, cod, squid, anchovies and other animal ingredients could pass. The
check also missed the `foodName` field, and the compact Today cache discarded
its safety result. Opening a recipe could use the household diet instead of the
selected filter.

The ingredient check now recognizes additional meat, fish, seafood and animal
derivatives in canonical English and common source-language names. It checks
each ingredient separately, distinguishes explicit plant foods such as coconut
milk, and retains explicit incompatible ingredient evidence. Missing ingredient
text and unresolved recipe-level exclusions cannot qualify for an adaptation.

Recipes are eligible for a restricted diet either as written or when every
identified incompatible ingredient has a suitable advisory replacement. Each
replacement is tied to its original ingredient index. Partial coverage stays
excluded. Allergy and avoid conflicts remain blocking, and replacement choices
are checked against those restrictions too. Foods whose functional replacement
cannot be established from the ingredient list, including gelatin and whole
eggs, do not receive a generic substitute.

The original recipe remains incompatible (`match.safe` is false). An independent
`eligibleWithSubstitutions` flag permits it to appear with a visible replacement
badge and a complete replacement list in expanded cards and fullscreen. The
replacement names and explanations support English, Greek and German. Other UI
languages use English for these new labels.

Official appliance programs, original ingredients, cooking times and nutrient
values are preserved. The UI explains that the displayed cooking/nutrition
values refer to the original. Sending an incompatible original recipe stays
blocked. Pending adaptations do not reserve stock or add original ingredients
to shopping; weekly shopping reports unresolved adaptations. Already cooked
leftovers cannot qualify based on potential raw-ingredient replacements.

The selected diet is carried into recipe-detail/presentation requests and
preserved in the compact Today cache. Old or mismatched restricted-diet cards
stay hidden until results are refreshed. Refresh Today, Week and Official
results after installing this update.

Checks cover missed animal foods, complete and incomplete substitutions,
allergy/avoid restrictions, vegan and pescatarian differences, cached match
persistence, original recipe send protection and shopping reservations. DOM
checks cover stale results, selected-diet requests, escaped replacement text and
disabled original actions. Browser geometry checks retain 42 cards across six
layouts. Live Home Assistant/appliance verification remains pending.

Validation: all 1,356 Python tests passed. The final pinned installer passed all
four installation, backup and rollback checks. Four dashboard DOM suites passed,
and Chromium verified all 42 card layouts including replacement badges and lists.
The runtime is pinned to `d17bc0c8627831c7ae5c4e54f098b3e8d13242dd`.
