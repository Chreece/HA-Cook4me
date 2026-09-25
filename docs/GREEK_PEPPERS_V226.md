# Whole peppers and pepper spices

Three provider foods share the English name `Pepper`. Their French and German
source labels identify separate foods: bell pepper (`Poivron` / `Paprika`,
M_FOOD_389), pepper spice (`Poivre` / `Pfeffer`, M_FOOD_388), and chilli pepper
(`Piment`, M_FOOD_377). Grouping by that English name merged them, and the Greek
label became `Πιπέρι` even for the vegetable.

Reviewed presentation overrides now distinguish `Πιπεριά`, `Πιπέρι`, and
`Πιπεριά τσίλι` before catalog grouping and recipe/shopping naming. Six source
rows describing peppers chopped, deseeded or cut into strips join the vegetable
choice. Paprika spice (M_FOOD_358) stays `Πάπρικα`; its German display name is
`Paprikapulver` to keep it separate from vegetable `Paprika`.

These are exact source-ID presentation corrections. They do not rewrite the
provider catalog, saved product assignments, recipe quantities, prices or
nutrition. Original source names remain search aliases. Runtime v226 refreshes
the frontend. Tests cover the complete shipped catalog in Greek, German and
English, recipe/shopping quantities, and mobile/desktop ingredient choices.
