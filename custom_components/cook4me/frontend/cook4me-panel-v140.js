const V139='cook4me-recipe-hub-panel-v139';
if(!customElements.get(V139))await import('./cook4me-panel-v139.js?v=2026.9.21.4');
const BasePanel=customElements.get(V139);
const DEVICE_SOURCE_V140=new URL('./assets/device-v133.jpg?v=2026.9.21.5',import.meta.url).href;

const MARKET_LANGUAGES=['ar','bg','cs','de','el','en','es','fr','hr','hu','it','ja','ko','pl','pt','ro','ru','sk','sl','tr','uk','zh'];
const MARKET_BY_COUNTRY={DE:'de',AT:'de',CH:'de',GR:'el',CY:'el',GB:'en',US:'en',AU:'en',IE:'en',CA:'en',FR:'fr',BE:'fr',ES:'es',IT:'it',PT:'pt',BR:'pt',PL:'pl',CZ:'cs',SK:'sk',HU:'hu',RO:'ro',BG:'bg',HR:'hr',SI:'sl',UA:'uk',RU:'ru',TR:'tr',JP:'ja',KR:'ko',CN:'zh',TW:'zh',AE:'ar',SA:'ar'};
const TEXT={
 en:{supermarketLanguage:'Supermarket language',supermarketHelp:'Ingredient names in missing-ingredient views, shopping lists and plan purchases use this language.',supermarketFallback:'If a translated ingredient name is unavailable, Cook4Me falls back to the UI language and then the original ingredient name.'},
 de:{supermarketLanguage:'Supermarktsprache',supermarketHelp:'Zutatennamen bei fehlenden Zutaten, Einkaufslisten und Planeinkäufen werden in dieser Sprache angezeigt.',supermarketFallback:'Fehlt eine Übersetzung, verwendet Cook4Me zuerst die UI-Sprache und danach den ursprünglichen Zutatennamen.'},
 el:{supermarketLanguage:'Γλώσσα σούπερ μάρκετ',supermarketHelp:'Τα ονόματα υλικών στα υλικά που λείπουν, στη λίστα αγορών και στις αγορές πλάνου χρησιμοποιούν αυτή τη γλώσσα.',supermarketFallback:'Αν δεν υπάρχει μετάφραση, το Cook4Me χρησιμοποιεί πρώτα τη γλώσσα του UI και μετά το αρχικό όνομα του υλικού.'}
};

class Cook4MeRecipeHubPanelV140 extends BasePanel{
 _v140Text(key){return (TEXT[this._langCode?.()||this._uiIngredientLanguage?.()||'en']||TEXT.en)[key]||TEXT.en[key]||key;}
 _v140CountryLanguage(country){
  const code=MARKET_BY_COUNTRY[String(country||'').trim().toUpperCase()];
  return MARKET_LANGUAGES.includes(code)?code:'en';
 }
 _v140SupermarketLanguage(){
  const settings=this._v79Settings||this._weekState?.costSettings||{};
  const value=String(settings.supermarketLanguage||'').trim().toLowerCase().replace('_','-').split('-',1)[0];
  if(MARKET_LANGUAGES.includes(value))return value;
  return this._v140CountryLanguage(settings.country||this._hass?.config?.country||'');
 }
 _v140LanguageName(code){
  try{return new Intl.DisplayNames([this._langCode?.()||this._uiIngredientLanguage?.()||'en'],{type:'language'}).of(code)||code.toUpperCase();}catch{return code.toUpperCase();}
 }
 _v140IngredientKey(row){
  if(!row||typeof row!=='object')return '';
  const raw=row.ingredientId||row.id||row.key||row.foodKey||'';
  if(raw)return String(raw);
  const identity=String(row.identity||'');
  return /^[ki]:/.test(identity)?identity.slice(2):identity;
 }
 _v140LocalizeIngredient(row){
  if(!row||typeof row!=='object')return row;
  const local=this._v140MarketNames?.get(this._v140IngredientKey(row));
  if(!local)return row;
  const original=String(row.originalName||row.name||row.foodName||'').trim();
  const shown=original&&original.localeCompare(local,undefined,{sensitivity:'base'})!==0?`${local} (${original})`:local;
  return {...row,originalName:original||row.originalName,name:shown,...('foodName'in row?{foodName:shown}:{})};
 }
 _v140LocalizeRows(rows){return Array.isArray(rows)?rows.map(row=>this._v140LocalizeIngredient(row)):rows;}

 async _v140LoadSupermarketCatalog(force=false){
  if(!this._entryId||!this._hass?.connection)return;
  const language=this._v140SupermarketLanguage(),key=`${this._prefKey()}:${language}`;
  if(!force&&this._v140MarketCatalogKey===key)return;
  if(this._v140MarketCatalogLoading?.key===key)return this._v140MarketCatalogLoading.promise;
  const request={key};
  request.promise=this._hass.connection.sendMessagePromise({type:'cook4me/v31/ingredient_catalog',entry_id:this._entryId,language})
   .then(result=>{
    if(key!==`${this._prefKey()}:${this._v140SupermarketLanguage()}`)return;
    const map=new Map();
    for(const row of result?.items||[]){
     if(!row||typeof row!=='object'||!row.name)continue;
     for(const field of ['ingredientId','id','key','foodKey'])if(row[field])map.set(String(row[field]),String(row.name));
     for(const id of row.sourceIngredientIds||[])if(id)map.set(String(id),String(row.name));
    }
    this._v140MarketNames=map;this._v140MarketCatalogKey=key;
    if(this.shadowRoot?.getElementById('content')){this._renderTab();if(this._opened)this._renderRecipeDialog();}
   })
   .catch(()=>{})
   .finally(()=>{if(this._v140MarketCatalogLoading===request)this._v140MarketCatalogLoading=null;});
  this._v140MarketCatalogLoading=request;
  return request.promise;
 }
 async _v79LoadSettings(){
  await super._v79LoadSettings();
  if(this._v79Settings)await this._v140LoadSupermarketCatalog();
 }
 _missingIngredientObjects(recipe){
  return this._v140LocalizeRows(super._missingIngredientObjects(recipe)||[]);
 }
 async _api(type,data={}){
  if(type.endsWith('/shopping_add')||type.endsWith('/week_add_shopping'))data={...data,ui_language:this._v140SupermarketLanguage()};
  const result=await super._api(type,data);
  if(result?.shoppingDelta)result.shoppingDelta=this._v140LocalizeRows(result.shoppingDelta);
  return result;
 }

 _v79RenderSettings(c){
  const t=k=>this._escape(this._v79Text(k)),s=this._v79Settings||{},lang=this._v140SupermarketLanguage();
  c.innerHTML=`<h2>${t('prices')}</h2><p class="muted">${t('help')}</p><div class="v78-fields v140-market-fields"><label class="field">${t('market')}<input data-v79-country maxlength="2" pattern="[A-Za-z]{2}" placeholder="DE" value="${this._escape(s.country||'')}" autocapitalize="characters" list="v79Countries"></label><datalist id="v79Countries">${['DE','GR','FR','GB','US','ES','IT','NL','BE','AT','CH','PL','PT','AU','CA'].map(code=>{let name=code;try{name=new Intl.DisplayNames([this._langCode()],{type:'region'}).of(code);}catch{}return `<option value="${code}">${this._escape(name)}</option>`;}).join('')}</datalist><label class="field">${t('currency')}<input data-v79-currency maxlength="3" pattern="[A-Za-z]{3}" placeholder="EUR" value="${this._escape(s.currency||'')}" autocapitalize="characters"></label><label class="field">${this._escape(this._v140Text('supermarketLanguage'))}<select data-v140-supermarket-language>${MARKET_LANGUAGES.map(code=>`<option value="${code}" ${code===lang?'selected':''}>${this._escape(this._v140LanguageName(code))} (${code.toUpperCase()})</option>`).join('')}</select></label></div><p class="muted">${t('marketHelp')} ${this._escape(this._v140Text('supermarketHelp'))}</p><p class="muted">${this._escape(this._v140Text('supermarketFallback'))}</p><label class="v79-check"><input type="checkbox" data-v79-auto ${s.autoGlobalPrices!==false?'checked':''}> ${t('auto')}</label><button class="btn secondary" data-v79-save-settings>${this._escape(this._t('save'))}</button><p role="status">${this._escape(this._v79SettingsError||'')}</p>`;
  const country=c.querySelector('[data-v79-country]'),currency=c.querySelector('[data-v79-currency]'),language=c.querySelector('[data-v140-supermarket-language]');
  let countryChanged=false,currencyEdited=false,languageEdited=false;
  country.oninput=()=>{countryChanged=true;currencyEdited=false;currency.value='';if(!languageEdited)language.value=this._v140CountryLanguage(country.value);};
  currency.oninput=()=>currencyEdited=true;
  language.onchange=()=>languageEdited=true;
  c.querySelector('[data-v79-save-settings]').onclick=async event=>{
   const context=this._prefKey();event.target.disabled=true;
   try{
    const payload={entry_id:this._entryId,country:country.value.trim().toUpperCase(),supermarket_language:language.value,auto_global_prices:c.querySelector('[data-v79-auto]').checked};
    if(!countryChanged||currencyEdited)payload.currency=currency.value.trim().toUpperCase();
    const result=await this._api('cook4me/v34/price_settings',payload);
    if(context!==this._prefKey())return;
    this._v79Settings=result.settings;this._v79Revision=(this._v79Revision||0)+1;
    this._v140MarketCatalogKey='';await this._v140LoadSupermarketCatalog(true);
    this._v79RenderSettings(c);c.querySelector('[role=status]').textContent=this._v79Text('saved');
   }catch(e){c.querySelector('[role=status]').textContent=String(e.message||e);}
   finally{event.target.disabled=false;}
  };
 }

 _v140BuildDeviceCutout(){
  if(this._v140DeviceCutout)return Promise.resolve(this._v140DeviceCutout);
  if(this._v140DeviceCutoutPromise)return this._v140DeviceCutoutPromise;
  this._v140DeviceCutoutPromise=new Promise((resolve,reject)=>{
   const source=new Image();
   source.onload=()=>{
    try{
     const canvas=document.createElement('canvas');canvas.width=source.naturalWidth||474;canvas.height=source.naturalHeight||474;
     const ctx=canvas.getContext('2d',{willReadFrequently:true});ctx.drawImage(source,0,0,canvas.width,canvas.height);
     const image=ctx.getImageData(0,0,canvas.width,canvas.height),data=image.data,w=canvas.width,h=canvas.height;
     // Remove only the edge-connected studio background; never threshold the cooker body itself.
     const background=index=>{
      const p=index*4,r=data[p],g=data[p+1],b=data[p+2],max=Math.max(r,g,b),min=Math.min(r,g,b);
      const luminance=.2126*r+.7152*g+.0722*b;
      return luminance>=182&&max-min<=34;
     };
     const seen=new Uint8Array(w*h),queue=new Int32Array(w*h);let head=0,tail=0;
     const push=index=>{if(index<0||index>=w*h||seen[index]||!background(index))return;seen[index]=1;queue[tail++]=index;};
     for(let x=0;x<w;x++){push(x);push((h-1)*w+x);}
     for(let y=1;y<h-1;y++){push(y*w);push(y*w+w-1);}
     while(head<tail){
      const index=queue[head++],x=index%w,y=(index/w)|0;
      if(x)push(index-1);if(x+1<w)push(index+1);if(y)push(index-w);if(y+1<h)push(index+w);
     }
     for(let index=0;index<seen.length;index++)if(seen[index])data[index*4+3]=0;
     ctx.putImageData(image,0,0);
     ctx.fillStyle='#060808';
     const sx=canvas.width/474,sy=canvas.height/474;
     ctx.beginPath();ctx.roundRect(174*sx,248*sy,127*sx,80*sy,12*Math.min(sx,sy));ctx.fill();
     ctx.beginPath();ctx.roundRect(218*sx,231*sy,40*sx,15*sy,3*Math.min(sx,sy));ctx.fill();
     ctx.beginPath();ctx.roundRect(219*sx,357*sy,38*sx,13*sy,3*Math.min(sx,sy));ctx.fill();
     this._v140DeviceCutout=canvas.toDataURL('image/png');resolve(this._v140DeviceCutout);
    }catch(error){reject(error);}
   };
   source.onerror=reject;source.src=DEVICE_SOURCE_V140;
  }).finally(()=>{this._v140DeviceCutoutPromise=null;});
  return this._v140DeviceCutoutPromise;
 }
 _v132FixDeviceAsset(){
  const root=this.shadowRoot,model=root?.querySelector('.v130-model'),image=root?.querySelector('.v130-model-photo');
  if(!model||!image)return;
  model.querySelector('.v139-model-svg')?.remove();
  image.style.setProperty('display','block','important');
  if(this._v140DeviceCutout){if(image.src!==this._v140DeviceCutout)image.src=this._v140DeviceCutout;return;}
  image.style.opacity='0';
  this._v140BuildDeviceCutout().then(url=>{
   if(!image.isConnected)return;
   image.src=url;image.style.opacity='1';
   model.classList.remove('v132-model-image-error','v133-model-image-error','v134-model-image-error','v135-model-image-error','v138-model-image-error');
  }).catch(()=>{image.src=DEVICE_SOURCE_V140;image.style.opacity='1';});
 }

 _updateHeader(){super._updateHeader();this._v132FixDeviceAsset();this._v140Styles();}
 _renderShell(){super._renderShell();this._v132FixDeviceAsset();this._v140Styles();}
 _renderTab(){
  const result=super._renderTab();this._v132FixDeviceAsset();this._v140Styles();
  if(this._entryId){if(!this._v79Settings&&!this._v79SettingsLoading)queueMicrotask(()=>void this._v79LoadSettings());else queueMicrotask(()=>void this._v140LoadSupermarketCatalog());}
  this.setAttribute('data-cook4me-build','2026.9.21.5');return result;
 }
 _v140Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v140Styles'))return;
  const style=document.createElement('style');style.id='v140Styles';style.textContent=`
   .v139-model-svg{display:none!important}
   .v130-model{background:transparent!important;box-shadow:none!important;filter:none!important;overflow:visible!important}
   .v130-model-photo{display:block!important;clip-path:none!important;mix-blend-mode:normal!important;background:transparent!important;border-radius:0!important;object-fit:contain!important;filter:drop-shadow(0 0 4px rgba(220,230,255,.30)) drop-shadow(0 0 10px rgba(170,195,255,.12)) drop-shadow(0 8px 12px rgba(0,0,0,.34))!important}
   .v130-brand-mask{display:none!important}
   .v130-live-screen{z-index:3!important;left:36.7%!important;top:52.3%!important;width:26.8%!important;height:16.9%!important;border-radius:11%!important;padding:2.2% 3% 2.8%!important}
   .v140-market-fields{grid-template-columns:repeat(3,minmax(0,1fr))!important}
   .v140-market-fields select{width:100%;box-sizing:border-box}
   @media(max-width:760px){.v140-market-fields{grid-template-columns:1fr!important}}
  `;this.shadowRoot.append(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v140',Cook4MeRecipeHubPanelV140);
