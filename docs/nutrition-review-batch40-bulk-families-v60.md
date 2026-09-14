# Batch 40: fourth bulk nutrition-family pass

Base: Batch 39 / PR #131, merged at `55f99c60d300c17279566ba122ff1c2accb66955`.

This pass adds **110 explicit target-to-FDC reference bindings** covering **765 recipe ingredient usages**. The classifier still approves zero targets by itself. Every accepted destination has an explicit review row and an exact retained-reference receipt.

The pass deliberately leaves the high-impact ambiguous families unresolved: generic `Pepper`, generic `Rice`, `Curry`, potato/unspecified starches, crème fraîche, garam masala and mixed herbs. It instead advances bounded families such as named cheese, plant drinks, salad greens, hot pepper varieties, vegetarian fillets, fish/shellfish category fallbacks, pasta/flatbread, chocolate presentation families, dried kombu, selected preserved desserts, and exact retained categories such as sprinkles, sorbet, maraschino cherry, praline, dulce de leche, raw prawns and lamb rib.

Tier B rows explicitly document where the retained USDA reference is only a category fallback. No exact brand, species, cultivar, fatty-acid profile, fortification, filling, cure, cocoa percentage or ingredient ratio is claimed unless the target/reference establishes it. No provider/FDC crawl, rank-as-proof selection, density, piece/yield, cooking, soaking, draining or concentration conversion is performed.

After the batch: **5,071 recorded targets**, **1,248 never-reviewed targets**, **12 held targets**, and **1,262 unresolved-or-held targets**. The 11 historical provenance discrepancies remain visible and confined to the hold set. The 446 older recorded targets outside the retained snapshot remain outside that snapshot's verification scope.
