"""Seasonal gap fixes in Greek/German and confirmed upright juice handling."""
from datetime import datetime, timezone
from pathlib import Path
import shutil

from playwright.sync_api import expect, sync_playwright
from test_catalog_lifecycle_v230 import catalog, opening
from ui_offline_loader_v203 import local_html

ROOT = Path(__file__).resolve().parents[1]


def run():
    ids = {'M_FOOD_107', 'M_FOOD_412', 'M_FOOD_258'}
    catalogs = {lang: [r for r in catalog.ingredient_choices(lang) if r.get('key') in ids] for lang in ('el', 'de')}
    ingredient = next(r for r in catalogs['el'] if r.get('key') == 'M_FOOD_258')
    lot = {'brand': 'dmBio', 'barcode': '4066447855494'}
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
            for month, present in ((3, {'M_FOOD_107'}), (4, {'M_FOOD_412'}),
                                   (5, {'M_FOOD_107', 'M_FOOD_412'}),
                                   (8, {'M_FOOD_107', 'M_FOOD_412'}),
                                   (11, {'M_FOOD_107', 'M_FOOD_412'}), (12, {'M_FOOD_107'})):
                page.clock.set_system_time(datetime(2026, month, 15, 12, tzinfo=timezone.utc))
                section.locator('[data-v223-toggle]').uncheck();section.locator('[data-v223-toggle]').check()
                for ident in ids - {'M_FOOD_258'}:
                    name = next(r['name'] for r in catalogs['el'] if r.get('key') == ident)
                    expect(section.locator('option').filter(has_text=name)).to_have_count(int(ident in present))
                    if ident in present:
                        german = next(r['name'] for r in catalogs['de'] if r.get('key') == ident)
                        expect(section.locator('option').filter(has_text=name)).to_contain_text(german)
                expect(section.locator('option').filter(has_text=ingredient['name'])).to_have_count(1)
            page.clock.set_system_time(datetime(2026, 9, 25, 12, tzinfo=timezone.utc))
            page.evaluate("""async ({ingredient,lot}) => {
                await app._v78Open('manual');
                Object.assign(app._v78Draft,lot,{productName:'Orangensaft',quantity:1,unit:'l',
                    ingredient,ingredientLinks:[ingredient],editorOpen:true,bestBefore:'2099-12-31'});
                app._v78RenderCapture();
            }""", {'ingredient': ingredient, 'lot': lot})
            page.locator('main [data-draft="useWithinDays"]').locator('xpath=ancestor::details').locator('summary').click()
            select = page.locator('[data-v222-rule]')
            expect(select.locator('option[value="dmbio_orange_juice"]')).to_have_text('3 ημέρες · dmBio')
            select.select_option('dmbio_orange_juice')
            expect(page.locator('[data-v222-editor]')).to_contain_text('Διατήρηση σε όρθια θέση')
            expect(page.locator('[data-v222-opened]')).to_be_disabled()
            page.locator('[data-v222-conditions]').check()
            page.locator('[data-v222-apply]').check();page.locator('[data-v222-opened]').check()
            expect(page.locator('main [data-draft="useWithinDays"]')).to_have_value('3')
            assert page.evaluate("app._v78Draft.openedAt==='2026-09-25' && app._v78Draft.applyOpeningExpiry")
            assert not errors, errors
            print(f'PASS {width}: March/April/May/August/November/December seasons and upright juice guidance')
            page.close()
        browser.close()


if __name__ == '__main__':
    run()
