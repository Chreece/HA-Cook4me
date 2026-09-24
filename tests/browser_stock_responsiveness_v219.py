"""Stock totals and interaction with a 3,293-row catalog and 80 review items.

Uses the delivered frontend chain. Only HA/network responses are fixtures; the
stock-summary loader and nutrition-review renderer run their production code.
"""
from pathlib import Path
import shutil

from playwright.sync_api import sync_playwright
from ui_offline_loader_v203 import local_html

ROOT = Path(__file__).resolve().parents[1]


def run():
    html = local_html(ROOT)
    override = "async _v142LoadStockSummary(){}"
    assert html.count(override) == 1
    html = html.replace(override, "")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=shutil.which("chromium") or None, args=["--no-sandbox"]
        )
        for width, height in ((390, 844), (1906, 978)):
            page = browser.new_page(viewport={"width": width, "height": height})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.set_default_timeout(5000)
            page.set_content(html)
            page.wait_for_function("window.ready")
            page.evaluate("""() => {
                const added = Array.from({length:3290}, (_, i) => ({
                    key:'ingredient-'+i, ingredientId:'provider-'+i,
                    sourceIngredientIds:['source-'+i], name:'Υλικό '+i,
                    presentationVersion:63, displayLanguage:'el', searchAliases:['Food '+i]
                }));
                app._ingredientCatalog = [...app._ingredientCatalog, ...added];
                const extraStock = added.slice(-40).map((row,i) => ({
                    key:row.key, name:row.name, quantity:500, unit:'g',
                    lots:[{id:'stock-'+i, quantity:500, storageLocationId:'pantry'}]
                }));
                app._houseIngredients = [...app._houseIngredients, ...extraStock];
                app._entry().profile.houseIngredients = app._houseIngredients;
                app._v78State.houseIngredients = app._houseIngredients;
                app._fixtureNutrition = {...app._fixtureNutrition, blockedFailures:80,
                    unresolvedDetails:added.slice(-80).map(row => ({
                        identity:'k:'+row.sourceIngredientIds[0], name:'Fallback', reason:'ambiguous'
                    }))};
                app._nutritionSettings = structuredClone(app._fixtureNutrition);
                const summary = {...app._v142StockSummary, packageCount:42};
                app._v142StockSummary = null;
                app._v142StockSummaryAt = 0;
                window.stockRequests = 0;
                const api = app._api.bind(app);
                app._api = (type,data) => {
                    if(!type.endsWith('/stock_summary'))return api(type,data);
                    stockRequests++;
                    return new Promise(resolve => setTimeout(() => resolve(summary), 50));
                };
                window.stockStart = performance.now();
                setTimeout(() => {window.stockTimerDelay=performance.now()-stockStart;}, 0);
                app.show('profile');
                window.stockRenderMs = performance.now()-stockStart;
            }""")
            page.wait_for_function("window.stockTimerDelay !== undefined && app._v142StockSummary?.packageCount === 42 && !app._v142StockSummaryLoading")
            result = page.evaluate("""() => ({
                render:stockRenderMs, timer:stockTimerDelay, calls:stockRequests,
                catalog:app._ingredientCatalog.length, inventory:app._houseIngredients.length,
                review:app.shadowRoot.querySelectorAll('[data-v218-unresolved]').length,
                loaders:app.shadowRoot.querySelectorAll('.v142-loading').length,
                packages:app.shadowRoot.querySelector('.v142-summary-stat strong')?.textContent,
                localized:app._v218LocalUnresolvedName({identity:'k:source-3289'})
            })""")
            assert result["render"] < 1500 and result["timer"] < 1500, result
            assert result["catalog"] == 3293 and result["inventory"] == 42, result
            assert result["review"] == 80 and result["loaders"] == 0, result
            assert result["calls"] == 1 and result["packages"] == "42", result
            assert result["localized"] == "Υλικό 3289", result
            page.locator('[data-v78-pane="places"]').click()
            assert page.locator('[data-v78-section="places"]').is_visible()
            page.locator('[data-v78-pane="stock"]').click()
            page.locator("[data-v84-search]").fill("Food 3289")
            assert page.evaluate("app._v84Catalog.query") == "Food 3289"
            page.locator('#tabs .tab[data-tab="today"]').click()
            assert page.evaluate("app._tab") == "today"
            assert not errors, errors
            print(f"PASS {width}: stock screen responsive; {result}", flush=True)
            page.close()
        browser.close()


if __name__ == "__main__":
    run()
