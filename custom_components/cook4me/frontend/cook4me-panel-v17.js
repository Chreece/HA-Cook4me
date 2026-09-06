import "./cook4me-panel-v16.js";

const BasePanel = customElements.get("cook4me-recipe-hub-panel-v16");

const TEXT = {
  en:{
    scanShopping:"Scan shopping",scanHelp:"Keep the camera open and scan each product barcode. Known products are added immediately; unknown products need one mapping, then future scans are automatic.",
    startScanner:"Start camera scanner",stopScanner:"Stop scanner",cameraUnsupported:"Live barcode scanning is not supported by this browser. You can still enter the barcode below.",
    cameraError:"Could not open the camera",barcode:"Barcode",scanBarcode:"Scan / look up",lookingUp:"Looking up product…",scanReady:"Point the rear camera at an EAN/UPC barcode.",
    scannedAdded:"Added to house stock",mapProduct:"Map this product once",mapHelp:"Choose the Cook4Me ingredient and package amount. This barcode will be remembered for future automatic scans.",
    product:"Product",packageAmount:"Package amount",mapAndAdd:"Save mapping & add",unknownProduct:"Unknown product",chooseIngredient:"Cook4Me ingredient",invalidIngredient:"Choose an ingredient from the Cook4Me catalog.",
  },
  de:{
    scanShopping:"Einkauf scannen",scanHelp:"Kamera geöffnet lassen und nacheinander die Barcodes der Einkäufe scannen. Bekannte Produkte werden sofort addiert; unbekannte Produkte müssen nur einmal zugeordnet werden.",
    startScanner:"Kamera-Scanner starten",stopScanner:"Scanner stoppen",cameraUnsupported:"Dieser Browser unterstützt keinen Live-Barcodescanner. Der Barcode kann unten weiterhin eingegeben werden.",
    cameraError:"Kamera konnte nicht geöffnet werden",barcode:"Barcode",scanBarcode:"Scannen / suchen",lookingUp:"Produkt wird gesucht…",scanReady:"EAN/UPC-Barcode vor die Rückkamera halten.",
    scannedAdded:"Zum Vorrat hinzugefügt",mapProduct:"Produkt einmal zuordnen",mapHelp:"Cook4Me-Zutat und Packungsmenge wählen. Dieser Barcode wird danach bei jedem Scan automatisch erkannt.",
    product:"Produkt",packageAmount:"Packungsmenge",mapAndAdd:"Zuordnung speichern & hinzufügen",unknownProduct:"Unbekanntes Produkt",chooseIngredient:"Cook4Me-Zutat",invalidIngredient:"Bitte eine Zutat aus dem Cook4Me-Katalog auswählen.",
  },
  el:{
    scanShopping:"Σάρωση αγορών",scanHelp:"Άφησε την κάμερα ανοιχτή και σκάναρε διαδοχικά το barcode κάθε προϊόντος. Τα γνωστά προϊόντα προστίθενται αμέσως· τα άγνωστα χρειάζονται αντιστοίχιση μόνο την πρώτη φορά.",
    startScanner:"Έναρξη scanner κάμερας",stopScanner:"Διακοπή scanner",cameraUnsupported:"Ο browser δεν υποστηρίζει live σάρωση barcode. Μπορείς ακόμη να εισαγάγεις τον barcode παρακάτω.",
    cameraError:"Δεν ήταν δυνατό να ανοίξει η κάμερα",barcode:"Barcode",scanBarcode:"Σάρωση / αναζήτηση",lookingUp:"Αναζήτηση προϊόντος…",scanReady:"Στρέψε την πίσω κάμερα σε barcode EAN/UPC.",
    scannedAdded:"Προστέθηκε στο απόθεμα",mapProduct:"Αντιστοίχιση προϊόντος μία φορά",mapHelp:"Επίλεξε το υλικό Cook4Me και την ποσότητα συσκευασίας. Ο barcode θα θυμάται την αντιστοίχιση για τις επόμενες σαρώσεις.",
    product:"Προϊόν",packageAmount:"Ποσότητα συσκευασίας",mapAndAdd:"Αποθήκευση αντιστοίχισης & προσθήκη",unknownProduct:"Άγνωστο προϊόν",chooseIngredient:"Υλικό Cook4Me",invalidIngredient:"Επίλεξε υλικό από τον κατάλογο Cook4Me.",
  },
};

class Cook4MeRecipeHubPanelV17 extends BasePanel {
  constructor(){
    super();
    this._scannerOpen=false;
    this._scannerStream=null;
    this._scannerDetector=null;
    this._scannerTimer=null;
    this._scannerBusy=false;
    this._scannerStatus="";
    this._scannerResult=null;
    this._scannerLastCode="";
    this._scannerLastAt=0;
  }

  _t(key){return TEXT[this._langCode()]?.[key]||TEXT.en[key]||super._t(key);}

  _stopBarcodeCamera(close=false){
    if(this._scannerTimer){clearTimeout(this._scannerTimer);this._scannerTimer=null;}
    if(this._scannerStream){
      for(const track of this._scannerStream.getTracks?.()||[])track.stop();
      this._scannerStream=null;
    }
    this._scannerDetector=null;
    if(close)this._scannerOpen=false;
  }

  _renderTab(){
    if(this._tab!=="profile")this._stopBarcodeCamera(true);
    super._renderTab();
  }

  _scannerHtml(){
    return `<div class="field wide" id="shoppingScannerBlock" style="border:1px solid var(--divider-color);border-radius:14px;padding:14px">
      <div class="detail-head"><div><h3 style="margin:0">📷 ${this._escape(this._t("scanShopping"))}</h3><div class="muted" style="margin-top:4px">${this._escape(this._t("scanHelp"))}</div></div>
      <button id="scannerToggle" type="button" class="btn secondary">${this._escape(this._scannerOpen?this._t("stopScanner"):this._t("startScanner"))}</button></div>
      ${this._scannerOpen?`<div style="margin-top:12px">
        <video id="shoppingScannerVideo" playsinline autoplay muted style="width:100%;max-height:340px;object-fit:cover;background:#000;border-radius:12px"></video>
        <div id="scannerStatus" class="muted" style="margin:8px 0">${this._escape(this._scannerStatus||this._t("scanReady"))}</div>
        <div class="toolbar"><input id="manualBarcode" class="grow" inputmode="numeric" autocomplete="off" placeholder="${this._escape(this._t("barcode"))}"><button id="manualBarcodeBtn" type="button" class="btn secondary">${this._escape(this._t("scanBarcode"))}</button></div>
        <div id="scannerResult" style="margin-top:10px">${this._scannerResultHtml()}</div>
      </div>`:""}
    </div>`;
  }

  _scannerResultHtml(){
    const result=this._scannerResult;
    if(!result)return "";
    if(result.status==="added"){
      const mapping=result.mapping||{}; const ingredient=mapping.ingredient||{};
      const amount=mapping.quantity!==undefined&&mapping.quantity!==null?`${mapping.quantity}${mapping.unit?` ${mapping.unit}`:""}`:"";
      const product=mapping.productName||result.product?.productName||ingredient.name||result.barcode;
      return `<div class="notice">✓ ${this._escape(this._t("scannedAdded"))}: <strong>${this._escape(product)}</strong> → ${this._escape(ingredient.name||"")} ${amount?`(${this._escape(amount)})`:""}</div>`;
    }
    if(result.status!=="needs_mapping")return "";
    const product=result.product||{};
    const first=result.suggestions?.[0]?.ingredient||result.mapping?.ingredient||{};
    const defaultName=String(first.name||"");
    const quantity=product.quantity??result.mapping?.quantity??1;
    const unit=String(product.unit||result.mapping?.unit||"pcs");
    const options=(this._ingredientCatalog||[]).map(row=>`<option value="${this._escape(row.name||"")}"></option>`).join("");
    const productName=product.productName||product.name||result.mapping?.productName||this._t("unknownProduct");
    const brand=product.brand||result.mapping?.brand||"";
    return `<div class="card" style="padding:12px;margin:0">
      <h3 style="margin:0 0 4px">${this._escape(this._t("mapProduct"))}</h3>
      <div class="muted">${this._escape(this._t("mapHelp"))}</div>
      <div style="margin:10px 0"><strong>${this._escape(this._t("product"))}:</strong> ${this._escape(productName)}${brand?` · ${this._escape(brand)}`:""}<br><span class="muted">${this._escape(result.barcode||"")}${product.rawQuantity?` · ${this._escape(product.rawQuantity)}`:""}</span></div>
      <div class="formgrid">
        <div class="field wide"><label>${this._escape(this._t("chooseIngredient"))}</label><input id="scanIngredientName" list="scanIngredientCatalog" value="${this._escape(defaultName)}"><datalist id="scanIngredientCatalog">${options}</datalist></div>
        <div class="field"><label>${this._escape(this._t("packageAmount"))}</label><input id="scanPackageAmount" type="number" min="0" step="any" value="${this._escape(quantity)}"></div>
        <div class="field"><label>${this._escape(this._t("unit"))}</label><input id="scanPackageUnit" value="${this._escape(unit)}" list="cook4meStockUnits"></div>
      </div>
      <button id="scanMapAdd" type="button" class="btn" style="margin-top:8px">${this._escape(this._t("mapAndAdd"))}</button>
    </div>`;
  }

  _renderScannerResult(c){
    const target=c.querySelector("#scannerResult");
    if(target){target.innerHTML=this._scannerResultHtml();this._bindScannerMapping(c);}
    const status=c.querySelector("#scannerStatus");
    if(status)status.textContent=this._scannerStatus||this._t("scanReady");
  }

  _catalogRowByName(name){
    const target=String(name||"").trim().toLocaleLowerCase();
    return (this._ingredientCatalog||[]).find(row=>String(row?.name||"").trim().toLocaleLowerCase()===target)||null;
  }

  _bindScannerMapping(c){
    c.querySelector("#scanMapAdd")?.addEventListener("click",async()=>{
      const result=this._scannerResult; if(!result?.barcode)return;
      const name=String(c.querySelector("#scanIngredientName")?.value||"").trim();
      const ingredient=this._catalogRowByName(name);
      if(!ingredient){this._scannerStatus=this._t("invalidIngredient");this._renderScannerResult(c);return;}
      const quantity=String(c.querySelector("#scanPackageAmount")?.value||"").trim();
      const unit=String(c.querySelector("#scanPackageUnit")?.value||"").trim();
      if(!quantity)return;
      this._scannerBusy=true;this._scannerStatus=this._t("lookingUp");this._renderScannerResult(c);
      try{
        const mapped=await this._api("cook4me/v15/barcode_map_add",{
          entry_id:this._entryId,barcode:String(result.barcode),ingredient,
          quantity,unit,product_name:String(result.product?.productName||result.product?.name||""),brand:String(result.product?.brand||""),
        });
        this._houseIngredients=mapped?.houseIngredients||[];this._syncEntryProfile();this._renderInventoryOnly(c);
        this._scannerResult=mapped;this._scannerStatus=this._t("scannedAdded");navigator.vibrate?.(80);
      }catch(e){this._scannerStatus=`${this._t("error")}: ${e.message||e}`;}
      finally{this._scannerBusy=false;this._renderScannerResult(c);}
    });
  }

  async _handleBarcode(code,c){
    code=String(code||"").replace(/[\s-]+/g,"");
    if(!code||this._scannerBusy)return;
    const now=Date.now();
    if(code===this._scannerLastCode&&now-this._scannerLastAt<1200)return;
    this._scannerLastCode=code;this._scannerLastAt=now;
    this._scannerBusy=true;this._scannerStatus=this._t("lookingUp");this._renderScannerResult(c);
    try{
      const result=await this._api("cook4me/v15/barcode_scan",{
        entry_id:this._entryId,barcode:code,language:this._ingredientCatalogLanguage||this._capabilities?.deviceCatalogLanguage||"de",
      });
      this._scannerResult=result;
      this._houseIngredients=result?.houseIngredients||this._houseIngredients;this._syncEntryProfile();this._renderInventoryOnly(c);
      if(result?.status==="added"){
        this._scannerStatus=this._t("scannedAdded");navigator.vibrate?.(80);
      }else{
        this._scannerStatus=this._t("mapProduct");navigator.vibrate?.([40,40,40]);
      }
    }catch(e){this._scannerStatus=`${this._t("error")}: ${e.message||e}`;}
    finally{this._scannerBusy=false;this._renderScannerResult(c);}
  }

  async _startBarcodeCamera(c){
    if(!this._scannerOpen||this._scannerStream)return;
    const video=c.querySelector("#shoppingScannerVideo"); if(!video)return;
    if(!navigator.mediaDevices?.getUserMedia||!("BarcodeDetector" in globalThis)){
      this._scannerStatus=this._t("cameraUnsupported");this._renderScannerResult(c);return;
    }
    try{
      let formats=[];
      try{
        const supported=await BarcodeDetector.getSupportedFormats();
        formats=["ean_13","ean_8","upc_a","upc_e","itf"].filter(format=>supported.includes(format));
      }catch(_e){}
      this._scannerDetector=formats.length?new BarcodeDetector({formats}):new BarcodeDetector();
      this._scannerStream=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:"environment"}},audio:false});
      video.srcObject=this._scannerStream;await video.play();
      this._scannerStatus=this._t("scanReady");this._renderScannerResult(c);
      const tick=async()=>{
        if(!this._scannerOpen||!this._scannerDetector||!this._scannerStream)return;
        if(!this._scannerBusy&&video.readyState>=2){
          try{
            const found=await this._scannerDetector.detect(video);
            const code=found?.[0]?.rawValue;
            if(code)void this._handleBarcode(code,c);
          }catch(_e){}
        }
        this._scannerTimer=setTimeout(tick,180);
      };
      tick();
    }catch(e){
      this._stopBarcodeCamera(false);
      this._scannerStatus=`${this._t("cameraError")}: ${e.message||e}`;this._renderScannerResult(c);
    }
  }

  _bindScanner(c){
    c.querySelector("#scannerToggle")?.addEventListener("click",()=>{
      if(this._scannerOpen){this._stopBarcodeCamera(true);this._scannerStatus="";this._scannerResult=null;this._renderProfile(c);}
      else{this._scannerOpen=true;this._scannerStatus=this._t("scanReady");this._renderProfile(c);}
    });
    const manual=()=>{const code=String(c.querySelector("#manualBarcode")?.value||"").trim();if(code)void this._handleBarcode(code,c);};
    c.querySelector("#manualBarcodeBtn")?.addEventListener("click",manual);
    c.querySelector("#manualBarcode")?.addEventListener("keydown",event=>{if(event.key==="Enter")manual();});
    this._bindScannerMapping(c);
  }

  _renderProfile(c){
    this._stopBarcodeCamera(false);
    super._renderProfile(c);
    const grid=c.querySelector(".formgrid");
    if(!grid)return;
    grid.insertAdjacentHTML("afterbegin",this._scannerHtml());
    this._bindScanner(c);
    if(this._scannerOpen)queueMicrotask(()=>void this._startBarcodeCamera(c));
  }
}

customElements.define("cook4me-recipe-hub-panel-v17",Cook4MeRecipeHubPanelV17);
