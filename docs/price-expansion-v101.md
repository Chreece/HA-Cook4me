# Offline price expansion v101

Checked 2026-09-17 for Germany/EUR. Five new package references bring the offline snapshot to **514 observations: 371 receipt observations and 143 retail references**. The existing 120 USDA portions, six recipe portions, four densities and 18 budget groups are retained.

## Catalog coverage

The reproducible audit compares published v100 commit `1e1ca9937322da3c9c824f24cf5955e57292b93f` with v101 across the same **32,163 language/serving variants and 230,483 ingredient occurrences**, without household prices.

| Measure | v100 | v101 | Change |
| --- | ---: | ---: | ---: |
| Occurrences with observed/reference prices | 132,921 | 134,124 | +1,203 |
| Variants fully covered by observed/reference prices | 5,575 | 5,749 | +174 |
| Occurrences using rough food-group budgets | 43,460 | 42,278 | −1,182 |
| Unmeasured basic zero allowances | 13,462 | 13,462 | 0 |
| Covered occurrences, including budgets and zero allowances | 189,843 | 189,864 | +21 |
| Complete variants, including budgets and zero allowances | 15,252 | 15,261 | +9 |
| Variants without any observed/reference price | 1,512 | 1,509 | −3 |

These are occurrences and language/serving variants, not unique recipes. Most gains replace rough budgets with named product evidence. Gains are minced beef (367), ground beef (132), cod (322), cod fillet (8), vanilla pod (298), vanilla pods (2) and Demerara sugar (74). Sixty-one variants still have no usable budget cost.

`price-expansion-v101.json` records the full summary, changed ingredient identities and the next 30 reference gaps. Reproduce it with:

```sh
python tools/audit_price_expansion_v101.py --output /tmp/cook4me-v101-audit.json
```

## New package evidence

All prices below include VAT and exclude shipping. They are dated representative retail prices, not national averages or availability promises. Saved household prices remain preferred.

| Product | Package price | Source |
| --- | ---: | --- |
| Der Ludwig raw Simmental ground beef, shock-frozen | €16.95 / 500 g | [Der Ludwig](https://www.der-ludwig.de/rinderhackfleisch) |
| Fresh skinless cod fillets | €22.90 / 500 g | [Send-a-Fish](https://www.send-a-fish.de/kabeljaufilet-frisch-ohne-haut/) |
| Naturata organic Demerara sugar | €3.59 / 500 g | [Naturata](https://www.naturata-shop.de/Demerara-Rohrohrzucker-500-g/NAT-034035) |
| Whole organic Fairtrade Bourbon vanilla pods, tube | €10.00 / 3 pods | [Vanillekiste](https://shop.vanillekiste.de/shop/echte-bourbon-vanilleschoten-aus-madagaskar/?attribute_groesse=Drei+St%C3%BCck+im+Reagenzglas) |
| Whole Bourbon vanilla pods, refill | €25.00 / 50 g | [Vanillekiste](https://shop.vanillekiste.de/shop/echte-bourbon-vanilleschoten-aus-madagaskar/?attribute_groesse=50g+im+Standbodenbeutel) |

The minced-beef reference uses a specialist butcher's named product; its price can differ substantially from supermarket purchases. It does not price whole beef cuts or mixed mince. Generic cod is explicitly represented by skinless fresh fillets; salted, dried and breaded forms are not matched. Fillet counts do not infer a weight.

Demerara uses the single-pack price, without the six-pack discount, and has its own exact category. It does not substitute for every brown sugar. Vanilla count and mass references come from different packages: no gram-per-pod conversion uses the retailer's approximate refill count. Powder, seeds, extract, tablespoons and unspecified packet sizes do not receive a whole-pod price.

Shell-on mussels were researched but deferred: the catalog also contains quantities that may mean shelled meat. Broad beef, stock and spice identities likewise need better form evidence. Missing recipe quantities remain unresolved. Unmeasured salt, pepper and water keep v99's separate zero-budget allowance, without increasing observed/reference coverage.

## Runtime and verification

Build `2026.9.17.5` serves the v101 bundle and invalidates price evidence caches with version 101. The new bundle retains the responsive v100 header and shared navigation/filter bar. Four reviewed retailer HTTPS hosts are added to the existing evidence-link validation.

- Five backend tests cover exact package costs, count/mass separation, unsupported forms and amounts, market/currency/date boundaries, saved-price priority, persistent cache reuse and five real catalog variants through the translated recipe-cost endpoint.
- The shipped bundle renders the actual €23.28 evidence fixture in English, German and Greek, including all five package links and rejection of misleading hostnames, credentials, protocols and ports.
- Existing v97 price/quantity and v99 zero-allowance tests remain part of the focused regression checks.
- Four installer tests cover preflight, installation, failures and rollback. Both staged and installed probes require all five new references and the updated evidence counts. The installer runs the v101 backend tests before swapping files.
- Bundle freshness, Python compilation, shell syntax and whitespace checks are included.

The installer is pinned to the tested runtime in a follow-up commit and retains backup and rollback. No live Home Assistant deployment was performed.
