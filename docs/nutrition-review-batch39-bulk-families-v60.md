# Batch 39: third bulk nutrition-family pass

Base: Batch 38 / PR #130, merged at `e5d840a5748ca3717814c3dc79c3db4fd85dcf50`.

This pass adds **122 explicit target-to-FDC reference bindings** covering **1,347 recipe ingredient usages**. The classifier still approves zero targets by itself. Every accepted target has its own destination review row and retained-reference receipt.

The largest new family is named dry/as-purchased rice: Basmati, Arborio/Carnaroli/risotto/Vialone/Baldo, sushi/Japanese, Jasmine/Thai and brown rice. Before approving semantic rice concepts, the original multilingual source identities were inspected and the selected plain concepts were required to contain no wash/rinse/soak/drain/cooked qualifier. The generic `Rice` concept remains excluded because Batch 36 proved that one source identity historically lost an explicit wash/30-minute-soak/drain qualifier. Explicit washed/rinsed rice targets also remain unresolved.

Other reviewed families cover explicit 50–64% dark chocolate ranges, chocolate/speculoos/amaretti/shortbread/digestive biscuits, caramel, fruit/berries, Provola/Emmental, cut-only beef, pork collar, prosciutto, speck/pancetta, cod, wrappers, prawns, unspecified fish, ham tortellini, edamame, selected chili forms, dried seaweed, bisque, corn porridge, nuts, peppercorns, fleur de sel, leaveners, drained sweetcorn, pumpkin, pea pods, sauerkraut, gherkins, salad onion and wholemeal flour T110.

Generic `Rice`, generic `Pepper`, potato/generic starch, crème fraîche, curry, garam masala, mixed herbs, ambiguous blends/concentrations and explicit washed/rinsed rice remain outside this batch. No provider/FDC crawl, automatic rule expansion, density, piece weight, edible yield, hydration, cooking conversion, catalog activation, release, deployment, Home Assistant restart or live-cache mutation is included.

All 12 historical holds / 22 exact held identities remain unchanged. All 11 historical provenance discrepancies remain visible inside the hold set. The retained candidate snapshot remains `e3b22f9b0834a79ffcc471d7bc61c07f08ce1f63da312c2ac36e84633c2931ac` and reference manifest remains `e135d4235a897688e37f8561602820bb84d186e91c09d9f654f52bf0d8fab29d`.

After this batch the recorded target count is **4,961**, the never-reviewed queue is **1,358**, and unresolved-or-held is **1,370**.
