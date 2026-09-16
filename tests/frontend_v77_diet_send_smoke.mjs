import assert from 'node:assert/strict';
import {parseHTML} from 'linkedom';
const {window}=parseHTML('<!doctype html><html><body></body></html>');
for(const key of ['document','customElements','HTMLElement','Node','Event','CustomEvent','MutationObserver','Element','ShadowRoot'])if(window[key])globalThis[key]=window[key];
globalThis.window=window;globalThis.requestAnimationFrame=fn=>setTimeout(fn,0);globalThis.cancelAnimationFrame=clearTimeout;
globalThis.ResizeObserver=class{observe(){} disconnect(){}};globalThis.CSS={escape:String};
globalThis.localStorage={getItem:()=>null,setItem(){},removeItem(){}};
await import('../custom_components/cook4me/frontend/cook4me-panel-v77-bundle.js');
const panel=document.createElement('cook4me-recipe-hub-panel-v77'),calls=[],errors=[];
const recipe={id:'r',title:'Duck and prawns',displayVariantId:'original-r',sendVariantId:'original-r',language:'en',
 ingredients:[{name:'Duck'},{name:'Prawns'}],steps:[{instruction:'Cook the duck and prawns'}],
 match:{diet:'vegetarian',dietCheckVersion:76,safe:false,eligibleWithSubstitutions:true,requiresSubstitutions:true,substitutions:[
 {ingredientIndex:0,original:'Duck',replacement:{key:'tofu',name:'Firm tofu'}},
 {ingredientIndex:1,original:'Prawns',replacement:{key:'mushrooms',name:'Mushrooms'}}]}};
let detail=async()=>structuredClone(recipe);
panel._entryId='one';panel._hass={user:{id:'alice'},language:'en',connection:{sendMessagePromise:async msg=>{
 calls.push(msg);if(msg.type.endsWith('/recipe_detail'))return detail();
 if(msg.type.endsWith('/send_multi'))return {sentCount:1,queuedCount:0};return {};
}}};
panel._entries=[{entry_id:'one',profile:{diet:'omnivore'}},{entry_id:'two',profile:{diet:'vegetarian'}}];panel._tab='official';
panel._v63FilterKey=panel._prefKey();panel._v63Filters={diet:'vegetarian',languages:['en'],mealTypes:[]};
panel._processStart=()=>1;panel._processEnd=()=>{};panel._v59FailProcess=(_job,error)=>errors.push(error);
panel._loadOverview=async()=>{};panel._message=()=>{};panel._renderTab=()=>{};panel._renderRecipeDialog=()=>{};
const body=panel._v67Dom(panel._v66Body(recipe,false,{sections:new Set(),device:'one'}));
assert.equal(body.querySelector('[data-v66-action="send"]').disabled,false);
assert.equal(body.querySelector('[data-v66-action="shopping"]').disabled,true);
assert.match(body.textContent,/Send delivers the original recipe and cooking program/);
assert.equal(body.querySelectorAll('[data-v76-substitution]').length,2);
const original=structuredClone(recipe);
panel._v66BindRecipe(body,recipe,false);
body.querySelector('[data-v66-action="send"]').dispatchEvent(new Event('click'));
await new Promise(resolve=>setTimeout(resolve,30));
assert.equal(errors.length,0);
const sent=calls.find(row=>row.type.endsWith('/send_multi'));
assert.ok(sent,'Clicking Send must dispatch an adapted official recipe');
assert.equal(sent.type,'cook4me/v25/send_multi');
assert.equal(sent.recipe.sendDiet,'vegetarian');
assert.equal(sent.recipe.sendVariantId,'original-r');
assert.deepEqual(sent.recipe.ingredients,original.ingredients);
assert.deepEqual(sent.recipe.steps,original.steps);
assert.equal(sent.recipe.match.safe,false,'Do not relabel the original as diet-compatible');
assert.equal(calls.find(row=>row.type.endsWith('/recipe_detail')).diet,'vegetarian');

calls.length=0;detail=async()=>({...structuredClone(recipe),match:{...recipe.match,eligibleWithSubstitutions:false}});
await panel._v66Send(recipe,'one');
assert.equal(calls.some(row=>row.type.endsWith('/send_multi')),false,'Incomplete fresh substitutions cannot send');
assert.equal(errors.length,1);

calls.length=0;let release;detail=()=>new Promise(resolve=>{release=resolve;});
const pending=panel._v66Send(recipe,'one');
await new Promise(resolve=>setTimeout(resolve,10));
panel._v63Filters.diet='vegan';release(structuredClone(recipe));await pending;
assert.equal(calls.some(row=>row.type.endsWith('/send_multi')),false,'Changing diet during detail loading must cancel Send');

calls.length=0;panel._v63Filters.diet='profile';detail=async()=>structuredClone(recipe);
await panel._v66Send(recipe,'two');
const targetSend=calls.find(row=>row.type.endsWith('/send_multi'));
assert.equal(targetSend.entry_id,'two');assert.equal(targetSend.recipe.sendDiet,'profile');
assert.equal(calls.find(row=>row.type.endsWith('/recipe_detail')).entry_id,'two');
const custom=panel._v67Dom(panel._v66Body(recipe,true,{sections:new Set(),device:'two'}));
assert.equal(custom.querySelector('[data-v66-action="send"]').disabled,true);
panel.disconnectedCallback();
console.log('v77 Send click, original program, complete replacements, selected target and diet race checks passed');
