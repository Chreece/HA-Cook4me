// Resize the existing preview; rotation must not reopen the camera or lose a draft.
export const CAMERA_TEXT={
 en:{frame:'Photograph the whole receipt. No alignment box is required.'},
 de:{frame:'Fotografiere den gesamten Kassenbon. Es ist kein Ausrichtungsrahmen erforderlich.'},
 el:{frame:'Φωτογράφισε ολόκληρη την απόδειξη. Δεν χρειάζεται ευθυγράμμιση σε πλαίσιο.'}
};
export const RECEIPT_ICON='mdi:receipt-text-outline';
export function cameraLayout(width,height,header=0,videoWidth=0,videoHeight=0){
 const w=Math.max(1,Number(width)||1),h=Math.max(1,Number(height)||1);
 return {landscape:w>h,height:Math.max(150,h-Math.max(0,header)-24),
  ratio:videoWidth>0&&videoHeight>0?videoWidth/videoHeight:w/h};
}
export const ScannerCameraMixin=Base=>class extends Base {
 _r195Text(key){
  const lang=String(this._uiIngredientLanguage?.()||'en').split(/[-_]/)[0];
  return key==='frame'?(CAMERA_TEXT[lang]||CAMERA_TEXT.en).frame:super._r195Text(key);
 }
 _v202CameraDispose(){
  const state=this._v202CameraWatch;if(!state)return;
  state.observer?.disconnect();state.controller.abort();
  if(state.frameRequest)cancelAnimationFrame(state.frameRequest);
  this._v202CameraWatch=null;
 }
 _v202CameraLayout(){
  const c=this._v78Dialog,frame=c?.querySelector('[data-v111-frame]'),d=this._v78Draft;
  if(!c||!frame||!d)return;
  const video=frame.querySelector('video'),viewport=window.visualViewport;
  const header=c.querySelector(':scope > header')?.getBoundingClientRect().height||0;
  const layout=cameraLayout(viewport?.width||window.innerWidth,viewport?.height||window.innerHeight,header,video?.videoWidth,video?.videoHeight);
  c.classList.toggle('v202-camera-live',!d.editorOpen&&!this._v180CameraUnavailable);
  c.classList.toggle('v202-camera-landscape',layout.landscape);
  frame.classList.toggle('v202-receipt-camera',d.mode==='receipt');
  c.style.setProperty('--v202-camera-height',layout.height+'px');
  c.style.setProperty('--v202-video-ratio',String(layout.ratio));
  const modes=frame.querySelector('.v111-modes'),bottom=frame.querySelector('.v111-bottom');
  const top=(modes?.offsetHeight||56)+20,below=(bottom?.offsetHeight||56)+20;
  frame.style.setProperty('--v202-camera-top',top+'px');
  frame.style.setProperty('--v202-camera-bottom',below+'px');
  const receipt=frame.querySelector('[data-v80-scan="receipt"]');
  receipt?.querySelector('ha-icon')?.setAttribute('icon',RECEIPT_ICON);
  const guide=frame.querySelector('[data-v111-guide]');
  if(guide){guide.hidden=d.mode==='receipt';guide.setAttribute('aria-hidden',String(d.mode==='receipt'));}
 }
 _v202CameraDecorate(){
  const c=this._v78Dialog,frame=c?.querySelector('[data-v111-frame]');
  if(!c||!frame){this._v202CameraDispose();return;}
  if(!this.shadowRoot.querySelector('#v202CameraStyles')){
   const style=document.createElement('style');style.id='v202CameraStyles';style.textContent=`
    .v78-capture.v202-camera-live>.v78-capture-body{max-width:1400px;width:100%;box-sizing:border-box;padding:10px 12px;margin:0 auto}
    .v78-capture.v202-camera-live .v111-camera[data-v111-frame]{height:var(--v202-camera-height)!important;min-height:0!important;max-height:none!important;width:100%!important;aspect-ratio:auto}
    .v202-camera-live .v111-photo-help{display:none}.v202-camera-live .v111-modes{flex-wrap:wrap;gap:5px}
    .v202-camera-live .v111-guide-wrap{inset:var(--v202-camera-top) 16px var(--v202-camera-bottom);min-height:0;gap:8px}
    .v202-camera-live .v111-guide{min-height:0;max-height:60%;flex-shrink:1}.v202-camera-landscape .v111-guide-wrap p,.v202-camera-landscape .v111-guide-wrap small{font-size:.8rem;padding:4px 8px}
    .v202-camera-live .v111-result{top:var(--v202-camera-top);bottom:var(--v202-camera-bottom)}
    .v202-receipt-camera [data-v111-guide]{display:none!important;border:0!important;box-shadow:none!important}
    .v202-receipt-camera video{object-fit:contain!important;background:#101417}
    .v202-receipt-camera [data-v111-guide-wrap]{justify-content:flex-start;pointer-events:none}
    .v202-receipt-camera [data-v111-target]{display:none!important}
    .v202-receipt-camera [data-r199-photo-privacy]{font-size:.75rem;line-height:1.3;max-width:52ch}
    .v202-camera-live [data-v112-editor]{top:var(--v202-camera-top);bottom:var(--v202-camera-bottom)}
    @media(orientation:landscape) and (max-height:540px){
     .v78-capture.v202-camera-live>header{padding:6px 12px}.v202-camera-live>header .v78-eyebrow{display:none}
     .v202-camera-live>header h2{font-size:1rem;margin:0}.v202-camera-live .v111-modes{top:5px;padding:3px}.v202-camera-live .v111-bottom{bottom:5px;padding:3px}
     .v202-camera-live .v111-guide{width:min(70%,520px)}.v202-receipt-camera [data-r199-photo-privacy]{display:none}
    }
   `;this.shadowRoot.append(style);
  }
  const video=frame.querySelector('video');
  if(this._v202CameraWatch?.frame!==frame||this._v202CameraWatch?.video!==video){
   this._v202CameraDispose();
   const state={frame,video,controller:new AbortController()};this._v202CameraWatch=state;
   const schedule=()=>{if(this._v202CameraWatch!==state||state.frameRequest)return;state.frameRequest=requestAnimationFrame(()=>{state.frameRequest=0;if(this._v202CameraWatch===state&&frame.isConnected)this._v202CameraLayout();});};
   const options={signal:state.controller.signal};
   window.addEventListener('resize',schedule,options);
   window.visualViewport?.addEventListener('resize',schedule,options);
   window.screen?.orientation?.addEventListener('change',schedule,options);
   video?.addEventListener('loadedmetadata',schedule,options);video?.addEventListener('resize',schedule,options);
   if(typeof ResizeObserver==='function'){
    state.observer=new ResizeObserver(schedule);
    for(const node of [c.querySelector(':scope > header'),frame.querySelector('.v111-modes'),frame.querySelector('.v111-bottom')])if(node)state.observer.observe(node);
   }
  }
  this._v202CameraLayout();
 }
 // Receipt capture always uses the uncropped source frame, regardless of the
 // preview's portrait/landscape aspect ratio. Other scan modes keep their ROI.
 _v111Canvas(crop=true){return super._v111Canvas(this._v78Draft?.mode==='receipt'?false:crop);}
 _v78RenderCapture(){const result=super._v78RenderCapture();this._v202CameraDecorate();return result;}
 _v111Paint(){const result=super._v111Paint();this._v202CameraDecorate();return result;}
 _v78Close(force=false){const result=super._v78Close(force);if(!this._v78Dialog)this._v202CameraDispose();return result;}
 disconnectedCallback(){this._v202CameraDispose();super.disconnectedCallback();}
};
