"""Real current frontend: unlimited pantry ingredients across recipe languages.

Test both the final inherited recipe renderer and actual linked inventory
presentation at phone and desktop widths. No live Home Assistant access.
"""
from pathlib import Path
import shutil
from playwright.sync_api import sync_playwright
from ui_offline_loader_v203 import local_html

ROOT=Path(__file__).resolve().parents[1]
HTML=local_html(ROOT)

with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=shutil.which("chromium") or None,
                              args=["--no-sandbox"])
    for width in (390,1440):
        page=browser.new_page(viewport={"width":width,"height":850},
                              is_mobile=width==390,has_touch=width==390)
        errors=[]
        page.on("pageerror",lambda e:errors.append(str(e)))
        page.set_default_timeout(12000)
        page.set_content(HTML)
        page.wait_for_function("window.ready")
        page.evaluate("app.show('official')")
        result=page.evaluate("""() => {
          app._ingredientCatalog=[
            {key:'salt-bin',name:'Αλάτι'},
            {key:'salt-ko',name:'소금'},
            {key:'salt-ja',name:'塩'},
            {key:'wrong',name:'Αλάτι'}
          ];
          app._v219IdentityCache=null;
          app._houseIngredients=[
            {key:'salt-bin',name:'Αλάτι',unlimited:true,
             storageLocationId:'pantry',ingredientLinks:[
              {key:'salt-ko',name:'소금'},
              {key:'salt-ja',name:'塩'}]}
          ];

          const inspect=(key,name,quantity,match)=>{
            const item={key,name,foodName:name,quantity,unit:'g'};
            const recipe={ingredients:[item],language:'ko',
             match:{quantityAvailability:[{key,status:'unknown_requirement',
                coverage:null}],quantityConfidence:0,quantityCoverage:1,
                ingredientAvailability:[{key,status:'missing'}],...match}};
            const coverage=app._coverage(recipe,item);
            const location=app._v218StorageNames(item);
            const html=app._v66Body(recipe,false,{sections:new Set(['ingredients'])});
            const root=document.createElement('section');root.innerHTML=html;
            const chip=root.querySelector('[data-v66-ingredient] .chip');
            return {coverage,location,chip:chip?.textContent?.trim()||'',
                title:chip?.getAttribute('title')||'',
                unlimited:chip?.dataset.v293Unlimited||'',
                rendered:!!chip};
          };
          const ko=inspect('salt-ko','소금',null);
          const ja=inspect('salt-ja','塩',null);
          const salty=inspect('salt-ko','소금',2);
          const wrong=inspect('wrong','Αλάτι',null);
          app._houseIngredients=[];
          const removed=inspect('salt-ko','소금',null);
          return {ko,ja,salty,wrong,removed};
        }""")

        for lang in ("ko","ja"):
            row=result[lang]
            assert row["rendered"],row
            assert row["coverage"]["percent"]==100,row
            assert row["coverage"]["unlimited"] is True,row
            assert row["coverage"]["displayLabel"]=="∞",row
            assert "∞" in row["chip"],row
            assert row["unlimited"]=="true",row
            assert "Απεριόριστο" in row["title"],row
            assert "Ντουλάπι" in row["location"],row

        assert result["salty"]["coverage"]["percent"]==100,result
        assert "∞" in result["salty"]["chip"],result
        assert result["wrong"]["coverage"]["percent"] is None,result
        assert result["wrong"]["unlimited"]=="",result
        assert result["removed"]["unlimited"]=="",result
        assert result["removed"]["coverage"]["percent"] is None,result
        assert not errors,errors
        print(f"PASS {width}px: stored infinite salt in Korean and Japanese; "
              "real location, no false foreign name match, unknown after stock removal",
              flush=True)
        page.close()
    browser.close()
