"""Permanent stock-removal UI checks in the real active frontend hierarchy.

Mock only backend/device requests; verify that the original expiry editor and
home-stock summary remain clickable and that the correct existing server
deletion command receives the exact identity or lot version.
"""
from pathlib import Path
import shutil
from playwright.sync_api import sync_playwright, expect
from ui_offline_loader_v203 import local_html

ROOT = Path(__file__).resolve().parents[1]
HTML = local_html(ROOT)

SETUP = r"""() => {
 window.removalRequests=[];
 window.confirmations=[];
 window.confirmDecision=false;
 window.confirm=(message)=>{confirmations.push(message);return confirmDecision;};
 const stock=[
  {key:'rice',name:'Ρύζι',unit:'g',quantity:500,lots:[
   {id:'lot-old',quantity:200,productName:'Ρύζι παλιό',bestBefore:'2026-10-17',storageLocationId:'pantry'},
   {id:'lot-new',quantity:300,productName:'Ρύζι νέο',bestBefore:'2026-12-20',storageLocationId:'pantry'}
  ]},
  {key:'carrot',name:'Καρότο',unit:'g',quantity:300,lots:[
   {id:'lot-carrot',quantity:300,productName:'Καρότο',bestBefore:'2026-10-20',storageLocationId:'fridge'}
  ]},
  {key:'salt',name:'Αλάτι',unit:'',unlimited:true}
 ];
 app._houseIngredients=stock;
 app._v78State.houseIngredients=stock;
 app._entry().profile.houseIngredients=stock;
 app._ingredientCatalog=stock.map(row=>({key:row.key,ingredientId:row.key,name:row.name}));
 const expiry=row=>({
  lotId:row.id,identity:'k:'+row.key,ingredientName:row.name,
  productName:row.lot.productName,quantity:row.lot.quantity,unit:'g',
  bestBefore:row.lot.bestBefore,effectiveBestBefore:row.lot.bestBefore,
  storageName:row.key==='rice'?'Ντουλάπι':'Ψυγείο',daysRemaining:row.key==='rice'?0:3
 });
 const summary=()=>({
  packageCount:app._houseIngredients.flatMap(row=>row.lots||[]).length,
  value:{totalsByCurrency:{EUR:4.9},pricedPackages:2,packageCount:2,exactPackages:2},
  nutrition:{totals:{energyKcal:2120},coveredPackages:2,packageCount:2},
  expiring:app._houseIngredients.flatMap(row=>(row.lots||[])
   .filter(lot=>lot.id==='lot-old'||lot.id==='lot-carrot')
   .map(lot=>expiry({key:row.key,name:row.name,id:lot.id,lot})))
 });
 app._v142StockSummary=summary();
 const api=app._api.bind(app);
 app._api=async (type,data={})=>{
  if(type==='cook4me/v33/product_details'){
   removalRequests.push({type,data:structuredClone(data)});
   const row=app._houseIngredients.find(x=>x.lots?.some(lot=>lot.id===data.lot_id));
   const lot=row?.lots?.find(lot=>lot.id===data.lot_id);
   if(!lot)throw Error('Lot not found');
   return {lot:structuredClone(lot),version:'v1',unit:row.unit,ingredient:{key:row.key,name:row.name}};
  }
  if(type==='cook4me/v33/product_remove'){
   removalRequests.push({type,data:structuredClone(data)});
   if(data.expected_version!=='v1')throw Error('Wrong version');
   const rows=structuredClone(app._houseIngredients);
   return {houseIngredients:rows.flatMap(row=>{
    if(!row.lots?.some(lot=>lot.id===data.lot_id))return [row];
    const lots=row.lots.filter(lot=>lot.id!==data.lot_id);
    return lots.length?[{...row,lots,quantity:lots.reduce((sum,lot)=>sum+Number(lot.quantity||0),0)}]:[];
   })};
  }
  if(type==='cook4me/v14/inventory_remove'){
   removalRequests.push({type,data:structuredClone(data)});
   return {houseIngredients:app._houseIngredients.filter(row=>'k:'+row.key!==data.identity)};
  }
  if(type==='cook4me/v14/inventory_state'){
   removalRequests.push({type,data:structuredClone(data)});
   return {houseIngredients:app._houseIngredients};
  }
  if(type==='cook4me/v39/stock_summary'){
   removalRequests.push({type,data:structuredClone(data)});
   return summary();
  }
  return api(type,data);
 };
 app.show('profile');
 app._v142PaintStockSummary();
}"""

with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=shutil.which('chromium') or None,args=['--no-sandbox'])
    for width in (390,1440):
        page=browser.new_page(viewport={'width':width,'height':844},is_mobile=width==390,has_touch=width==390)
        errors=[]
        page.on('pageerror',lambda err: errors.append(str(err)))
        page.set_default_timeout(15000)
        page.set_content(HTML)
        page.wait_for_function('window.ready')
        page.evaluate(SETUP)
        # The At home inventory is inside a collapsible stock details section.
        # Count locators can see hidden elements, but a real click requires
        # the parent section to be explicitly open, just as a user opens it.
        page.evaluate("""() => {
            const rows=app.shadowRoot.querySelector('#houseInventoryRows');
            for(let parent=rows?.parentElement;parent;parent=parent.parentElement)
                if(parent.tagName==='DETAILS')parent.open=true;
            const stock=app.shadowRoot.querySelector('[data-v78-section="stock"]');
            if(stock)stock.hidden=false;
        }""")

        # Stock groups are PRODUCT-name groups (v114), not ingredient IDs.
        # A rice ingredient can have two different named products and the
        # complete remove action must affect only the chosen product group.
        expect(page.locator('[data-v291-expiry-index]')).to_have_count(2)
        groups=page.locator('#houseInventoryRows > .v112-stock-group')
        existing=groups.evaluate_all(
            '(rows)=>rows.map(row=>({key:row.dataset.v112Group,title:row.querySelector("summary strong")?.textContent,remove:!!row.querySelector("summary [data-v291-remove-group]"),lotIds:[...row.querySelectorAll("[data-v112-edit-lot]")].map(el=>el.dataset.v112EditLot)}))'
        )
        assert len(existing)>=4,existing
        assert all(row['remove'] for row in existing),existing
        def group_key(title):
            matches=[row['key'] for row in existing if (row['title'] or '').startswith(title)]
            assert len(matches)==1,(title,existing)
            return matches[0]
        salt_key=group_key('Αλάτι')
        old_key=group_key('Ρύζι παλιό')
        new_key=group_key('Ρύζι νέο')
        carrot_key=group_key('Καρότο')
        assert old_key!=new_key
        print(f'RENDERED_STOCK_GROUPS={existing}',flush=True)
        assert page.locator('[data-v291-expiry-index="0"]').get_attribute('aria-label').startswith('Οριστική')
        assert page.locator('[data-v291-expiry-index="0"]').evaluate('(el)=>el.closest("button button")') is None
        assert page.evaluate("app._houseIngredients[0].lots.length") == 2

        # Cancel an expiry deletion. It must not call the backend or toggle the
        # parent edit card.
        page.locator('[data-v291-expiry-index="0"]').click()
        assert page.evaluate('removalRequests.length') == 0
        assert page.evaluate('app._houseIngredients[0].lots.length') == 2
        assert page.evaluate('confirmations[0].includes("παραμείνουν")')

        # Cancel a full group deletion and confirm the details accordion stays shut.
        page.locator(f'[data-v112-group="{salt_key}"] > summary > [data-v291-remove-group]').click()
        assert page.evaluate('removalRequests.length') == 0
        assert not page.locator(f'[data-v112-group="{salt_key}"]').get_attribute('open')

        # Delete only the expired Rice lot, preserving the newer Rice package.
        page.evaluate('confirmDecision=true')
        page.locator('[data-v291-expiry-index="0"]').click()
        page.wait_for_function("removalRequests.some(x=>x.type==='cook4me/v33/product_remove') && !app._v291Removing")
        assert page.evaluate("app._houseIngredients.find(x=>x.key==='rice').lots.map(x=>x.id)") == ['lot-new']
        assert page.evaluate("removalRequests.find(x=>x.type==='cook4me/v33/product_remove').data.expected_version") == 'v1'
        expect(page.locator('[data-v291-expiry-index]')).to_have_count(1)
        expect(page.locator(f'[data-v112-group="{new_key}"]')).to_have_count(1)

        # The other product under Rice is still visible. Remove that complete
        # At home PRODUCT entry, without redirecting to the ingredient's ID.
        expect(page.locator(f'[data-v112-group="{old_key}"]')).to_have_count(0)
        expect(page.locator(f'[data-v112-group="{new_key}"]')).to_have_count(1)
        page.locator(f'[data-v112-group="{new_key}"] > summary > [data-v291-remove-group]').click()
        page.wait_for_function("!app._v291Removing && removalRequests.filter(x=>x.type==='cook4me/v33/product_remove').length===2")
        assert page.evaluate("!app._houseIngredients.some(x=>x.key==='rice')")
        expect(page.locator(f'[data-v112-group="{new_key}"]')).to_have_count(0)
        assert page.evaluate("app._houseIngredients.some(x=>x.key==='carrot')")

        # Unlimited stock has no physical package. Remove its entire inventory
        # row rather than attempting to remove a fabricated lot.
        page.locator(f'[data-v112-group="{salt_key}"] > summary > [data-v291-remove-group]').click()
        page.wait_for_function("removalRequests.some(x=>x.type==='cook4me/v14/inventory_remove') && !app._v291Removing")
        assert page.evaluate("!app._houseIngredients.some(x=>x.key==='salt')")
        expect(page.locator(f'[data-v112-group="{salt_key}"]')).to_have_count(0)
        assert page.evaluate("removalRequests.find(x=>x.type==='cook4me/v14/inventory_remove').data.identity") == 'k:salt'
        expect(page.locator(f'[data-v112-group="{carrot_key}"]')).to_have_count(1)
        assert not errors,errors
        print(f'PASS {width}px: lot-only and entire-stock actions, Greek confirmations, cancellation, exact server requests, synchronized lists',flush=True)
        page.close()
    browser.close()
