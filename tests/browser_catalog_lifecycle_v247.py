"""Batch 31: BBQ/horseradish season filtering and exact opening clocks in the real UI."""
from datetime import datetime, timezone
from pathlib import Path
import re
import shutil

from playwright.sync_api import expect, sync_playwright
from test_catalog_lifecycle_v231 import actual_choice
from test_catalog_lifecycle_v227 import catalog, opening
from ui_offline_loader_v203 import local_html

ROOT = Path(__file__).resolve().parents[1]


def run():
    source = catalog.load_release_catalog()['ingredients']

    def ident(canonical):
        return next(
            row['id'] for row in source
            if row.get('canonicalName') == canonical
            and row.get('classification') in (None, 'food')
            and not row.get('needsSemanticConfirmation')
        )

    ids = {
        'bbq': ident('Barbecue sauce'),
        'honey_bbq': ident('Honey barbecue sauce'),
        'horseradish': ident('Horseradish'),
        'horseradish_sauce': ident('Horseradish sauce'),
        'daikon': ident('Daikon radish'),
    }
    catalogs = {}
    for lang in ('el', 'de'):
        rows = catalog.ingredient_choices(lang)
        catalogs[lang] = list({actual_choice(rows, value)['id']: actual_choice(rows, value) for value in ids.values()}.values())

    scenarios = (
        {
            'ingredient': actual_choice(catalogs['el'], ids['bbq']),
            'lot': {'brand': 'Heinz', 'barcode': '8715700036106'},
            'rule': 'heinz_barbecue_10l',
            'days': 14,
            'expiry': '2026-10-10',
            'rules': opening.opening_rules({'ingredientId': ids['bbq']}, {'brand': 'Heinz', 'barcode': '8715700036106'}),
        },
        {
            'ingredient': actual_choice(catalogs['el'], ids['bbq']),
            'lot': {'brand': 'Heinz', 'barcode': '8715700036113'},
            'rule': 'heinz_barbecue_10l',
            'days': 14,
            'expiry': '2026-10-10',
            'rules': opening.opening_rules({'ingredientId': ids['bbq']}, {'brand': 'Heinz', 'barcode': '8715700036113'}),
        },
        {
            'ingredient': actual_choice(catalogs['el'], ids['honey_bbq']),
            'lot': {'brand': 'Heinz', 'barcode': '8715700036106'},
            'rule': 'heinz_barbecue_10l',
            'days': 14,
            'expiry': '2026-10-10',
            'rules': opening.opening_rules({'ingredientId': ids['honey_bbq']}, {'brand': 'Heinz', 'barcode': '8715700036106'}),
        },
        {
            'ingredient': actual_choice(catalogs['el'], ids['horseradish_sauce']),
            'lot': {'brand': 'Byodo', 'barcode': '4018462160558'},
            'rule': 'byodo_tafelmeerrettich_100',
            'days': 21,
            'expiry': '2026-10-17',
            'rules': opening.opening_rules({'ingredientId': ids['horseradish_sauce']}, {'brand': 'Byodo', 'barcode': '4018462160558'}),
        },
        {
            'ingredient': actual_choice(catalogs['el'], ids['horseradish']),
            'lot': {'brand': 'Byodo', 'barcode': '4018462160558'},
            'rule': 'byodo_tafelmeerrettich_100',
            'days': 21,
            'expiry': '2026-10-17',
            'rules': opening.opening_rules({'ingredientId': ids['horseradish']}, {'brand': 'Byodo', 'barcode': '4018462160558'}),
        },
    )
    html = local_html(ROOT).replace(
        '_api(type,data={}){\n  this.calls.push',
        '_api(type,data={}){\n  if(type.endsWith("/opening_guidance"))return super._api(type,data);\n  this.calls.push',
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=shutil.which('chromium'), args=['--no-sandbox'])
        for width, height in ((390, 844), (1440, 980)):
            page = browser.new_page(viewport={'width': width, 'height': height})
            page.clock.install(time=datetime(2026, 9, 26, 12, tzinfo=timezone.utc))
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.set_default_timeout(6000)
            page.set_content(html)
            page.wait_for_function('window.ready')
            page.evaluate(
                """async catalogs => {
                    app._ingredientCatalog=catalogs.el;app._ingredientCatalogLanguage='el';
                    app._v79Settings={country:'DE',supermarketLanguage:'de'};
                    app._hass.connection.sendMessagePromise=async msg=>{
                        if(msg.type.endsWith('/job_run'))return app._hass.connection.sendMessagePromise(msg.request);
                        if(msg.type.endsWith('/ingredient_catalog'))return {items:catalogs[msg.language]};
                        if(msg.type.endsWith('/opening_guidance'))return {rules:window.offeredRules||[]};
                        return {};
                    };
                    await app._v140LoadSupermarketCatalog(true);app.show('profile');
                }""",
                catalogs,
            )
            section = page.locator('[data-v84-catalog]')

            def option(key):
                name = actual_choice(catalogs['el'], ids[key])['name']
                return section.locator('option').filter(has_text=re.compile('^' + re.escape(name) + r'(?: \\(|$)'))

            section.locator('[data-v223-toggle]').uncheck()
            for key, german in (
                ('bbq', 'BBQ-Sauce'),
                ('honey_bbq', 'Honig-BBQ-Sauce'),
                ('horseradish', 'Meerrettich'),
                ('horseradish_sauce', 'Meerrettichsauce'),
                ('daikon', 'Daikon-Rettich'),
            ):
                expect(option(key)).to_contain_text(german)

            for month in range(1, 13):
                page.clock.set_system_time(datetime(2026, month, 15, 12, tzinfo=timezone.utc))
                section.locator('[data-v223-toggle]').uncheck()
                section.locator('[data-v223-toggle]').check()
                expect(option('horseradish')).to_have_count(1 if month == 10 else 0)
                for key in ('bbq', 'honey_bbq', 'horseradish_sauce', 'daikon'):
                    expect(option(key)).to_have_count(1)

            section.locator('[data-v223-toggle]').uncheck()
            page.clock.set_system_time(datetime(2026, 9, 26, 12, tzinfo=timezone.utc))
            for scenario in scenarios:
                page.evaluate(
                    """async ({ingredient,lot,rules}) => {
                        window.offeredRules=rules;await app._v78Open('manual');
                        Object.assign(app._v78Draft,{...lot,productName:ingredient.name,quantity:210,unit:'g',
                            ingredient,ingredientLinks:[ingredient],editorOpen:true,bestBefore:'2099-12-31'});
                        app._v78RenderCapture();
                    }""",
                    scenario,
                )
                page.locator('main [data-draft="useWithinDays"]').locator('xpath=ancestor::details').locator('summary').click()
                selected = page.locator('[data-v222-rule]')
                expected = int(bool(scenario['rules']))
                expect(selected.locator('option[value="' + scenario['rule'] + '"]')).to_have_count(expected)
                if scenario['rules']:
                    selected.select_option(scenario['rule'])
                    expect(page.locator('[data-v222-opened]')).to_be_disabled()
                    page.locator('[data-v222-conditions]').check()
                    page.locator('[data-v222-apply]').check()
                    page.locator('[data-v222-opened]').check()
                    expect(page.locator('main [data-draft="useWithinDays"]')).to_have_value(str(scenario['days']))
                    expect(page.locator('[data-v222-expiry]')).to_contain_text(scenario['expiry'])
                page.evaluate('app._v78Close(true)')

            assert not errors, errors
            print(f'PASS {width}: BBQ and horseradish German names, October season filter, exact opening clocks and form exclusions')
            page.close()
        browser.close()


if __name__ == '__main__':
    run()
