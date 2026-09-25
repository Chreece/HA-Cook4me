"""Real frontend queue, receipt editing, scanning context and package cards."""
from pathlib import Path
import shutil
from playwright.sync_api import expect, sync_playwright
from ui_offline_loader_v203 import local_html

ROOT=Path(__file__).resolve().parents[1]

def run():
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=shutil.which('chromium') or None,args=['--no-sandbox'])
        for width,height in ((390,844),(1440,980)):
            page=browser.new_page(viewport={'width':width,'height':height});errors=[]
            page.on('pageerror',lambda e:errors.append(str(e)));page.set_default_timeout(8000)
            page.set_content(local_html(ROOT));page.wait_for_function('window.ready')
            page.evaluate('''async()=>{
                window.draft={id:'receipt1',revision:1,merchant:'Fixture market',purchaseDate:'2026-09-25',currency:'EUR',total:6,taxStatus:'allocated',processing:{state:'processing',stage:'barcode',done:0,total:2},items:[
                    {id:'a',status:'pending',kind:'product',productName:'Ρύζι',quantity:500,unit:'g',packageCount:2,lineTotal:4,barcode:'4000000000001',ingredientLinks:[{key:'rice',name:'Ρύζι'}],nutrition:{basisQuantity:100,basisUnit:'g',values:{protein:7}}},
                    {id:'b',status:'pending',kind:'product',productName:'Καρότο',quantity:1,unit:'kg',packageCount:1,lineTotal:2,ingredientLinks:[{key:'carrot',name:'Καρότο'}]}
                ]};window.adds=0;window.serverCalls=[];
                const original=app._api.bind(app);
                app._api=async(type,data={})=>{
                    serverCalls.push({type,...structuredClone(data)});
                    if(type.endsWith('/recognize')&&type.includes('/receipts/'))return {receipt:structuredClone(draft),saved:true};
                    if(!type.endsWith('/drafts'))return original(type,data);
                    if(data.action==='list')return {drafts:draft?[{...draft,pendingCount:draft.items.filter(i=>['pending','applying'].includes(i.status)).length,itemCount:draft.items.length}]:[]};
                    if(data.action==='get')return {receipt:structuredClone(draft)};
                    const item=draft.items.find(i=>i.id===data.item_id);
                    if(data.action==='save_item'){Object.assign(item,data.item,{itemRevision:(item.itemRevision||0)+1,enrichment:{state:'reviewed'}});Object.assign(draft,data.receipt||{});draft.revision++;}
                    if(data.action==='apply'){if(window.failApply){window.failApply=false;item.status='applying';draft.revision++;throw Error('Lost response');}if(item.status!=='applied'){adds++;item.status='applied';}draft.revision++;return {receipt:structuredClone(draft),result:{houseIngredients:app._houseIngredients}};}
                    if(data.action==='discard'){if(item)item.status='discarded';else draft=null;}
                    return {receipt:structuredClone(draft)};
                };
                app.show('profile');await app._r232Poll();
            }''')
            button=page.locator('[data-r232-open]');expect(button).to_have_text('Αποθηκευμένες αποδείξεις (1)')
            assert page.evaluate('''()=>{const b=app.shadowRoot.querySelector('[data-r232-open]');return b.previousElementSibling.matches('[data-r199-receipt-photo]')}''')
            # Each weight action belongs to its package bubble, with valid sibling buttons.
            expect(page.locator('.r232-package [data-v116-lot]')).to_have_count(2)
            assert page.evaluate('''()=>[...app.shadowRoot.querySelectorAll('.r232-package')].every(c=>c.querySelector('[data-v112-edit-lot]')&&c.querySelector('[data-v116-lot]')&&!c.querySelector('button button'))''')
            page.evaluate('''()=>{app.weighed='';app._v116ReweighLot=async id=>app.weighed=id;}''')
            page.evaluate('''()=>{let n=app.shadowRoot.querySelector('[data-v116-lot="lot-rice"]');for(;n;n=n.parentElement)if(n.tagName==='DETAILS')n.open=true;}''')
            page.locator('[data-v116-lot="lot-rice"]').click()
            assert page.evaluate('app.weighed')=='lot-rice'
            # Real recognition completion saves the result into the queue and closes capture.
            page.evaluate("async()=>{await app._v78Open('manual');await app._r195Start(true,false);await app._v78Recognize('fixture-photo');}")
            queue=page.locator('[data-r232-queue]');expect(queue).to_be_visible()
            expect(queue.locator('[data-r232-item]')).to_have_count(2)
            expect(queue.locator('summary')).to_contain_text('Αναζήτηση barcode')
            assert page.evaluate('!app._v78Dialog')
            page.evaluate("async()=>{draft.processing={state:'ready',stage:'ready',done:2,total:2};await app._r232Poll();}")
            expect(queue.locator('summary')).to_contain_text('Έτοιμη για έλεγχο')
            page.screenshot(path=f'/tmp/cook4me-receipts-{width}.png')
            page.locator('[data-r232-item="a"] [data-r232-action="edit"]').click()
            expect(queue).not_to_be_visible()
            expect(page.locator('main [data-draft="productName"]')).to_have_value('Ρύζι')
            assert page.evaluate("app._v78Draft.paidAmount===4&&app._v78Draft.barcode==='4000000000001'&&app._v78Draft.packageCount===2")
            expect(page.locator('[data-v80-scan="barcode"]')).to_be_enabled()
            # A different physical barcode uses the real scanner lookup/new-draft path.
            page.evaluate("async()=>{await app._v78Lookup('4000000000002');}")
            assert page.evaluate("app._v78Draft.receiptItemId==='a'&&app._v78Draft.paidAmount===4&&app._v78Draft.purchaseDate==='2026-09-25'&&app._v78Draft.packageCount===2")
            page.locator('main [data-draft="productName"]').fill('Ρύζι διορθωμένο')
            page.locator('[data-r195-save]').click()
            expect(queue).to_be_visible();expect(page.locator('[data-r232-item="a"]')).to_contain_text('Ρύζι διορθωμένο')
            assert page.evaluate('adds')==0
            page.locator('[data-r232-item="a"] [data-r232-action="apply"]').click()
            expect(page.locator('[data-r232-item="a"]')).to_have_count(0)
            assert page.evaluate('adds')==1
            # A lost Add response must retain the original applying state and retry.
            page.evaluate('''async()=>{draft.taxStatus='needs_review';draft.items.push({...structuredClone(draft.items[1]),id:'c',productName:'Γιαούρτι'});await app._r232Poll();}''')
            page.locator('[data-r232-item="c"] [data-r232-action="edit"]').click()
            page.locator('[data-r232-tax]').check();page.evaluate('window.failApply=true')
            page.locator('[data-r195-apply]').click()
            expect(page.locator('[data-r195-message]')).to_contain_text('Lost response')
            assert page.evaluate("app._r195Current().status==='applying'")
            page.locator('[data-r195-apply]').click()
            expect(queue).to_be_visible();expect(page.locator('[data-r232-item="c"]')).to_have_count(0)
            assert page.evaluate('adds')==2
            page.locator('[data-r232-item="b"] [data-r232-action="discard"]').click()
            expect(page.locator('[data-r232-item]')).to_have_count(0)
            page.locator('[data-r232-close]').click();button.click()
            expect(page.locator('[data-r232-item]')).to_have_count(0)
            expect(button).to_have_text('Αποθηκευμένες αποδείξεις (0)')
            # Saved review is available even if receipt AI is currently unavailable.
            page.evaluate('''()=>{app._v78State.aiChoices=[];app._r199Launch();}''')
            expect(page.locator('[data-r199-receipt-photo]')).to_have_count(0);expect(button).to_be_attached()
            assert page.evaluate('''()=>{const d=app._r232Dialog;return d.scrollWidth<=d.clientWidth+1&&d.getBoundingClientRect().right<=innerWidth}''')
            assert not errors,errors
            print(f'PASS {width}: package weight, saved queue, progress, barcode edit, VAT confirmation, interrupted Add retry, permanent discard')
            page.close()
        browser.close()

if __name__=='__main__':run()
