import "./cook4me-panel-v3.js";

const BasePanel = customElements.get("cook4me-recipe-hub-panel-v3");

const EXTRA = {
  en: {
    translating:"Translating recipes…",
    translated:"AI translation · source",
    translationUnavailable:"No AI Conversation agent is available for recipes that SEB does not provide in your Home Assistant language.",
    officialLocalization:"Official SEB localization",
  },
  de: {
    translating:"Rezepte werden übersetzt…",
    translated:"KI-Übersetzung · Quelle",
    translationUnavailable:"Für Rezepte, die SEB nicht in deiner Home-Assistant-Sprache anbietet, ist kein KI-Conversation-Agent zur Übersetzung verfügbar.",
    officialLocalization:"Offizielle SEB-Lokalisierung",
  },
  el: {
    translating:"Μετάφραση συνταγών…",
    translated:"Μετάφραση AI · πηγή",
    translationUnavailable:"Δεν υπάρχει διαθέσιμος AI Conversation agent για τις συνταγές που η SEB δεν παρέχει στη γλώσσα του Home Assistant.",
    officialLocalization:"Επίσημη μετάφραση SEB",
  },
};

class Cook4MeRecipeHubPanelV4 extends BasePanel {
  constructor(){
    super();
    this._translationCache=new Map();
    this._translationAgentResolved=false;
    this._translationAgentId=null;
  }

  _t(key){return EXTRA[this._langCode()]?.[key]||EXTRA.en[key]||super._t(key);}

  _targetLanguageName(){
    const code=this._langCode();
    try{return new Intl.DisplayNames([code],{type:"language"}).of(code)||code;}
    catch(_e){return code;}
  }

  async _translationAgent(){
    if(this._translationAgentResolved)return this._translationAgentId;
    if(!this._agentsLoaded)await this._loadAgents();
    const agents=this._agents||[];
    const storageKey=`cook4me.translationAgent.${this._entryId||"default"}`;
    let preferred=null;
    try{preferred=localStorage.getItem(storageKey);}catch(_e){}

    const usable=agents.filter(agent=>{
      const id=String(agent?.id||"").toLowerCase();
      // The built-in Home Assistant intent agent is not a generative
      // translation model. Keep every configured external/local LLM agent.
      return id && id!=="conversation.home_assistant" && id!=="home_assistant";
    });
    const chosen=(preferred&&usable.find(a=>String(a.id)===preferred))||usable[0]||null;
    this._translationAgentId=chosen?.id||null;
    this._translationAgentResolved=true;
    if(this._translationAgentId){try{localStorage.setItem(storageKey,this._translationAgentId);}catch(_e){}}
    return this._translationAgentId;
  }

  _speech(response){
    return response?.response?.speech?.plain?.speech
      ||response?.response?.speech?.ssml?.speech
      ||response?.speech?.plain?.speech
      ||"";
  }

  async _conversationJson(prompt,agentId){
    const response=await this._api("conversation/process",{
      text:prompt,
      language:this._hass?.language||this._langCode(),
      agent_id:agentId,
    });
    return this._extractAIJson(this._speech(response));
  }

  _translationKey(recipe,kind="card"){
    const id=recipe?.displayVariantId||recipe?.searchVariantId||recipe?.variantFunctionalId||recipe?.sendVariantId||recipe?.title||"recipe";
    return `${kind}|${this._langCode()}|${id}`;
  }

  _applyCardTranslation(recipe,translated){
    if(!translated||typeof translated!=="object")return;
    const source=recipe.translatedFrom||recipe.sourceLanguage||this._recipeLanguage(recipe)||"";
    if(translated.title)recipe.title=String(translated.title);
    if(Array.isArray(translated.ingredients)&&translated.ingredients.length)recipe.ingredients=translated.ingredients.map(String);
    if(Array.isArray(translated.missing)&&recipe.match){
      recipe.match={...recipe.match,missingIngredients:translated.missing.map(String)};
    }
    recipe.translatedFrom=source;
    recipe.language=this._langCode();
    recipe.translationRequired=false;
    recipe.translationMethod="ha_conversation";
    delete recipe.translationUnavailable;
  }

  async _translateCardChunk(recipes,agentId){
    const target=this._targetLanguageName();
    const payload=recipes.map((recipe,index)=>({
      id:String(index),
      title:this._clean(recipe.title||""),
      ingredients:(recipe.ingredients||[]).slice(0,10).map(item=>this._ingredientText(item)).filter(Boolean),
      missing:(recipe.match?.missingIngredients||[]).slice(0,8).map(item=>this._clean(item)).filter(Boolean),
    }));
    const prompt=`Translate the following recipe DISPLAY TEXT to ${target}. The source recipes may use different languages.\n\nRules:\n- Translate only human-readable text.\n- Never change, round, invent, remove or reorder numbers, quantities, measurements or ingredient entries.\n- Preserve proper names when appropriate.\n- Do not add cooking advice or ingredients.\n- Keep each id exactly unchanged.\n- Return ONLY valid JSON, no markdown.\n\nReturn this exact schema: {"recipes":[{"id":"0","title":"...","ingredients":["..."],"missing":["..."]}]}\n\nINPUT:\n${JSON.stringify({recipes:payload})}`;
    const translated=await this._conversationJson(prompt,agentId);
    const rows=Array.isArray(translated?.recipes)?translated.recipes:[];
    const byId=new Map(rows.map(row=>[String(row?.id),row]));
    recipes.forEach((recipe,index)=>{
      const row=byId.get(String(index));
      if(row)this._applyCardTranslation(recipe,row);
    });
  }

  async _translateCollection(items){
    const target=this._langCode();
    const pending=(items||[]).filter(recipe=>{
      const source=this._recipeLanguage(recipe)||String(recipe?.sourceLanguage||"").toLowerCase();
      return recipe?.translationRequired===true || (!!source&&source!==target);
    });
    if(!pending.length)return {translated:0,unavailable:0};

    const agentId=await this._translationAgent();
    if(!agentId){
      pending.forEach(recipe=>recipe.translationUnavailable=true);
      return {translated:0,unavailable:pending.length};
    }

    let translatedCount=0;
    for(let offset=0;offset<pending.length;offset+=6){
      const chunk=pending.slice(offset,offset+6);
      const uncached=[];
      for(const recipe of chunk){
        const key=this._translationKey(recipe,"card");
        const cached=this._translationCache.get(key);
        if(cached){this._applyCardTranslation(recipe,cached);translatedCount++;}
        else uncached.push(recipe);
      }
      if(uncached.length){
        try{
          await this._translateCardChunk(uncached,agentId);
          for(const recipe of uncached){
            if(recipe.translationMethod==="ha_conversation"){
              this._translationCache.set(this._translationKey(recipe,"card"),{
                title:recipe.title,
                ingredients:recipe.ingredients,
                missing:recipe.match?.missingIngredients||[],
              });
              translatedCount++;
            }else recipe.translationUnavailable=true;
          }
        }catch(_e){
          uncached.forEach(recipe=>recipe.translationUnavailable=true);
        }
      }
      // Progressive rerender: the user sees localized cards as each batch is
      // translated instead of waiting for the entire result set.
      if(this._tab==="official"||this._tab==="recommend")this._renderTab();
    }
    return {translated:translatedCount,unavailable:pending.filter(x=>x.translationUnavailable).length};
  }

  async _translateDetail(recipe){
    const source=recipe?.translatedFrom||recipe?.sourceLanguage||this._recipeLanguage(recipe)||"";
    const target=this._langCode();
    if(!source||source===target)return recipe;

    const key=this._translationKey(recipe,"detail");
    const cached=this._translationCache.get(key);
    if(cached)return {...recipe,...cached};

    const agentId=await this._translationAgent();
    if(!agentId)return {...recipe,translationUnavailable:true};

    const ingredients=(recipe.ingredients||[]).map(item=>this._ingredientText(item)).filter(Boolean);
    const steps=(recipe.steps||[]).map(step=>this._stepText(step)).filter(Boolean);
    const targetName=this._targetLanguageName();
    const prompt=`Translate this recipe DISPLAY TEXT to ${targetName}.\n\nRules:\n- Keep every number, time, temperature, quantity and measurement semantically identical.\n- Do not add/remove ingredients or steps.\n- Preserve the order of ingredients and steps.\n- Translate cooking instructions naturally and accurately.\n- Return ONLY valid JSON, no markdown.\n\nReturn exactly: {"title":"...","ingredients":["..."],"steps":["..."]}\nThe ingredient and step arrays must have the same lengths as the input.\n\nINPUT:\n${JSON.stringify({title:this._clean(recipe.title||""),ingredients,steps})}`;
    try{
      const translated=await this._conversationJson(prompt,agentId);
      const output={...recipe};
      if(translated?.title)output.title=String(translated.title);
      if(Array.isArray(translated?.ingredients)&&translated.ingredients.length===ingredients.length)output.ingredients=translated.ingredients.map(String);
      if(Array.isArray(translated?.steps)&&translated.steps.length===steps.length)output.steps=translated.steps.map(String);
      output.translatedFrom=source;
      output.language=target;
      output.translationRequired=false;
      output.translationMethod="ha_conversation";
      this._translationCache.set(key,{
        title:output.title,
        ingredients:output.ingredients,
        steps:output.steps,
        translatedFrom:source,
        language:target,
        translationRequired:false,
        translationMethod:"ha_conversation",
      });
      return output;
    }catch(_e){
      return {...recipe,translationUnavailable:true};
    }
  }

  _recipeCard(recipe,custom=false){
    let html=super._recipeCard(recipe,custom);
    if(recipe?.translationMethod==="ha_conversation"&&recipe?.translatedFrom){
      const chip=`<span class="chip">🌐 ${this._escape(this._t("translated"))}: ${this._escape(String(recipe.translatedFrom).toUpperCase())}</span>`;
      html=html.replace('<div class="chips">',`<div class="chips">${chip}`);
    }else if(recipe?.translationUnavailable&&recipe?.translationRequired){
      const chip=`<span class="chip warn">🌐 ${this._escape(this._t("translationUnavailable"))}</span>`;
      html=html.replace('<div class="chips">',`<div class="chips">${chip}`);
    }
    return html;
  }

  _detailHtml(recipe){
    let html=super._detailHtml(recipe);
    if(!html)return html;
    if(recipe?.translationMethod==="ha_conversation"&&recipe?.translatedFrom){
      const notice=`<div class="notice">🌐 ${this._escape(this._t("translated"))}: ${this._escape(String(recipe.translatedFrom).toUpperCase())}</div>`;
      html=html.replace('<div class="detail-head">',`${notice}<div class="detail-head">`);
    }else if(recipe?.translationUnavailable&&recipe?.translationRequired){
      const notice=`<div class="notice">${this._escape(this._t("translationUnavailable"))}</div>`;
      html=html.replace('<div class="detail-head">',`${notice}<div class="detail-head">`);
    }
    return html;
  }

  async _search(query){
    this._searchQuery=String(query||"").trim();
    this._opened=null;
    try{
      this._message(this._t("loading"));
      const result=await this._api("cook4me/search",{
        entry_id:this._entryId,
        query:this._searchQuery,
        size:20,
        language:this._langCode(),
      });
      this._results=result?.items||[];
      this._message("");
      this._renderTab();
      const pending=this._results.filter(x=>x.translationRequired).length;
      if(pending){
        this._message(`${this._t("translating")} (${pending})`);
        const status=await this._translateCollection(this._results);
        if(status.unavailable)this._message(this._t("translationUnavailable"),true);
        else this._message("");
        this._renderTab();
      }
    }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
  }

  async _recommend(){
    this._opened=null;
    try{
      this._message(this._t("loading"));
      const result=await this._api("cook4me/recommend",{
        entry_id:this._entryId,
        limit:12,
        catalog_size:24,
        language:this._langCode(),
      });
      this._recommendations=result?.items||[];
      this._message("");
      this._renderTab();
      const pending=this._recommendations.filter(x=>x.translationRequired).length;
      if(pending){
        this._message(`${this._t("translating")} (${pending})`);
        const status=await this._translateCollection(this._recommendations);
        if(status.unavailable)this._message(this._t("translationUnavailable"),true);
        else this._message("");
        this._renderTab();
      }
    }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
  }

  async _openOfficial(recipe){
    const variant=recipe.displayVariantId||recipe.searchVariantId||recipe.variantFunctionalId||recipe.recipeFunctionalId;
    if(!variant){
      this._opened=await this._translateDetail({...recipe});
      this._renderTab();this._scrollToDetail();return;
    }
    try{
      this._message(this._t("loading"));
      let detail;
      const hasText=Array.isArray(recipe.steps)&&recipe.steps.some(step=>this._stepText(step));
      if(hasText)detail={...recipe};
      else detail=await this._api("cook4me/recipe_detail",{
        entry_id:this._entryId,
        variant_id:String(variant),
        language:this._langCode(),
      });
      detail={
        ...recipe,
        ...detail,
        sendVariantId:recipe.sendVariantId||detail.sendVariantId||recipe.searchVariantId,
        sendGroupingFunctionalId:recipe.sendGroupingFunctionalId||detail.sendGroupingFunctionalId,
        sendRecipeFunctionalId:recipe.sendRecipeFunctionalId||detail.sendRecipeFunctionalId,
      };
      const source=detail.translatedFrom||detail.sourceLanguage||this._recipeLanguage(detail)||"";
      if(detail.translationRequired||recipe.translationRequired||recipe.translatedFrom||(source&&source!==this._langCode())){
        if(recipe.translatedFrom&&!detail.translatedFrom)detail.translatedFrom=recipe.translatedFrom;
        detail=await this._translateDetail(detail);
      }
      this._opened=detail;
      this._message("");
      this._renderTab();
      this._scrollToDetail();
    }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
  }
}

customElements.define("cook4me-recipe-hub-panel-v4",Cook4MeRecipeHubPanelV4);
