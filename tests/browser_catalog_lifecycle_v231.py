"""Winter produce, German supermarket labels and clean-spoon opening guidance."""
from datetime import datetime, timezone
from pathlib import Path
import shutil

from playwright.sync_api import expect, sync_playwright
from test_catalog_lifecycle_v231 import SEASONS, actual_choice, catalog, opening
from ui_offline_loader_v203 import local_html

ROOT = Path(__file__).resolve().parents[1]


def run():
    ids = {r[0] for r in SEASONS} | {'M_FOOD_265', 'local:ko:ebae66f49637679858fb', 'local:en:2d9f581b4fc8823f558a'}
    catalogs = {lang: [r for r in catalog.ingredient_choices(lang) if r.get('id') in ids] for lang in ('el', 'de')}
    ingredient = actual_choice(catalogs['el'], 'local:ko:ebae66f49637679858fb')
    lot = {'brand': 'dmBio', 'barcode': '4066447982046'}
    rules = opening.opening_rules(ingredient, lot)
    assert len(rules) == 1
    html = local_html(ROOT).replace('_api(type,data={}){\n  this.calls.push',
        '_api(type,data={}){\n  if(type.endsWith("/opening_guidance"))return super._api(type,data);\n  this.calls.push')
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=shutil.which('chromium') or None, args=['--no-sandbox'])
        for width, height in ((390, 844), (1440, 980)):
            page = browser.new_page(viewport={'width': width, 'height': height})
            page.clock.install(time=datetime(2026, 11, 15, 12, tzinfo=timezone.utc))
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.set_default_timeout(6000)
            page.set_content(html);page.wait_for_function('window.ready')
            page.evaluate("""async ({catalogs,rules,lot}) => {
                app._ingredientCatalog=catalogs.el;app._ingredientCatalogLanguage='el';
                app._v79Settings={country:'DE',supermarketLanguage:'de'};
                app._hass.connection.sendMessagePromise=async msg=>{
                    if(msg.type.endsWith('/job_run'))return app._hass.connection.sendMessagePromise(msg.request);
                    if(msg.type.endsWith('/ingredient_catalog'))return {items:catalogs[msg.language]};
                    if(msg.type.endsWith('/opening_guidance'))return {rules:msg.lot_metadata.barcode===lot.barcode?rules:[]};
                    return {};
                };
                await app._v140LoadSupermarketCatalog(true);app.show('profile');
            }""", {'catalogs': catalogs, 'rules': rules, 'lot': lot})
            section = page.locator('[data-v84-catalog]')
            expect(section.locator('[data-v223-season] label')).to_have_text('Υλικά εποχής (Saisonale Zutaten)')
            for month in (2, 4, 6, 9):
                page.clock.set_system_time(datetime(2026, month, 15, 12, tzinfo=timezone.utc))
                section.locator('[data-v223-toggle]').uncheck();section.locator('[data-v223-toggle]').check()
                for ident, months, _ in SEASONS:
                    name = actual_choice(catalogs['el'], ident)['name']
                    expect(section.locator('option').filter(has_text=name)).to_have_count(int(month in months))
                    if month in months:
                        german = actual_choice(catalogs['de'], ident)['name']
                        expect(section.locator('option').filter(has_text=name)).to_contain_text(german)
                for ident in ids - {r[0] for r in SEASONS}:
                    row = actual_choice(catalogs['el'], ident)
                    expect(section.locator('option').filter(has_text=row['name'])).to_have_count(1)
            for german in ('Feldsalat', 'Pflanzendrink', 'Ingwersaft'):
                expect(section.locator('option').filter(has_text=german)).to_have_count(1)
            for language, expected in (('en', 'Use a clean spoon'), ('de', 'Mit einem sauberen Löffel dosieren'),
                                       ('el', 'Χρήση καθαρού κουταλιού')):
                rendered = page.evaluate("""({language,rule}) => {
                    const previous=app._v222Lang;app._v222Lang=()=>language;
                    try{return app._v222Conditions(rule);}finally{app._v222Lang=previous;}
                }""", {'language': language, 'rule': rules[0]})
                assert expected in rendered, rendered
            page.clock.set_system_time(datetime(2026, 9, 25, 12, tzinfo=timezone.utc))
            page.evaluate("""async ({ingredient,lot}) => {
                await app._v78Open('manual');
                Object.assign(app._v78Draft,lot,{productName:'Ingwersaft',quantity:200,unit:'ml',
                    ingredient,ingredientLinks:[ingredient],editorOpen:true,bestBefore:'2099-12-31'});
                app._v78RenderCapture();
            }""", {'ingredient': ingredient, 'lot': lot})
            page.locator('main [data-draft="useWithinDays"]').locator('xpath=ancestor::details').locator('summary').click()
            select = page.locator('[data-v222-rule]')
            expect(select.locator('option[value="dmbio_ginger_juice"]')).to_have_text('14 ημέρες · dmBio')
            select.select_option('dmbio_ginger_juice')
            expect(page.locator('[data-v222-editor]')).to_contain_text('Χρήση καθαρού κουταλιού')
            expect(page.locator('[data-v222-opened]')).to_be_disabled()
            page.locator('[data-v222-conditions]').check()
            page.locator('[data-v222-apply]').check();page.locator('[data-v222-opened]').check()
            expect(page.locator('main [data-draft="useWithinDays"]')).to_have_value('14')
            assert page.evaluate("app._v78Draft.openedAt==='2026-09-25' && app._v78Draft.applyOpeningExpiry")
            assert not errors, errors
            print(f'PASS {width}: winter/summer calendars, German supermarket names and clean-spoon confirmation')
            page.close()
        browser.close()


if __name__ == '__main__':
    run()
