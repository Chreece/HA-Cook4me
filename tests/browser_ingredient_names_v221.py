"""Exercise ingredient naming through the delivered frontend and offline HA reads."""
from pathlib import Path
import shutil

from playwright.sync_api import expect, sync_playwright
from ui_offline_loader_v203 import local_html

ROOT = Path(__file__).resolve().parents[1]


def run():
    html = local_html(ROOT)
    html = html.replace(
        "_api(type,data={}){\n  this.calls.push",
        "_api(type,data={}){\n  if(/\\/(ingredient_info|ingredient_catalog)$/.test(type))return super._api(type,data);\n  this.calls.push",
    )
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=shutil.which("chromium") or None, args=["--no-sandbox"])
        for width, height in ((390, 844), (1440, 980)):
            page = browser.new_page(viewport={"width": width, "height": height})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.set_default_timeout(6000)
            page.set_content(html)
            page.wait_for_function("window.ready")
            page.evaluate("""() => {
                window.uiRows=[{key:'rice',ingredientId:'catalog-rice',sourceIngredientIds:['fr-rice'],
                    name:'Ρύζι',presentationVersion:63,displayLanguage:'el'}];
                app._ingredientCatalog=uiRows;app._ingredientCatalogLanguage='el';
                app._v140MarketNames=new Map([['rice','Reis']]);
                app._v140MarketCatalogKey=app._prefKey()+':de';
                window.requests=[];
                app._hass.connection.sendMessagePromise=async msg => {
                    if(msg.type.endsWith('/job_run'))return app._hass.connection.sendMessagePromise(msg.request);
                    requests.push(structuredClone(msg));
                    if(msg.type.endsWith('/ingredient_info'))return {
                        ingredientInfoContract:'offline-ingredient-info-v62',ingredient:{name:'Ρύζι'},
                        stock:null,history:[],savedRecipeUsage:[],officialRecipeUsage:[],nutritionReferences:[]
                    };
                    if(msg.type.endsWith('/ingredient_catalog')){
                        if(msg.language==='de')return {items:[{key:'rice',name:'Reis'}],presentationVersion:63};
                        if(msg.language==='it')return new Promise(resolve=>window.finishMarket=resolve);
                        return {items:uiRows,presentationVersion:63};
                    }
                    return {};
                };
                window.namingRecipe={...samples(0),language:'fr',selectedLanguage:'fr',ingredients:[
                    {key:'rice',ingredientId:'fr-rice',name:'Riz',originalName:'Riz',displayName:'Ρύζι',displayLanguage:'el',quantity:200,unit:'g'}
                ],match:{...samples(0).match,quantityAvailability:[{key:'rice',status:'partial',coverage:.75}]}};
                window.originalIngredients=JSON.stringify(namingRecipe.ingredients);
                app._todayResults=[namingRecipe];const state=app._v66State(namingRecipe);
                state.expanded=true;state.sections.add('ingredients');app.show('today');
                app._ingredientCatalog=uiRows;app._ingredientCatalogLanguage='el';app._v221RefreshNames();
            }""")
            name = page.locator('[data-v221-ingredient-name]').first
            expect(name).to_have_text("Ρύζι (Reis, Riz)")
            row = page.locator('[data-v66-ingredient="0"]').first
            assert row.locator('.rx-v66-quantity').count() == 1
            assert "200" in row.locator('.rx-v66-quantity').inner_text()
            assert row.locator('.chip').inner_text() == "75%"
            assert row.locator('.v218-stored-at').count() == 1
            row.click()
            heading = page.locator('[data-ingredient-dialog] .detail-head h2')
            expect(heading).to_have_text("🥕 Ρύζι (Reis, Riz)")
            assert page.evaluate("requests.find(r=>r.type.endsWith('/ingredient_info')).ingredient.name") == "Riz"
            page.locator('[data-ingredient-dialog] [data-close]').click()

            # Fullscreen uses the same names and keeps the ingredient's identity.
            page.locator('[data-v66-photo]').first.click()
            full = page.locator('.rx-v66-fullscreen')
            expect(full.locator('[data-v221-ingredient-name]')).to_have_text("Ρύζι (Reis, Riz)")
            full.locator('[data-v66-ingredient="0"]').click()
            expect(heading).to_have_text("🥕 Ρύζι (Reis, Riz)")

            # A delayed market switch updates the open info window and underlying
            # recipe without rebuilding either dialog or moving focus.
            page.evaluate("""() => {
                window.infoNode=app.shadowRoot.querySelector('[data-ingredient-dialog]');
                window.recipeNode=app._v63RecipeDialog;
                app._v79Settings.supermarketLanguage='it';
                window.marketLoading=app._v140LoadSupermarketCatalog(true);
            }""")
            page.wait_for_function("typeof finishMarket==='function'")
            page.evaluate("finishMarket({items:[{key:'rice',name:'Riso'}],presentationVersion:63})")
            page.wait_for_function("app.shadowRoot.querySelector('[data-ingredient-dialog] h2').textContent==='🥕 Ρύζι (Riso, Riz)'")
            assert page.evaluate("infoNode===app.shadowRoot.querySelector('[data-ingredient-dialog]') && recipeNode===app._v63RecipeDialog")
            expect(full.locator('[data-v221-ingredient-name]')).to_have_text("Ρύζι (Riso, Riz)")
            page.locator('[data-ingredient-dialog] [data-close]').click()
            page.locator('[data-modal-close]').click()

            # The catalog entry has no recipe name to repeat. Duplicate language
            # labels collapse, and unknown handwritten ingredients stay readable.
            page.evaluate("app._showIngredientInfo(uiRows[0])")
            expect(heading).to_have_text("🥕 Ρύζι (Riso)")
            page.locator('[data-ingredient-dialog] [data-close]').click()
            page.evaluate("""() => {
                app._v79Settings.supermarketLanguage='de';
                app._v140MarketNames=new Map([['rice','Riz']]);app._v140MarketCatalogKey=app._prefKey()+':de';
                app._renderTab();
            }""")
            expect(name).to_have_text("Ρύζι (Riz)")
            assert page.evaluate("JSON.stringify(namingRecipe.ingredients)===originalIngredients")
            assert not errors, errors
            print(f"PASS {width}: recipe list, fullscreen, info window, delayed catalog, duplicate names and original identity", flush=True)
            page.close()
        browser.close()


if __name__ == "__main__":
    run()
