import "./cook4me-panel-v9.js";

const BasePanel = customElements.get("cook4me-recipe-hub-panel-v9");

const TEXT = {
  en:{fallback:"KRUPS rejected the newer search body; compatibility search is active for this request."},
  de:{fallback:"KRUPS hat den neueren Such-Body abgelehnt; für diese Anfrage ist die Kompatibilitätssuche aktiv."},
  el:{fallback:"Η KRUPS απέρριψε το νεότερο σώμα αναζήτησης· για αυτή την αναζήτηση χρησιμοποιείται προσωρινά το συμβατό request."},
};

class Cook4MeRecipeHubPanelV10 extends BasePanel {
  constructor(){
    super();
    this._catalogFallbackNotice="";
  }

  _v10Text(key){return TEXT[this._langCode()]?.[key]||TEXT.en[key]||key;}

  async _api(type,data={}){
    const mapped={
      "cook4me/v8/search":"cook4me/v10/search",
      "cook4me/v9/search":"cook4me/v10/search",
      "cook4me/v8/recommend":"cook4me/v10/recommend",
      "cook4me/v9/recommend":"cook4me/v10/recommend",
    }[type]||type;
    const result=await super._api(mapped,data);
    if((mapped==="cook4me/v10/search"||mapped==="cook4me/v10/recommend")&&result?.ok===false){
      const error=new Error(String(result.error||"KRUPS recipe catalog request was rejected"));
      error.catalogDiagnostic=result.catalogDiagnostic||null;
      throw error;
    }
    if((mapped==="cook4me/v10/search"||mapped==="cook4me/v10/recommend")&&result?.fallbackUsed){
      this._catalogFallbackNotice=String(result.catalogDiagnosticSummary||this._v10Text("fallback"));
    }
    return result;
  }

  async _search(query){
    this._catalogFallbackNotice="";
    await super._search(query);
    if(this._catalogFallbackNotice&&this._results.length){
      this._message(`${this._v10Text("fallback")} ${this._catalogFallbackNotice}`);
    }
  }

  async _recommend(){
    this._catalogFallbackNotice="";
    await super._recommend();
    if(this._catalogFallbackNotice&&this._recommendations.length){
      this._message(`${this._v10Text("fallback")} ${this._catalogFallbackNotice}`);
    }
  }
}

customElements.define("cook4me-recipe-hub-panel-v10",Cook4MeRecipeHubPanelV10);
