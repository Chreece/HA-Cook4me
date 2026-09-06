import "./cook4me-panel-v17.js";

const BasePanel = customElements.get("cook4me-recipe-hub-panel-v17");

const TEXT = {
  en:{nativeScannerReady:"Home Assistant native scanner is open. Scan EAN/UPC products continuously.",unsupportedNativeCode:"This barcode type is not a supported shopping-product code. Scan an EAN/UPC barcode."},
  de:{nativeScannerReady:"Der native Home-Assistant-Scanner ist geöffnet. EAN/UPC-Produkte können nacheinander gescannt werden.",unsupportedNativeCode:"Dieser Barcode-Typ wird für Einkaufsprodukte nicht unterstützt. Bitte einen EAN/UPC-Barcode scannen."},
  el:{nativeScannerReady:"Ο native scanner του Home Assistant είναι ανοιχτός. Σκάναρε διαδοχικά προϊόντα EAN/UPC.",unsupportedNativeCode:"Αυτός ο τύπος barcode δεν υποστηρίζεται για προϊόντα αγορών. Σκάναρε EAN/UPC barcode."},
};

class Cook4MeRecipeHubPanelV18 extends BasePanel {
  constructor(){
    super();
    this._nativeScannerExternal=null;
    this._nativeScannerOriginalReceive=null;
    this._nativeScannerWrappedReceive=null;
    this._nativeScannerRequest=null;
    this._nativeScannerActive=false;
  }

  _t(key){return TEXT[this._langCode()]?.[key]||TEXT.en[key]||super._t(key);}

  _nativeBarcodeScannerAvailable(){
    const external=this._hass?.auth?.external;
    return Boolean(
      external?.config?.hasBarCodeScanner&&
      typeof external.fireMessage==="function"&&
      typeof external.receiveMessage==="function"
    );
  }

  _restoreNativeScannerReceiver(){
    const external=this._nativeScannerExternal;
    if(
      external&&
      this._nativeScannerWrappedReceive&&
      external.receiveMessage===this._nativeScannerWrappedReceive&&
      this._nativeScannerOriginalReceive
    ){
      external.receiveMessage=this._nativeScannerOriginalReceive;
    }
    this._nativeScannerExternal=null;
    this._nativeScannerOriginalReceive=null;
    this._nativeScannerWrappedReceive=null;
    this._nativeScannerRequest=null;
  }

  _stopNativeBarcodeScanner(sendClose=true){
    const external=this._nativeScannerExternal||this._hass?.auth?.external;
    if(sendClose&&this._nativeScannerActive&&typeof external?.fireMessage==="function"){
      try{external.fireMessage({type:"bar_code/close"});}catch(_e){}
    }
    this._nativeScannerActive=false;
    this._restoreNativeScannerReceiver();
  }

  _stopBarcodeCamera(close=false){
    this._stopNativeBarcodeScanner(true);
    super._stopBarcodeCamera(close);
  }

  async _onNativeBarcodeMessage(msg,c){
    if(!this._nativeScannerActive||!msg||msg.id!==this._nativeScannerRequest?.id)return;
    if(msg.command==="bar_code/aborted"){
      this._stopNativeBarcodeScanner(false);
      this._scannerOpen=false;
      this._scannerStatus="";
      this._renderTab();
      return;
    }
    if(msg.command!=="bar_code/scan_result")return;

    const format=String(msg.payload?.format||"").toLowerCase();
    const allowed=new Set(["ean_13","ean_8","upc_a","upc_e","itf"]);
    if(!allowed.has(format)){
      try{
        this._nativeScannerExternal?.fireMessage({
          type:"bar_code/notify",
          payload:{message:this._t("unsupportedNativeCode")},
        });
      }catch(_e){}
      return;
    }

    await this._handleBarcode(String(msg.payload?.rawValue||""),c);
    if(this._scannerResult?.status==="needs_mapping"){
      // The native overlay covers the panel. Close it while the user performs
      // the one-time mapping, then _bindScannerMapping restarts it automatically.
      this._stopNativeBarcodeScanner(true);
      this._renderScannerResult(c);
    }
  }

  async _startNativeBarcodeScanner(c){
    if(!this._scannerOpen||this._nativeScannerActive||!this._nativeBarcodeScannerAvailable())return;
    const external=this._hass.auth.external;
    const request={
      type:"bar_code/scan",
      payload:{
        title:this._t("scanShopping"),
        description:this._t("scanHelp"),
        alternative_option_label:this._t("stopScanner"),
      },
    };

    const original=external.receiveMessage;
    const wrapped=(msg)=>{
      // Let Home Assistant's normal external-app handler acknowledge and process
      // the command first. We only observe the matching scanner request.
      const result=original.call(external,msg);
      if(
        msg?.type==="command"&&
        (msg.command==="bar_code/scan_result"||msg.command==="bar_code/aborted")&&
        msg.id===request.id
      ){
        queueMicrotask(()=>void this._onNativeBarcodeMessage(msg,c));
      }
      return result;
    };

    this._nativeScannerExternal=external;
    this._nativeScannerOriginalReceive=original;
    this._nativeScannerWrappedReceive=wrapped;
    this._nativeScannerRequest=request;
    external.receiveMessage=wrapped;
    try{
      external.fireMessage(request);
      this._nativeScannerActive=true;
      this._scannerStatus=this._t("nativeScannerReady");
      this._renderScannerResult(c);
    }catch(e){
      this._stopNativeBarcodeScanner(false);
      this._scannerStatus=`${this._t("cameraError")}: ${e.message||e}`;
      this._renderScannerResult(c);
    }
  }

  async _startBarcodeCamera(c){
    if(this._nativeBarcodeScannerAvailable()){
      await this._startNativeBarcodeScanner(c);
      return;
    }
    await super._startBarcodeCamera(c);
  }

  _bindScannerMapping(c){
    c.querySelector("#scanMapAdd")?.addEventListener("click",async()=>{
      const result=this._scannerResult;if(!result?.barcode)return;
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
        this._houseIngredients=mapped?.houseIngredients||[];
        this._syncEntryProfile();
        this._renderInventoryOnly(c);
        this._scannerResult=mapped;
        this._scannerStatus=this._t("scannedAdded");
        navigator.vibrate?.(80);
      }catch(e){
        this._scannerStatus=`${this._t("error")}: ${e.message||e}`;
      }finally{
        this._scannerBusy=false;
        this._renderScannerResult(c);
      }
      if(this._scannerOpen&&this._nativeBarcodeScannerAvailable()&&!this._nativeScannerActive){
        await this._startNativeBarcodeScanner(c);
      }
    });
  }
}

customElements.define("cook4me-recipe-hub-panel-v18",Cook4MeRecipeHubPanelV18);
