"""Actual delivered frontend: seasonal choices, localization and saved view state."""
from datetime import datetime, timezone
from pathlib import Path
import os
import shutil

from playwright.sync_api import expect, sync_playwright
from ui_offline_loader_v203 import local_html

ROOT=Path(__file__).resolve().parents[1]

def run():
    html=local_html(ROOT)
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH') or shutil.which('chromium') or None,args=['--no-sandbox'])
        for width,height in ((390,844),(1440,980)):
            page=browser.new_page(viewport={'width':width,'height':height})
            page.clock.install(time=datetime(2026,9,25,12,tzinfo=timezone.utc))
            errors=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.set_default_timeout(6000)
            page.set_content(html)
            page.wait_for_function('window.ready')
            page.evaluate("""() => {
                const season=(de,gr)=>({seasonality:{status:'reviewed',regions:[{country:'DE',months:de},{country:'GR',months:gr}]}});
                const rows=[
                    {key:'apple',name:'Μήλο',market:'Apfel',lifecycle:season([9,10],[9,10])},
                    {key:'asparagus',name:'Σπαράγγι',market:'Spargel',lifecycle:season([4,5,6],[9,10])},
                    {key:'strawberry',name:'Φράουλα',market:'Erdbeere',lifecycle:season([5,6,7],[5,6,7])},
                    {key:'frozen',name:'Κατεψυγμένα σπαράγγια',market:'Tiefkühlspargel'},
                    {key:'rice',name:'Ρύζι',market:'Reis'}
                ];
                window.catalog=rows.map(row=>({...row,ingredientId:row.key,presentationVersion:63,displayLanguage:'el',searchAliases:[row.name,row.market]}));
                app._ingredientCatalog=catalog;app._ingredientCatalogLanguage='el';
                app._v79Settings={country:'DE',supermarketLanguage:'de'};
                app._v140MarketNames=new Map(rows.map(row=>[row.key,row.market]));
                app._v140MarketCatalogKey=app._prefKey()+':de';
                window.preferences=[];
                app._hass.connection.sendMessagePromise=async message=>{
                    if(message.preferences)preferences.push(structuredClone(message.preferences));
                    return message.type.endsWith('/ingredient_catalog')?{items:rows.map(row=>({...row,name:row.market}))}:{};
                };
                app.show('profile');
            }""")
            section=page.locator('[data-v84-catalog]')
            toggle=section.locator('[data-v223-toggle]')
            expect(toggle).not_to_be_checked()
            assert section.locator('option').count()==6
            expect(section.locator('[data-v223-season] label')).to_have_text('Υλικά εποχής (Saisonale Zutaten)')
            assert 'Deutschland · September' in section.locator('[data-v223-season] small').inner_text()
            toggle.check()
            assert section.locator('option').count()==4
            assert 'Μήλο (Apfel)' in section.locator('select').inner_text()
            assert page.evaluate('preferences.at(-1).filtersByView.profile.seasonalIngredients') is True
            section.locator('[data-v84-search]').fill('Spargel')
            assert section.locator('option').count()==2  # preserved food stays available
            section.locator('[data-v84-search]').fill('')

            # Scanner shares the current view's toggle and retains assigned rows.
            page.evaluate("""async () => {
                await app._v78Open('manual');
                app._v78Draft.ingredient=catalog[1];app._v78Draft.ingredientLinks=[catalog[1]];
                app._v78Draft.suggestions=catalog.map(ingredient=>({ingredient,reason:'name'}));
                app._v78IngredientOptions();
            }""")
            picker=page.locator('[data-v114-links]')
            expect(picker.locator('[data-v223-toggle]')).to_be_checked()
            assert picker.locator('[data-v114-link]').count()==4
            assert page.locator('[data-v194-index]').count()==4
            selected=picker.locator('label').filter(has_text='Σπαράγγι (Spargel)').locator('input')
            expect(selected).to_be_checked()
            selected.click()
            assert picker.locator('[data-v114-link]').count()==3
            picker.locator('[data-v223-toggle]').uncheck()
            assert picker.locator('[data-v114-link]').count()==5
            assert page.locator('[data-v194-index]').count()==5
            expect(section.locator('[data-v223-toggle]')).not_to_be_checked()
            page.evaluate('app._v78Dirty=false;app._v78Close();app.show("today");app._showFilter("ingredients")')

            overlay=page.locator('[data-filter-dialog="ingredients"]')
            toggle=overlay.locator('[data-v223-toggle]')
            expect(toggle).not_to_be_checked()
            asparagus=overlay.locator('[data-list="ingredients"][value="k:asparagus"]')
            asparagus.check();toggle.check()
            expect(asparagus).to_be_visible()
            expect(overlay.locator('[value="k:strawberry"]')).to_be_hidden()
            overlay.locator('[data-ingredient-search]').fill('Spargel')
            expect(asparagus).to_be_visible()
            asparagus.uncheck()
            expect(asparagus).to_be_hidden()
            toggle.uncheck();expect(asparagus).to_be_visible()
            toggle.check()
            overlay.locator('[data-v124-select-all=ingredients]').click()
            expect(asparagus).not_to_be_checked()
            expect(overlay.locator('[value="k:strawberry"]')).not_to_be_checked()
            expect(overlay.locator('[value="k:frozen"]')).to_be_checked()
            overlay.locator('[data-v124-deselect-all=ingredients]').click()
            assert overlay.locator('[data-list=ingredients]:checked').count()==0
            overlay.locator('[data-apply]').click()
            assert page.evaluate('app._filters().seasonalIngredients') is True
            assert page.evaluate('preferences.at(-1).filtersByView.today.seasonalIngredients') is True
            page.evaluate('app._showFilter("ingredients")')
            expect(overlay.locator('[data-v223-toggle]')).to_be_checked()

            # Same language, different shopping country: an open picker refreshes.
            page.evaluate("app._v79Settings.country='GR';app._v140LoadSupermarketCatalog()")
            expect(overlay.locator('[value="k:asparagus"]')).to_be_visible()
            assert 'Griechenland' in overlay.locator('[data-v223-season] small').inner_text()
            page.evaluate("app._v79Settings.country='AU';app._v140LoadSupermarketCatalog()")
            expect(overlay.locator('[value="k:strawberry"]')).to_be_visible()
            page.evaluate("app._v63CloseFilter();app.show('week');app._showFilter('ingredients')")
            expect(overlay.locator('[data-v223-toggle]')).not_to_be_checked()
            page.evaluate("app._v63CloseFilter();app.show('today');app._showFilter('ingredients')")
            expect(overlay.locator('[data-v223-toggle]')).to_be_checked()

            page.evaluate("app.shadowRoot.getAnimations().forEach(animation=>{if(animation.effect.getComputedTiming().iterations!==Infinity)animation.finish()})")
            # Rendered control fits both viewport sizes.
            assert overlay.locator('.rx-dialog').evaluate('(node)=>node.scrollWidth<=node.clientWidth+2')
            if os.environ.get('SCREENSHOT_DIR'):
                path=Path(os.environ['SCREENSHOT_DIR']);path.mkdir(parents=True,exist_ok=True)
                page.screenshot(path=str(path/f'season-filter-{width}.png'))
            assert not errors,errors
            page.close()
            print(f'PASS season filter: {width}px, selection, languages, markets, persistence')
        browser.close()

if __name__=='__main__':run()
