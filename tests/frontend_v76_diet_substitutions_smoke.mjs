import assert from 'node:assert/strict';
import {parseHTML} from 'linkedom';
const {window}=parseHTML('<!doctype html><html><body></body></html>');
for(const key of ['document','customElements','HTMLElement','Node','Event','CustomEvent','MutationObserver','Element','ShadowRoot'])if(window[key])globalThis[key]=window[key];
globalThis.window=window;globalThis.requestAnimationFrame=fn=>setTimeout(fn,0);globalThis.cancelAnimationFrame=clearTimeout;
globalThis.ResizeObserver=class{observe(){} disconnect(){}};globalThis.CSS={escape:String};
globalThis.localStorage={getItem:()=>null,setItem(){},removeItem(){}};
await import('../custom_components/cook4me/frontend/cook4me-panel-v76-bundle.js');
const panel=document.createElement('cook4me-recipe-hub-panel-v76');
panel._entryId='one';panel._hass={user:{id:'alice'},language:'el',connection:{sendMessagePromise:async msg=>{calls.push(msg);return {};}}};
panel._entries=[{entry_id:'one',profile:{diet:'omnivore'},recipes:[]}];panel._tab='official';
panel._v63FilterKey=panel._prefKey();panel._v63Filters={diet:'vegetarian',languages:['de'],mealTypes:[]};
const calls=[];
const recipe={id:'one',title:'Duck and prawns',displayVariantId:'r',sendVariantId:'r',language:'de',ingredients:[{name:'Duck'},{name:'Prawns'}],steps:[],
 match:{diet:'vegetarian',dietCheckVersion:76,safe:false,eligibleWithSubstitutions:true,requiresSubstitutions:true,substitutions:[
 {ingredientIndex:0,original:'Duck <script>bad()</script>',replacement:{key:'tofu',name:'Firm tofu'}},
 {ingredientIndex:1,original:'Prawns',replacement:{key:'mushrooms',name:'Mushrooms'}}]}};
assert.notEqual(panel._recipeCard(recipe),'');
assert.equal(panel._recipeCard({...recipe,match:{safe:true}}),'','Old cached cards cannot bypass the new diet check');
assert.equal(panel._recipeCard({...recipe,match:{...recipe.match,eligibleWithSubstitutions:false}}),'','Incomplete suggestions must be excluded');
assert.equal(panel._recipeCard({...recipe,match:{...recipe.match,diet:'omnivore',safe:true}}),'','Changing diet must hide stale results');
const card=panel._v67Dom(panel._recipeCard(recipe));assert.ok(card.querySelector('[data-v76-diet-badge]'));
const body=panel._v67Dom(panel._v66Body(recipe,false,{sections:new Set(),device:'one'}));
assert.equal(body.querySelectorAll('[data-v76-substitution]').length,2);
assert.match(body.textContent,/Σφιχτό τόφου/);assert.match(body.textContent,/Μανιτάρια/);
assert.equal(body.querySelectorAll('script').length,0);
assert.equal(body.querySelector('[data-v66-action="send"]').disabled,true);
assert.equal(body.querySelector('[data-v66-action="shopping"]').disabled,true);
await panel._api('cook4me/v31/recipe_detail',{entry_id:'one',variant_id:'r'});
assert.equal(calls.at(-1).diet,'vegetarian','Opening detail preserves selected diet rather than household diet');
const regional={...recipe,language:'fr',languageVariants:[{language:'fr',servingVariants:[{displayVariantId:'fr-r'}]},{language:'en',servingVariants:[{displayVariantId:'en-r'}]}]};
await panel._v66PreferLanguages([regional]);
assert.equal(calls.at(-1).variant_id,'en-r');
assert.equal(calls.at(-1).diet,'vegetarian','Automatic language selection must also keep the diet');
assert.equal(regional.language,'fr','An unchecked preferred-language result cannot replace the checked source edition');
panel._v63Filters.diet='profile';panel._entries[0].profile.diet='vegetarian';
assert.equal(panel._v76Diet(),'vegetarian');
panel.disconnectedCallback();
console.log('v76 dietary cache, filter, substitution display, escaping and action checks passed');
