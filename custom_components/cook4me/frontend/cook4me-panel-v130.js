const V129='cook4me-recipe-hub-panel-v129';
if(!customElements.get(V129))await import('./cook4me-panel-v129.js?v=2026.9.20.3');
const BasePanel=customElements.get(V129);
const DEVICE_IMAGE='data:image/jpeg;base64,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';

const V130_WORDS={
 en:{device:'Smart cooker',idle:'Ready',loading:'Loading recipe',preheating:'Preheating',cooking:'Cooking',warm:'Keeping warm',done:'Finished',offline:'Offline',waiting:'Waiting for appliance',step:'Step'},
 de:{device:'Multikocher',idle:'Bereit',loading:'Rezept wird geladen',preheating:'Vorheizen',cooking:'Kochen',warm:'Warmhalten',done:'Fertig',offline:'Offline',waiting:'Warten auf das Gerät',step:'Schritt'},
 el:{device:'Έξυπνη χύτρα',idle:'Έτοιμη',loading:'Φόρτωση συνταγής',preheating:'Προθέρμανση',cooking:'Μαγείρεμα',warm:'Διατήρηση θερμοκρασίας',done:'Ολοκληρώθηκε',offline:'Offline',waiting:'Αναμονή για τη συσκευή',step:'Βήμα'}
};
const V130_QUEUE_TEXT={
 en:{pendingRecipe:'Sending to appliance',pendingSending:'Sending to the appliance…',pendingWaiting:'Sent — waiting for the appliance to receive it',pendingOffline:'Appliance is offline — it will be sent automatically',pendingBusy:'Appliance is busy — it will be sent automatically',pendingRetry:'Waiting to retry delivery'},
 de:{pendingRecipe:'Wird an das Gerät gesendet',pendingSending:'Wird an das Gerät gesendet…',pendingWaiting:'Gesendet — warte auf Empfang durch das Gerät',pendingOffline:'Gerät ist offline — wird automatisch gesendet',pendingBusy:'Gerät ist beschäftigt — wird automatisch gesendet',pendingRetry:'Warte auf erneuten Sendeversuch'},
 el:{pendingRecipe:'Αποστολή στη συσκευή',pendingSending:'Αποστολή στη συσκευή…',pendingWaiting:'Στάλθηκε — αναμονή να το παραλάβει η συσκευή',pendingOffline:'Η συσκευή είναι offline — θα σταλεί αυτόματα',pendingBusy:'Η συσκευή είναι απασχολημένη — θα σταλεί αυτόματα',pendingRetry:'Αναμονή για νέα προσπάθεια αποστολής'}
};

class Cook4MeRecipeHubPanelV130 extends BasePanel{
 _v130Text(key){
  const lang=this._uiIngredientLanguage?.()||this._langCode?.()||'en';
  return (V130_WORDS[lang]||V130_WORDS.en)[key]||V130_WORDS.en[key]||key;
 }
 _v129Text(key){
  const lang=this._uiIngredientLanguage?.()||this._langCode?.()||'en';
  return (V130_QUEUE_TEXT[lang]||V130_QUEUE_TEXT.en)[key]||super._v129Text(key);
 }
 _v130Phase(entry){
  if(!entry?.connected)return'offline';
  const state=entry.state||{},queue=this._bookState?.queuedSend;
  const raw=String(state.phase||state.status||'').toLowerCase().replace(/[\s-]+/g,'_');
  if(/done|finish|complete/.test(raw))return'done';
  if(/keep|warm|maintain|temperature_hold/.test(raw))return'warm';
  if(/preheat|heating|heat_up/.test(raw))return'preheating';
  if(/cook|pressure|active|running/.test(raw))return'cooking';
  if(queue)return'loading';
  return'idle';
 }
 _v130PhaseLabel(phase){return this._v130Text(phase==='warm'?'warm':phase);}
 _v130RecipeImage(entry){
  const state=entry?.state||{},queue=this._bookState?.queuedSend,loaded=entry?.loadedRecipe||{};
  return String(
   state.recipeImage||state.cover||state.recipeCover||
   loaded.cover||loaded.image||
   queue?.recipe?.cover||queue?.recipe?.image||''
  ).trim();
 }
 _v130RecipeTitle(entry){
  const state=entry?.state||{},queue=this._bookState?.queuedSend;
  return this._clean(state.recipeTitle||entry?.loadedRecipe?.title||queue?.title||'');
 }
 _v130Step(entry){
  const state=entry?.state||{};
  const raw=Number(state.stepIndex),count=Number(state.stepCount||state.recipeStepCount);
  if(!Number.isFinite(raw))return'';
  const current=raw>=0?raw+1:raw;
  return Number.isFinite(count)&&count>0?`${this._v130Text('step')} ${current}/${count}`:`${this._v130Text('step')} ${current}`;
 }
 _v130DeviceHtml(entry){
  const phase=this._v130Phase(entry),state=entry?.state||{},title=this._v130RecipeTitle(entry),photo=this._v130RecipeImage(entry),step=this._v130Step(entry);
  const instruction=this._clean(state.currentInstruction||'');
  const temperature=state.temperature??state.currentTemperature??state.targetTemperature;
  const temp=temperature!==undefined&&temperature!==null&&temperature!==''?`${this._escape(temperature)}°`:'';
  const detail=[step,temp,instruction].filter(Boolean).join(' · ');
  const recipeLoaded=Boolean(title||entry?.loadedRecipe||state.variantFunctionalId||state.recipeFunctionalId);
  return `<div class="v130-device-summary">
   <div class="v130-model v130-${phase}" aria-label="${this._escape(this._v130Text('device'))}: ${this._escape(this._v130PhaseLabel(phase))}">
    <img class="v130-model-photo" src="${DEVICE_IMAGE}" alt="">
    <div class="v130-brand-mask"></div>
    <div class="v130-live-screen ${photo?'has-photo':''}">
     ${photo?`<img class="v130-recipe-photo" src="${this._escape(photo)}" alt="" loading="eager">`:`<div class="v130-screen-symbol" aria-hidden="true">${phase==='done'?'✓':phase==='preheating'?'♨':phase==='cooking'?'≋':phase==='warm'?'♨':phase==='loading'?'↻':'•'}</div>`}
     <div class="v130-screen-copy">
      <strong>${this._escape(title||this._v130PhaseLabel(phase))}</strong>
      <span>${this._escape(recipeLoaded?this._v130PhaseLabel(phase):this._v130Text('idle'))}</span>
     </div>
     <div class="v130-screen-progress"><i></i></div>
    </div>
    <div class="v130-steam" aria-hidden="true"><i></i><i></i><i></i></div>
   </div>
   <div class="v130-device-copy">
    <div class="v130-device-title">${this._escape(this._v130Text('device'))}</div>
    <div class="v130-device-state"><span class="v130-dot"></span>${this._escape(this._v130PhaseLabel(phase))}</div>
    ${title?`<div class="v130-device-recipe">${this._escape(title)}</div>`:''}
    ${detail?`<div class="muted v130-device-detail">${this._escape(detail)}</div>`:''}
   </div>
  </div>`;
 }
 _updateHeader(){
  super._updateHeader();
  const root=this.shadowRoot?.getElementById('status'),entry=this._entry();
  if(!root||!entry)return;
  const old=root.querySelector('.status,.v130-device-summary');
  if(old)old.outerHTML=this._v130DeviceHtml(entry);
  else root.insertAdjacentHTML('afterbegin',this._v130DeviceHtml(entry));
  root.querySelectorAll('.v130-recipe-photo').forEach(img=>img.addEventListener('error',()=>{img.remove();}));
  this._v130Styles();
 }
 _renderShell(){
  super._renderShell();
  this._v130Styles();
 }
 _renderTab(){
  const result=super._renderTab();
  this._v130Styles();
  this.setAttribute('data-cook4me-build','2026.9.20.4');
  return result;
 }
 _v130Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v130Styles'))return;
  const style=document.createElement('style');style.id='v130Styles';style.textContent=`
   #status{overflow:visible}
   .v130-device-summary{display:flex;align-items:center;gap:20px;min-width:0;min-height:138px}
   .v130-model{position:relative;flex:0 0 154px;width:154px;aspect-ratio:1;filter:drop-shadow(0 12px 16px rgba(0,0,0,.28));transform-origin:50% 90%}
   .v130-model-photo{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;border-radius:24px}
   .v130-brand-mask{position:absolute;left:31.2%;top:47.5%;width:38.2%;height:40.5%;border-radius:18% 18% 22% 22%;background:linear-gradient(180deg,#080a0b 0%,#050607 72%,#090a0b 100%);box-shadow:inset 0 0 0 1px rgba(255,255,255,.16),inset 0 0 18px rgba(255,255,255,.035)}
   .v130-live-screen{position:absolute;left:34.2%;top:51%;width:32.2%;height:31%;border-radius:12%;overflow:hidden;background:radial-gradient(circle at 50% 20%,#21322c,#080c0b 58%,#030404);box-shadow:0 0 12px rgba(57,190,137,.15),inset 0 0 0 1px rgba(255,255,255,.07);display:flex;flex-direction:column;align-items:center;justify-content:center;padding:5% 5% 6%;color:#eef5f1;text-align:center}
   .v130-live-screen.has-photo{justify-content:flex-end}
   .v130-recipe-photo{position:absolute;inset:0;width:100%;height:58%;object-fit:cover;filter:saturate(.94) contrast(1.04)}
   .v130-recipe-photo:after{content:'';position:absolute;inset:0;background:linear-gradient(transparent,#000)}
   .v130-screen-copy{position:relative;z-index:2;width:100%;display:grid;gap:1px;text-shadow:0 1px 3px #000}
   .v130-screen-copy strong{font-size:7px;line-height:1.08;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
   .v130-screen-copy span{font-size:5.5px;opacity:.78;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
   .v130-screen-symbol{font-size:19px;line-height:1;color:#78e3b6;text-shadow:0 0 12px currentColor;margin-bottom:3px}
   .v130-screen-progress{position:relative;z-index:2;width:72%;height:2px;margin-top:4px;border-radius:99px;background:rgba(255,255,255,.16);overflow:hidden}
   .v130-screen-progress i{display:block;height:100%;width:42%;border-radius:inherit;background:#70ddb0;box-shadow:0 0 8px #70ddb0}
   .v130-steam{position:absolute;left:38%;top:5%;width:24%;height:28%;pointer-events:none;opacity:0}
   .v130-steam i{position:absolute;bottom:4%;width:5px;height:22px;border-radius:50%;border-left:2px solid rgba(223,241,235,.56);filter:blur(.3px);opacity:0}
   .v130-steam i:nth-child(1){left:18%;animation-delay:-.5s}.v130-steam i:nth-child(2){left:48%;height:28px;animation-delay:-1.1s}.v130-steam i:nth-child(3){left:72%;height:19px;animation-delay:-1.65s}
   .v130-device-copy{min-width:0;display:grid;gap:5px}
   .v130-device-title{font-size:21px;font-weight:700;line-height:1.1}
   .v130-device-state{display:flex;align-items:center;gap:8px;font-weight:600;font-size:15px}
   .v130-dot{width:9px;height:9px;border-radius:50%;background:var(--success-color,#43a047);box-shadow:0 0 0 4px color-mix(in srgb,var(--success-color,#43a047) 15%,transparent)}
   .v130-device-recipe{font-size:15px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:720px}
   .v130-device-detail{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:800px}
   .v130-offline{filter:grayscale(.75) drop-shadow(0 10px 14px rgba(0,0,0,.2));opacity:.72}
   .v130-offline+.v130-device-copy .v130-dot{background:var(--error-color,#db4437)}
   .v130-loading .v130-screen-symbol{animation:v130Spin 1.1s linear infinite}
   .v130-loading .v130-screen-progress i{animation:v130Load 1.2s ease-in-out infinite}
   .v130-preheating,.v130-cooking{animation:v130Pressure 2.8s ease-in-out infinite}
   .v130-preheating .v130-steam,.v130-cooking .v130-steam,.v130-warm .v130-steam{opacity:1}
   .v130-preheating .v130-steam i,.v130-cooking .v130-steam i,.v130-warm .v130-steam i{animation:v130Steam 2s ease-out infinite}
   .v130-preheating .v130-live-screen{box-shadow:0 0 18px rgba(255,137,55,.36),inset 0 0 0 1px rgba(255,255,255,.08)}
   .v130-preheating .v130-screen-symbol,.v130-preheating .v130-screen-progress i{color:#ff9a55;background:#ff9a55}
   .v130-cooking .v130-live-screen{box-shadow:0 0 20px rgba(69,218,158,.34),inset 0 0 0 1px rgba(255,255,255,.08)}
   .v130-warm{animation:v130Float 4s ease-in-out infinite}.v130-warm .v130-screen-symbol,.v130-warm .v130-screen-progress i{color:#ffd36b;background:#ffd36b}
   .v130-done{animation:v130Done 1.2s ease-out 1}.v130-done .v130-live-screen{box-shadow:0 0 22px rgba(60,220,110,.42),inset 0 0 0 1px rgba(255,255,255,.08)}
   .v130-done .v130-screen-symbol{color:#62e58c}
   @keyframes v130Steam{0%{transform:translateY(9px) scale(.8);opacity:0}25%{opacity:.65}100%{transform:translateY(-20px) translateX(4px) scale(1.25);opacity:0}}
   @keyframes v130Pressure{0%,100%{transform:translateY(0) scale(1)}50%{transform:translateY(-1.5px) scale(1.004)}}
   @keyframes v130Float{0%,100%{transform:translateY(0)}50%{transform:translateY(-2px)}}
   @keyframes v130Spin{to{transform:rotate(360deg)}}@keyframes v130Load{0%{transform:translateX(-110%)}50%{transform:translateX(90%)}100%{transform:translateX(210%)}}
   @keyframes v130Done{0%{transform:scale(.96)}55%{transform:scale(1.025)}100%{transform:scale(1)}}
   @media(max-width:700px){.v130-device-summary{gap:12px;min-height:112px}.v130-model{flex-basis:118px;width:118px}.v130-device-title{font-size:18px}.v130-device-state{font-size:14px}.v130-device-recipe{font-size:13px}.v130-device-detail{font-size:12px}.v130-screen-copy strong{font-size:5.4px}.v130-screen-copy span{font-size:4.4px}}
   @media(prefers-reduced-motion:reduce){.v130-model,.v130-steam i,.v130-screen-symbol,.v130-screen-progress i{animation:none!important}}
  `;this.shadowRoot.append(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v130',Cook4MeRecipeHubPanelV130);
