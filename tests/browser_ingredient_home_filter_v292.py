"""Merged Ingredients/Home filter and linked Japanese/Korean rice stock on the
actual current Cook4Me frontend. Device/network boundaries use demo fixtures.
"""
from pathlib import Path
import shutil
from playwright.sync_api import expect, sync_playwright
from ui_offline_loader_v203 import local_html

ROOT=Path(__file__).resolve().parents[1]
HTML=local_html(ROOT)
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=shutil.which('chromium') or None,
                              args=['--no-sandbox'])
    for width in (390,1440):
        page=browser.new_page(viewport={'width':width,'height':850},
                              is_mobile=width==390,has_touch=width==390)
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.set_default_timeout(12000)
        page.set_content(HTML)
        page.wait_for_function('window.ready')
        page.evaluate("app.show('official')")
        assert page.locator('[data-filter="home"]').count()==0
        assert page.locator('[data-filter="ingredients"]').count()==1

        page.evaluate("""() => {
            const f=app._filters();
            f.onlyHome=true;
            f.preferExpiring=true;
            f.maxMissing=1;
            f.avoidRecentDays=7;
            f.ingredients=['k:rice'];
            app._showFilter('ingredients');
        }""")
        overlay=page.locator('[data-filter-dialog="ingredients"]')
        expect(overlay).to_have_count(1)
        assert overlay.locator('[data-v292-home]').count()==1
        for field in ['onlyHome','preferExpiring','maxMissing','avoidRecentDays']:
            expect(overlay.locator(f'[data-v292-home] [data-field="{field}"]')).to_have_count(1)
        assert overlay.locator('[data-v223-season]').count()==1
        fold=overlay.locator('[data-v292-fold]')
        expect(fold).to_have_attribute('aria-expanded','false')
        expect(fold).to_contain_text('1 επιλεγμένα')
        assert overlay.locator('[data-ingredient-choices]').is_hidden()
        assert overlay.locator('[data-ingredient-search]').is_hidden()
        assert overlay.locator('[data-v124-bulk="ingredients"]').is_hidden()
        fold.click()
        expect(fold).to_have_attribute('aria-expanded','true')
        assert overlay.locator('[data-ingredient-search]').is_visible()
        assert overlay.locator('[data-ingredient-choices]').is_visible()
        assert overlay.locator('[data-v124-bulk="ingredients"]').is_visible()
        assert overlay.locator('[data-v223-season]').is_visible()
        # Preserve selection and all original handlers; changing stock controls
        # must not collapse/recreate selected ingredient data.
        overlay.locator('[data-field="onlyHome"]').uncheck()
        overlay.locator('[data-field="preferExpiring"]').uncheck()
        overlay.locator('[data-field="maxMissing"]').fill('2')
        overlay.locator('[data-field="avoidRecentDays"]').fill('9')
        overlay.locator('[data-apply]').click()
        assert page.evaluate("""() => {
            const f=app._filters();
            return f.onlyHome===false && f.preferExpiring===false &&
                   Number(f.maxMissing)===2 && Number(f.avoidRecentDays)===9 &&
                   f.ingredients.includes('k:rice');
        }""")
        assert page.locator('[data-filter="home"]').count()==0
        page.evaluate("app._showFilter('ingredients')")
        overlay=page.locator('[data-filter-dialog="ingredients"]')
        expect(overlay.locator('[data-v292-fold]')).to_have_attribute('aria-expanded','false')
        assert overlay.locator('[data-field="preferExpiring"]').is_checked() is False
        overlay.locator('[data-close]').click()

        # A dated recipe's availability might be cached as zero from an older
        # stock snapshot, while a Japanese/Korean source ingredient has been
        # assigned to a package. The UI must reflect that positive linked stock
        # without inventing enough grams or borrowing a translated name.
        result=page.evaluate("""() => {
            app._ingredientCatalog=[
                {key:'dry-rice',name:'Ρύζι',sourceIngredientIds:['rice-ja','rice-ko']},
                {key:'rice-ja',name:'米',sourceIngredientIds:['dry-rice','rice-ko']},
                {key:'rice-ko',name:'쌀',sourceIngredientIds:['dry-rice','rice-ja']}
            ];
            app._v219IdentityCache=null;
            app._houseIngredients=[{
                key:'dry-rice',name:'Ρύζι',unit:'g',quantity:500,
                lots:[{id:'stored-rice',quantity:500,storageLocationId:'pantry',
                       ingredientLinks:[{key:'rice-ja',name:'米'}]}]
            }];
            const item={key:'rice-ko',name:'쌀',foodName:'쌀',quantity:100,unit:'g'};
            const recipe={ingredients:[item],language:'ko',
              match:{quantityAvailability:[{key:'rice-ko',status:'shortage',
                    coverage:0,availableQuantity:0}],
                     ingredientAvailability:[{key:'rice-ko',status:'missing'}]}};
            const coverage=app._coverage(recipe,item);
            const place=app._v218StorageNames(item);
            const html=app._v66Body(recipe,false,{sections:new Set(['ingredients'])});
            const unrelated={key:'other-grain',name:'Ρύζι',quantity:100,unit:'g'};
            const unrelatedRecipe={...recipe,ingredients:[unrelated],
              match:{quantityAvailability:[{key:'other-grain',status:'shortage',coverage:0}]}};
            return {coverage,place,html,
                    unrelated:app._coverage(unrelatedRecipe,unrelated)};
        }""")
        assert result['coverage']['status']=='at_home_quantity_unverified',result
        assert result['coverage']['percent'] is None,result
        assert result['coverage']['displayLabel']=='Στο σπίτι',result
        assert 'Ντουλάπι' in result['place'],result
        assert 'Στο σπίτι' in result['html'],result
        assert result['unrelated']['percent']==0,result

        # Unlimited salt must be displayed as unlimited even when the recipe
        # was previously cached as missing/unknown. An unrelated salt-like
        # identity cannot borrow the quantity merely by sharing a label.
        salt=page.evaluate("""() => {
          app._ingredientCatalog=[
            {key:'salt',name:'Αλάτι',sourceIngredientIds:['salt-source']},
            {key:'salt-source',name:'Salt',sourceIngredientIds:['salt']}
          ];
          app._v219IdentityCache=null;
          app._houseIngredients=[
            {key:'salt-container',name:'Salt jar',unlimited:true,
             ingredientLinks:[{key:'salt-source',name:'Salt'}],
             storageLocationId:'pantry'}
          ];
          const item={key:'salt-source',name:'Αλάτι',quantity:null,unit:''};
          const recipe={ingredients:[item],
            match:{quantityAvailability:[{key:'salt-source',status:'missing',coverage:0}],
              ingredientAvailability:[{key:'salt-source',status:'missing'}]}};
          const coverage=app._coverage(recipe,item);
          const html=app._v66Body(recipe,false,{sections:new Set(['ingredients'])});
          const unrelated={key:'unrelated-salt',name:'Αλάτι',quantity:1,unit:'g'};
          const otherRecipe={ingredients:[unrelated],
             match:{quantityAvailability:[{key:'unrelated-salt',status:'missing',coverage:0}]}};
          return {coverage,html,unrelated:app._coverage(otherRecipe,unrelated)};
        }""")
        assert salt['coverage']['status']=='staple',salt
        assert salt['coverage']['percent']==100,salt
        assert salt['coverage']['displayLabel']=='∞',salt
        assert '∞' in salt['html'],salt
        assert salt['unrelated']['percent']==0,salt


        assert not errors,errors
        print(f'PASS {width}px: one merged filter, collapsed ingredient picker, persisted controls, Korean rice presence, unrelated-key safeguards',flush=True)
        page.close()
    browser.close()
