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
            # Recognition saves the receipt but the saved-receipt list always opens folded.
            page.evaluate("async()=>{await app._v78Open('manual');await app._r195Start(true,false);await app._v78Recognize('fixture-photo');}")
            queue=page.locator('[data-r232-queue]');expect(queue).to_be_visible()
            receipt_row=queue.locator('[data-r232-receipt="receipt1"]')
            expect(receipt_row).to_be_attached()
            assert page.evaluate("!app._r232Dialog.querySelector('[data-r232-receipt=\"receipt1\"]').open")
            expect(queue.locator('[data-r232-item]')).to_have_count(0)
            expect(receipt_row.locator('[data-r232-receipt-remove]')).to_be_visible()
            receipt_row.locator('summary').click()
            expect(queue.locator('[data-r232-item]')).to_have_count(2)
            expect(queue.locator('[data-r232-select-item]')).to_have_count(2)
            expect(queue.locator('[data-r232-action="apply"]')).to_have_count(0)
            expect(queue.locator('[data-r232-action="discard"]')).to_have_count(2)
            expect(queue.locator('[data-r232-bulk="apply"]')).to_be_disabled()
            expect(queue.locator('[data-r232-bulk="discard"]')).to_be_disabled()
            expect(queue.locator('summary')).to_contain_text('Αναζήτηση barcode')
            assert page.evaluate('!app._v78Dialog')
            page.evaluate("async()=>{draft.processing={state:'ready',stage:'ready',done:2,total:2};await app._r232Poll();}")
            expect(queue.locator('summary')).to_contain_text('Έτοιμη για έλεγχο')
            page.screenshot(path=f'/tmp/cook4me-receipts-{width}.png')

            # Edit is edit-only. Barcode can be camera-scanned from beside the barcode field,
            # and the scan returns to this same receipt item without adding stock.
            page.locator('[data-r232-item="a"] [data-r232-action="edit"]').click()
            expect(queue).not_to_be_visible()
            expect(page.locator('main [data-draft="productName"]')).to_have_value('Ρύζι')
            assert page.evaluate("app._v78Draft.paidAmount===4&&app._v78Draft.barcode==='4000000000001'&&app._v78Draft.packageCount===2")
            expect(page.locator('[data-v196-scan]')).to_be_enabled()
            assert page.evaluate("""()=>{const input=app.shadowRoot.querySelector('[data-v112-barcode-edit]');const scan=app.shadowRoot.querySelector('[data-v196-scan]');return input&&scan&&input.parentElement===scan.parentElement}""")
            expect(page.locator('[data-r195-apply]')).to_be_hidden()
            expect(page.locator('[data-r195-save]')).to_be_visible()
            expect(page.locator('[data-r195-discard]')).to_be_visible()
            page.evaluate("""()=>{
                app._v248OriginalScan=app._v80Scan.bind(app);
                app._v80Scan=async mode=>{app._v248ScanMode=mode;if(mode==='barcode')await app._v78Lookup('4000000000002');};
            }""")
            page.locator('[data-v196-scan]').click()
            page.wait_for_function("app._v248ScanMode==='barcode' && app._v78Draft.editorOpen")
            assert page.evaluate("app._v78Draft.receiptItemId==='a'&&app._v78Draft.paidAmount===4&&app._v78Draft.purchaseDate==='2026-09-25'&&app._v78Draft.packageCount===2")
            page.locator('main [data-draft="productName"]').fill('Ρύζι διορθωμένο')
            page.locator('[data-r195-save]').click()
            expect(queue).to_be_visible()
            assert page.evaluate("!app._r232Dialog.querySelector('[data-r232-receipt=\"receipt1\"]').open")
            expect(queue.locator('[data-r232-item]')).to_have_count(0)
            receipt_row.locator('summary').click()
            expect(page.locator('[data-r232-item="a"]')).to_contain_text('Ρύζι διορθωμένο')
            assert page.evaluate('adds')==0

            # Both products can be selected and added with one bulk action.
            page.locator('[data-r232-select-item="a"]').check()
            page.locator('[data-r232-select-item="b"]').check()
            expect(page.locator('[data-r232-bulk="apply"]')).to_contain_text('(2)')
            expect(page.locator('[data-r232-bulk="discard"]')).to_contain_text('(2)')
            page.locator('[data-r232-bulk="apply"]').click()
            expect(page.locator('[data-r232-item]')).to_have_count(0)
            assert page.evaluate('adds')==2

            # Multi-remove uses the existing discard route and never writes stock.
            page.evaluate("""async()=>{
                const seed={...structuredClone(draft.items[1]),status:'pending',itemRevision:0,enrichment:{state:'ready'}};
                draft.items.push({...seed,id:'c',productName:'Γιαούρτι'},{...seed,id:'d',productName:'Γάλα'});
                draft.revision++;await app._r232Poll();
            }""")
            expect(page.locator('[data-r232-item]')).to_have_count(2)
            page.locator('[data-r232-select-item="c"]').check()
            page.locator('[data-r232-select-item="d"]').check()
            expect(page.locator('[data-r232-bulk="discard"]')).to_contain_text('(2)')
            page.locator('[data-r232-bulk="discard"]').click()
            expect(page.locator('[data-r232-item]')).to_have_count(0)
            assert page.evaluate("adds===2&&draft.items.find(i=>i.id==='c').status==='discarded'&&draft.items.find(i=>i.id==='d').status==='discarded'")

            # A lost bulk Add response keeps the applying product selected so Add selected retries it.
            page.evaluate("""async()=>{
                const seed={...structuredClone(draft.items[1]),id:'e',status:'pending',itemRevision:0,productName:'Τόφου',enrichment:{state:'ready'}};
                draft.items.push(seed);draft.revision++;await app._r232Poll();window.failApply=true;
            }""")
            page.locator('[data-r232-select-item="e"]').check()
            page.locator('[data-r232-bulk="apply"]').click()
            expect(page.locator('[data-r232-message]')).to_contain_text('Lost response')
            expect(page.locator('[data-r232-select-item="e"]')).to_be_checked()
            expect(page.locator('[data-r232-bulk="apply"]')).to_contain_text('(1)')
            page.locator('[data-r232-bulk="apply"]').click()
            expect(page.locator('[data-r232-item="e"]')).to_have_count(0)
            assert page.evaluate('adds')==3

            # Saved review remains reachable without receipt AI, and reopening starts folded again.
            page.locator('[data-r232-close]').click()
            page.evaluate('''()=>{app._v78State.aiChoices=[];app._r199Launch();}''')
            expect(page.locator('[data-r199-receipt-photo]')).to_have_count(0);expect(button).to_be_attached()
            button.click();expect(queue).to_be_visible()
            assert page.evaluate("!app._r232Dialog.querySelector('[data-r232-receipt=\"receipt1\"]').open")

            # Receipt delete is available on the folded row and removes the saved receipt itself.
            page.evaluate("window.confirm=()=>true")
            receipt_row.locator('[data-r232-receipt-remove]').click()
            expect(queue.locator('[data-r232-receipt="receipt1"]')).to_have_count(0)
            expect(button).to_have_count(0)
            assert page.evaluate('''()=>{const d=app._r232Dialog;return d.scrollWidth<=d.clientWidth+1&&d.getBoundingClientRect().right<=innerWidth}''')
            assert not errors,errors
            print(f'PASS {width}: folded receipts, barcode edit, bulk add/remove, interrupted bulk retry, receipt delete')
            page.close()
        browser.close()

if __name__=='__main__':run()
