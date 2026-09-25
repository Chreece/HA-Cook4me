# Catalog names without recipe quantities

Catalog choices remove numeric amounts, package weights and spoon/cup annotations
before grouping duplicate food names. Amount variants share a translated choice;
every original ingredient ID and search alias remains available. The supermarket
name index also includes those IDs so saved products still resolve correctly.

This is a catalog presentation change. Provider records, recipe ingredients,
shopping quantities, nutrition and stock amounts are not rewritten. The amount
normalizer preserves food specifications such as fat percentages, flour types and
sugar ratios, along with distinct fresh, canned and dried food names.

Validation covers the complete shipped catalog in Greek, German and English,
unchanged source records and recipe/shopping amounts, and the actual frontend on
mobile and desktop with legacy ingredient selections. Runtime v225 refreshes the
delivered frontend and its supermarket alias index.
