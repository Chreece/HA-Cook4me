"""Audit the current Cook4Me recipe panel for ALL stock badge categories.

Chromium loads the real bundled frontend; only pantry fixtures are synthetic.
No Home Assistant services, physical cooker, credentials or inventory writes.
"""
from pathlib import Path
import shutil
from playwright.sync_api import sync_playwright
from ui_offline_loader_v203 import local_html

ROOT=Path(__file__).resolve().parents[1]
html=local_html(ROOT)
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=shutil.which("chromium") or None,
                              args=["--no-sandbox"])
    for width in (390,1440):
        page=browser.new_page(viewport={"width":width,"height":880},
                              is_mobile=width==390,has_touch=width==390)
        errors=[]
        page.on("pageerror",lambda error:errors.append(str(error)))
        page.set_default_timeout(12000)
        page.set_content(html)
        page.wait_for_function("window.ready")
        result=page.evaluate("""() => {
            // Explicitly linked multilingual pantry products and several
            // unrelated items with identical display names.
            app._ingredientCatalog=[
              {key:'salt',name:'Αλάτι'},
              {key:'pepper',name:'Πιπέρι'},
              {key:'water',name:'Νερό'},
              {key:'rice',name:'Ρύζι'},
              {key:'cooked-rice',name:'Ρύζι'}
            ];
            app._v219IdentityCache=null;
            app._houseIngredients=[
              {key:'packaged-salt',name:'Αλάτι',unlimited:true,
               storageLocationId:'spices',ingredientLinks:[{key:'salt',name:'Αλάτι'}]},
              {key:'pepper',name:'Pfeffer',unlimited:true,
               storageLocationId:'spices'},
              {key:'water',name:'水',unlimited:true,
               storageLocationId:'pantry'},
              {key:'rice',name:'Ρύζι',unit:'g',quantity:500,
               lots:[{id:'rice-1',quantity:500,storageLocationId:'pantry'}]},
              {key:'empty-rice',name:'Ρύζι',unit:'g',quantity:1000,
               lots:[{id:'empty-1',quantity:0,storageLocationId:'pantry'}]}
            ];
            app._v78Locations=()=>[
              {id:'spices',name:'Ντουλάπι μπαχαρικών'},
              {id:'pantry',name:'Ντουλάπι'}
            ];
            const ingredient=(key,name,quantity,unit)=>
              ({key,name,foodName:name,quantity,unit});
            const ingredients=[
              ingredient('salt','Αλάτι',null,'g'),
              ingredient('pepper','Pfeffer',1,'unknown:measure'),
              ingredient('water','水',null,''),
              ingredient('rice','米',200,'g'),
              ingredient('rice','쌀',200,'g'),
              ingredient('cooked-rice','Ρύζι',50,'g'),
              ingredient('unrelated','Αλάτι',100,'g'),
              ingredient('empty-rice','Ρύζι',100,'g')
            ];
            const status=[
              {status:'unknown_requirement',coverage:null},
              {status:'incompatible_unit',coverage:null},
              {status:'unknown_requirement',coverage:null},
              {status:'enough',coverage:.5},
              {status:'shortage',coverage:.25},
              {status:'shortage',coverage:0},
              {status:'shortage',coverage:0},
              {status:'shortage',coverage:0}
            ];
            const recipe={
              title:'Generic pantry audit',language:'ko',ingredients,
              match:{quantityAvailability:status.map((row,i)=>({
                ...row,ingredientIndex:i,key:ingredients[i].key
              })),quantityCoverage:.25,quantityConfidence:.5}
            };
            const before=JSON.stringify(recipe);
            const coverage=ingredients.map(item=>app._coverage(recipe,item));
            const html=app._v66Body(recipe,false,{sections:new Set(['ingredients'])});
            const root=document.createElement('div');root.innerHTML=html;
            const display=[...root.querySelectorAll('[data-v66-ingredient]')]
             .map(button=>{
               const chip=[...button.querySelectorAll('.chip')].find(el=>
                 !!el.querySelector('ha-icon[icon="mdi:home-outline"]'));
               return {
                 index:Number(button.dataset.v66Ingredient),
                 chip:chip?.textContent?.trim(),
                 title:chip?.getAttribute('title')||'',
                 unlimited:chip?.dataset.v293Unlimited==='true',
                 price:button.querySelector('.v79-item-price')?.textContent||''
               };
             });
            const locations=ingredients.map(item=>app._v218StorageNames(item));
            return {coverage,display,locations,
                    unchanged:JSON.stringify(recipe)===before,
                    active:app.tagName.toLowerCase()};
        }""")
        assert result["unchanged"],result
        actual=[row["chip"] for row in result["display"]]
        assert actual==["∞","∞","∞","50%","25%","0%","0%","0%"],result
        assert [row["unlimited"] for row in result["display"][:3]]==[True]*3,result
        assert all("Απεριόριστο" in row["title"] for row in result["display"][:3]),result
        assert "Ντουλάπι" in result["display"][0]["title"],result
        assert result["coverage"][0]["unlimited"] is True,result
        assert all(row["percent"]==100 for row in result["coverage"][:3]),result
        assert result["coverage"][6]["percent"]==0,result
        assert result["coverage"][7]["percent"]==0,result
        assert result["locations"][6]==[],result
        assert result["locations"][7]!=[],result
        # The storage location alone must never turn a depleted lot into stock.
        assert result["coverage"][7]["status"]=="shortage",result
        assert not errors,errors
        print(f"PASS {width}px: unlimited salt/pepper/water, allocated rice, zero lots, incompatible units and safe multilingual identities",flush=True)
        page.close()
    browser.close()
