// Theme-aware foundations. No remote fonts, image downloads, or application data.
export const APP_THEME = `
:host(.ui203){
 --ui203-page:var(--primary-background-color,#f4f6f7);
 --ui203-surface:var(--card-background-color,#fff);
 --ui203-ink:var(--primary-text-color,#192c30);
 --ui203-muted:var(--secondary-text-color,#53686d);
 --ui203-accent:var(--primary-color,#007f7b);
 --ui203-soft:color-mix(in srgb,var(--ui203-accent) 9%,var(--ui203-surface));
 --ui203-raised:color-mix(in srgb,var(--ui203-ink) 3%,var(--ui203-surface));
 --ui203-line:color-mix(in srgb,var(--ui203-ink) 13%,var(--ui203-surface));
 --ui203-shadow:0 3px 14px #00000009;
 --ui203-radius:18px;
 color:var(--ui203-ink);background:var(--ui203-page);
 font-family:var(--paper-font-body1_-_font-family,Roboto,system-ui,sans-serif);
 font-size:14px;line-height:1.5;letter-spacing:normal;
}
:host(.ui203) .wrap{max-width:1740px!important;margin:0 auto!important;padding:24px clamp(14px,2vw,32px) 48px!important;box-sizing:border-box;gap:20px!important}
:host(.ui203) .card:not(.recipe){background:var(--ui203-surface)!important;border:1px solid var(--ui203-line)!important;border-radius:var(--ui203-radius)!important;box-shadow:var(--ui203-shadow)!important}
:host(.ui203) .card::before,:host(.ui203) .card::after{pointer-events:none}
:host(.ui203) h1,:host(.ui203) h2,:host(.ui203) h3,:host(.ui203) h4{letter-spacing:-.015em;line-height:1.35;word-break:normal;overflow-wrap:break-word}
:host(.ui203) h1,:host(.ui203) h2{font-weight:650}
:host(.ui203) p.muted,:host(.ui203) .muted{color:var(--ui203-muted);line-height:1.55}
:host(.ui203) .wrap>.top.v100-top{border:1px solid var(--ui203-line)!important;border-radius:20px!important;padding:14px 20px!important;background:var(--ui203-surface)!important;box-shadow:none!important;gap:16px!important}
:host(.ui203) .v100-top .status{background:transparent!important}
:host(.ui203) .v100-top .status-title{font-weight:650!important;letter-spacing:-.02em}
:host(.ui203) .v100-global-actions{gap:8px!important}
:host(.ui203) .v100-top .v130-model{filter:none!important;width:108px!important;height:108px!important;flex:0 0 108px!important}
:host(.ui203) .v100-top .v130-device-summary{min-height:108px!important;gap:18px!important}
/* Navigation carries text as well as icons; no rainbow of competing borders. */
:host(.ui203) .v100-navigation{display:flex!important;align-items:flex-start;flex-wrap:wrap;gap:12px!important;padding:10px!important;margin:18px 0 0!important;background:var(--ui203-surface)!important;border:1px solid var(--ui203-line)!important;border-radius:16px 16px 0 0!important;box-sizing:border-box;min-width:0}
:host(.ui203) #tabs{display:flex!important;align-items:stretch;gap:4px!important;flex:1 1 600px;min-width:0;overflow-x:auto!important;padding:0!important;margin:0!important;scrollbar-width:thin;border:0!important;background:transparent!important}
:host(.ui203) #tabs .tab{display:flex!important;align-items:center!important;justify-content:center;gap:8px!important;flex:0 0 auto!important;max-width:none!important;width:auto!important;min-width:44px!important;min-height:46px;height:auto!important;padding:10px 13px!important;border:1px solid transparent!important;border-radius:11px!important;background:transparent!important;color:var(--ui203-muted)!important;box-shadow:none!important;font-weight:550;font-size:.9rem;line-height:1.3;white-space:nowrap!important}
:host(.ui203) #tabs .tab::before,:host(.ui203) #tabs .tab::after{content:none!important}
:host(.ui203) #tabs .tab.active,:host(.ui203) #tabs .tab[aria-pressed=true]{color:var(--ui203-ink)!important;background:var(--ui203-soft)!important;border-color:color-mix(in srgb,var(--ui203-accent) 32%,var(--ui203-line))!important;font-weight:650}
:host(.ui203) #tabs .tab.active ha-icon,:host(.ui203) #tabs .tab[aria-pressed=true] ha-icon{color:var(--ui203-accent)!important}
:host(.ui203) #tabs .ui203-nav-label{display:inline!important;max-width:none!important;clip:auto!important;position:static!important;opacity:1!important;width:auto!important;height:auto!important;overflow:visible!important}
:host(.ui203) #tabs .tab ha-icon,:host(.ui203) #tabs .tab svg{flex:0 0 22px;--mdc-icon-size:22px;width:22px!important;height:22px!important}
:host(.ui203) .v100-filter-slot{margin-inline-start:auto;flex:0 1 auto;min-width:0}
:host(.ui203) .rx-shared-filters{gap:6px!important;margin:0!important}
:host(.ui203) .rx-shared-filters button{border-radius:10px!important;min-height:44px;background:var(--ui203-raised)!important;border-color:var(--ui203-line)!important}
:host(.ui203) .rx-shared-filters button[aria-pressed=true]{background:var(--ui203-soft)!important;border-color:var(--ui203-accent)!important}
:host(.ui203) #content{min-width:0}
:host(.ui203) #content>[data-v100-section]{padding:22px 24px!important;margin-top:0!important;margin-bottom:24px!important;background:var(--ui203-surface)!important;border:1px solid var(--ui203-line)!important;border-top:0!important;border-radius:0 0 16px 16px!important;box-shadow:none!important}
:host(.ui203) [data-v100-section] h1,:host(.ui203) [data-v100-section] h2{font-size:clamp(1.25rem,1.6vw,1.7rem)!important;line-height:1.3!important;margin:0!important}
:host(.ui203) .ui203-view-subtitle{font-size:.92rem;color:var(--ui203-muted);margin:8px 0 0;max-width:76ch;line-height:1.5}
:host(.ui203) .detail-head{display:flex;flex-wrap:wrap;gap:12px!important;min-width:0;align-items:center}
:host(.ui203) .detail-head>div:first-child{flex:1 1 210px;min-width:0}
:host(.ui203) .rx-heading{gap:10px!important}
:host(.ui203) .btn:has(>ha-icon:not(.rx-leading-icon))>.rx-leading-icon{display:none!important}
:host(.ui203) .toolbar,:host(.ui203) .v93-menu-controls{gap:12px!important;align-items:center;flex-wrap:wrap}
:host(.ui203) .v93-menu-controls h2,:host(.ui203) [data-v100-section] .toolbar>h2{flex:1 1 240px}
:host(.ui203) .btn{border-radius:11px!important;min-height:42px;gap:8px!important;line-height:1.35;font-weight:600;letter-spacing:0;box-shadow:none!important;transition:background-color .14s ease,border-color .14s ease}
:host(.ui203) .btn.secondary{background:var(--ui203-raised)!important;color:var(--ui203-ink)!important;border:1px solid var(--ui203-line)!important}
:host(.ui203) button:disabled{cursor:not-allowed}
:host(.ui203) :is(button,input,select,textarea,summary,a):focus-visible{outline:2px solid var(--ui203-accent)!important;outline-offset:3px}
:host(.ui203) :is(input,select,textarea)[aria-invalid=true]{outline:2px solid var(--error-color,#c93636)!important;border-color:var(--error-color,#c93636)!important}
:host(.ui203) button ha-icon{flex-shrink:0}
:host(.ui203) .chip{border-radius:8px!important;padding:4px 9px;line-height:1.4;border:1px solid var(--ui203-line);background:var(--ui203-raised);font-weight:500}
/* Shared recipe cards: source title above photo, only a small action dock below. */
:host(.ui203) article.recipe.ui203-recipe{display:flex!important;flex-direction:column;gap:0!important;padding:0!important;margin:0!important;height:auto!important;min-height:0!important;max-height:none!important;border:1px solid var(--ui203-line)!important;border-radius:16px!important;background:var(--ui203-surface)!important;box-shadow:var(--ui203-shadow)!important;overflow:hidden!important}
:host(.ui203) article.ui203-recipe>.rx-v66-title{display:flex!important;gap:10px!important;align-items:flex-start!important;padding:16px!important;min-height:0!important;height:auto!important;max-height:none!important;overflow:visible!important;flex:0 0 auto}
:host(.ui203) .ui203-recipe-heading{min-width:0;flex:1}
:host(.ui203) article.ui203-recipe .rx-v66-title h3{font-size:1.04rem!important;font-weight:650!important;line-height:1.45!important;display:block!important;height:auto!important;max-height:none!important;padding:0!important;margin:0!important;overflow:visible!important;overflow-wrap:anywhere!important;-webkit-line-clamp:unset!important}
:host(.ui203) .ui203-recipe-language{display:inline-flex!important;color:var(--ui203-muted)!important;font-size:.76rem!important;font-weight:450!important;line-height:1.5!important;margin-top:6px;padding:2px 7px;background:var(--ui203-raised);border-radius:6px;border:1px solid var(--ui203-line);max-width:100%;overflow-wrap:anywhere}
:host(.ui203) article.ui203-recipe>.rx-v69-media{min-height:0!important;height:auto!important;flex:0 0 auto;background:var(--ui203-raised)!important;border-radius:0!important}
:host(.ui203) article.ui203-recipe [data-v66-photo]{display:block;width:100%;height:auto!important;min-height:0!important;max-height:none!important;border:0!important;border-radius:0!important;box-shadow:none!important;background:transparent!important;padding:0!important}
:host(.ui203) article.ui203-recipe [data-v66-photo] .media{aspect-ratio:16/9!important;height:auto!important;min-height:0!important;max-height:none!important;border-radius:0!important;margin:0!important;padding:0!important;overflow:hidden}
:host(.ui203) article.ui203-recipe .media img.cover{display:block;width:100%!important;height:100%!important;min-height:0!important;max-height:none!important;aspect-ratio:16/9;object-fit:cover!important;border-radius:0!important}
:host(.ui203) article.ui203-recipe .media-placeholder{min-height:140px!important;background:var(--ui203-soft)!important}
:host(.ui203) .ui203-action-dock{position:relative!important;inset:auto!important;display:flex!important;align-items:flex-start;flex-wrap:wrap;gap:7px!important;padding:10px 12px!important;margin:0!important;background:var(--ui203-surface)!important;color:var(--ui203-ink);border-top:1px solid var(--ui203-line);pointer-events:auto;box-sizing:border-box;overflow:visible!important;max-height:none!important}
:host(.ui203) .ui203-action-dock>.rx-v66-actions{display:contents!important}
:host(.ui203) .ui203-action-dock .rx-v66-icon{display:inline-flex!important;align-items:center;justify-content:center;flex:0 0 auto;width:40px!important;height:40px!important;min-width:40px!important;min-height:40px!important;padding:8px!important;border-radius:10px!important;background:var(--ui203-raised)!important;color:var(--ui203-ink)!important;border:1px solid var(--ui203-line)!important;opacity:1!important;pointer-events:auto}
:host(.ui203) .ui203-action-dock .rx-v66-icon:disabled{opacity:.4!important}
:host(.ui203) .ui203-action-dock>[data-v66-action=send]{color:var(--ui203-accent)!important;background:var(--ui203-soft)!important;border-color:color-mix(in srgb,var(--ui203-accent) 30%,var(--ui203-line))!important}
:host(.ui203) details.ui203-more{display:block;flex:1 1 190px;min-width:min(100%,190px);box-sizing:border-box;align-self:flex-start;margin:0!important;padding:0!important;border:1px solid transparent!important;background:transparent!important;border-radius:12px;overflow:hidden}
:host(.ui203) details.ui203-more>summary{list-style:none;display:flex;align-items:center;justify-content:center;gap:6px;min-height:40px;padding:0 10px!important;margin:0!important;font-size:.82rem;font-weight:550;color:var(--ui203-muted);background:var(--ui203-raised);border:1px solid var(--ui203-line);border-radius:10px;cursor:pointer;box-sizing:border-box}
:host(.ui203) details.ui203-more>summary::-webkit-details-marker{display:none}
:host(.ui203) details.ui203-more>summary::after{content:none!important}
:host(.ui203) details.ui203-more[open]{flex-basis:190px;padding:0!important;border:1px solid var(--ui203-line)!important;background:var(--ui203-raised)!important;box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--ui203-accent) 8%,transparent)}
:host(.ui203) details.ui203-more[open]>summary{justify-content:center;background:var(--ui203-soft);color:var(--ui203-ink);border-color:color-mix(in srgb,var(--ui203-accent) 35%,var(--ui203-line))}
:host(.ui203) .ui203-more-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,140px),1fr));gap:6px;padding:6px 0 0;min-width:0}
:host(.ui203) .ui203-more-grid .rx-v66-icon{width:100%!important;min-width:0!important;height:auto!important;min-height:42px!important;justify-content:flex-start!important;text-align:start;padding:9px!important}
:host(.ui203) .ui203-more-grid .ui203-action-label{display:inline!important;font-size:.79rem;font-weight:500;white-space:normal!important;overflow-wrap:anywhere;line-height:1.45}
:host(.ui203) .ui203-more-grid select{width:100%;grid-column:1/-1;min-height:42px!important;background:var(--ui203-raised)!important;color:var(--ui203-ink)!important;opacity:1!important}
:host(.ui203) .ui203-more-grid [data-v66-action=delete],:host(.ui203) .ui203-more-grid [data-v66-action=clear-slot]{color:var(--error-color,#c93636)!important}
:host(.ui203) article.ui203-recipe>.rx-v66-body{padding:8px 16px 16px!important;border-top:1px solid var(--ui203-line)}
:host(.ui203) #recipeGrid,:host(.ui203) #mineGrid,:host(.ui203) #todayGrid,:host(.ui203) .rx-category-results{gap:20px!important}
:host(.ui203) .grid:has(>article.ui203-recipe){grid-template-columns:repeat(auto-fill,minmax(min(100%,280px),1fr))!important}
:host(.ui203) .rx-category-result{min-width:0}
:host(.ui203) .rx-category-result>h3{font-size:.9rem;color:var(--ui203-muted);font-weight:600;margin:0 0 12px;display:flex;align-items:center;gap:8px}
/* Each day is a complete visual group, rather than seven narrow image strips. */
:host(.ui203) .rx-week-grid{display:grid!important;grid-template-columns:repeat(auto-fit,minmax(min(100%,310px),1fr))!important;align-items:start;gap:20px!important;padding:0!important;margin:0!important}
:host(.ui203) .rx-week-day{padding:16px!important;margin:0!important;min-width:0;background:var(--ui203-raised)!important;border:1px solid var(--ui203-line)!important;border-radius:20px!important;box-shadow:none!important;overflow:visible}
:host(.ui203) .rx-week-day[aria-current=date]{background:var(--ui203-soft)!important;border-color:color-mix(in srgb,var(--ui203-accent) 48%,var(--ui203-line))!important}
:host(.ui203) .rx-week-day>h3{min-height:0!important;margin:0!important;padding:0!important;font-size:1rem!important;line-height:1.5!important;font-weight:650}
:host(.ui203) .v110-day-selection{display:flex;align-items:center;gap:10px!important}
:host(.ui203) .v110-day-selection input,:host(.ui203) .v110-selection input{width:20px!important;height:20px!important;accent-color:var(--ui203-accent);flex-shrink:0}
:host(.ui203) .v110-selection{margin-top:3px;flex:0 0 20px}
:host(.ui203) .ui203-day-meta{display:flex;align-items:center;flex-wrap:wrap;gap:6px;margin:10px 0 18px;padding-bottom:14px;border-bottom:1px solid var(--ui203-line);font-size:.75rem;color:var(--ui203-muted)}
:host(.ui203) .ui203-day-meta span{padding:3px 8px;border-radius:7px;border:1px solid var(--ui203-line);background:var(--ui203-surface)}
:host(.ui203) .ui203-day-meta .ui203-today{color:var(--ui203-accent);font-weight:650}
:host(.ui203) .rx-week-slot{display:block!important;border:0!important;padding:0!important;margin:0 0 18px!important;min-width:0}
:host(.ui203) .rx-week-slot:last-child{margin-bottom:0!important}
:host(.ui203) .rx-week-slot>h4{font-size:.81rem!important;font-weight:650;line-height:1.4;color:var(--ui203-muted);padding:0!important;margin:0 0 9px!important;display:flex;align-items:center;gap:8px}
:host(.ui203) .rx-week-slot>h4::before{content:'';height:6px;width:6px;border-radius:50%;background:var(--ui203-accent);opacity:.65;flex-shrink:0}
:host(.ui203) .rx-week-day article.ui203-recipe .rx-v66-title{padding:13px!important}
:host(.ui203) .rx-week-day article.ui203-recipe .rx-v66-title h3{font-size:.96rem!important}
:host(.ui203) .rx-week-day article.ui203-recipe .media,:host(.ui203) .rx-week-day article.ui203-recipe .media img.cover{aspect-ratio:2/1!important}
:host(.ui203) .v202-recipe-gap{border-radius:14px!important;border:1px dashed var(--ui203-line)!important;background:var(--ui203-surface)!important;padding:20px!important;min-height:155px;box-shadow:none!important}
:host(.ui203) .v202-recipe-gap h3{font-size:.94rem}
:host(.ui203) .v202-recipe-gap p{font-size:.86rem}
:host(.ui203) [data-v202-gap-info]{border-radius:12px!important;background:var(--ui203-soft);color:var(--ui203-muted);font-size:.88rem}
/* Panels, kitchen, shopping, preferences and dialogs use the same visual rules. */
:host(.ui203) .ui233-diet-section>h2{margin:0 0 18px!important}
:host(.ui203) .ui233-diet-section>[data-v83-profiles]{display:grid;gap:14px;min-width:0}
:host(.ui203) .ui233-diet-section .v83-diet-card{margin:0!important;padding:16px!important;border-radius:14px!important;background:var(--ui203-raised)!important;box-shadow:none!important;min-width:0}
:host(.ui203) .ui233-diet-section .v83-diet-card>summary{min-height:44px;font-size:1rem;list-style:none;overflow-wrap:anywhere}
:host(.ui203) .ui233-diet-section .v83-diet-card>summary::-webkit-details-marker{display:none}
:host(.ui203) .ui233-diet-section .v83-diet-card>summary>span{min-width:0}
:host(.ui203) .ui233-diet-section .v83-profile-actions{margin:0}
:host(.ui203) .ui233-diet-section [data-v83-save]{justify-self:start;max-width:100%;white-space:normal}
:host(.ui203) .ui233-diet-section [data-v83-status]:empty{display:none}
:host(.ui203) .ui233-other-preferences textarea{display:block;min-height:100px;resize:vertical}
@media(max-width:680px){:host(.ui203) .ui233-diet-section .v83-diet-card{padding:12px!important}}
:host(.ui203) [data-v179-fold],:host(.ui203) [data-v137-week-panel],:host(.ui203) .v145-week-pattern{margin-block:16px!important;padding:20px!important;background:var(--ui203-surface)!important}
:host(.ui203) .v179-fold-head,:host(.ui203) .v137-week-head{padding:0!important;min-height:32px;gap:12px!important}
:host(.ui203) .v179-fold-title{font-size:1rem!important;font-weight:600}
:host(.ui203) .v179-open>.v179-fold-body{padding-top:20px}
:host(.ui203) .v78-nav{gap:6px!important;padding:5px!important;background:var(--ui203-raised)!important;border:1px solid var(--ui203-line);border-radius:13px!important;max-width:100%;box-sizing:border-box}
:host(.ui203) .v78-nav button{padding:11px 15px!important;border-radius:9px!important;min-height:42px;font-size:.91rem}
:host(.ui203) .v78-nav button[aria-pressed=true]{background:var(--ui203-surface)!important;color:var(--ui203-ink)!important;box-shadow:var(--ui203-shadow)!important}
:host(.ui203) .v78-heading{padding:0!important;gap:16px!important}
:host(.ui203) .v78-heading h1{font-size:1.55rem!important}
:host(.ui203) .v78-eyebrow{font-size:.66rem!important;letter-spacing:.12em!important;color:var(--ui203-muted);margin-bottom:4px}
:host(.ui203) .v78-launch{align-items:flex-start!important;padding:22px!important;gap:18px!important;border-radius:18px!important;background:var(--ui203-soft)!important;border:1px solid var(--ui203-line)!important;flex-wrap:wrap}
:host(.ui203) .v78-launch h2{font-size:1.12rem!important}
:host(.ui203) .v78-launch-icon{align-self:flex-start!important;border-radius:14px!important;padding:14px!important;background:var(--ui203-surface)!important}
:host(.ui203) .v78-launch p{margin:5px 0 16px!important;line-height:1.5}
:host(.ui203) .v78-launch .v78-count{font-size:1.6rem!important;color:var(--ui203-accent)}
:host(.ui203) .v142-stock-summary{width:100%;flex-basis:100%}
:host(.ui203) .v142-summary-grid{gap:12px!important}
:host(.ui203) :is(.v78-place,.v112-package,.v142-expiry-row,.rx-shopping-item,.shopping-item){border-color:var(--ui203-line)!important;border-radius:12px!important;padding:14px!important;background:var(--ui203-raised)!important;gap:12px!important}
:host(.ui203) .v78-places{gap:12px!important}
:host(.ui203) .v78-place-form{padding-top:20px!important;margin-top:20px!important;border-top:1px solid var(--ui203-line)}
:host(.ui203) :is(.field,.formgrid>div,.v78-fields>label){min-width:0}
:host(.ui203) :is(input,select,textarea):not([type=checkbox]):not([type=radio]):not([type=range]):not([type=file]){border:1px solid var(--ui203-line);border-radius:10px!important;background:var(--ui203-raised);color:var(--ui203-ink);min-height:42px;line-height:1.45;box-sizing:border-box;padding:10px 12px}
:host(.ui203) textarea{resize:vertical}
:host(.ui203) :is(input[type=checkbox],input[type=radio]){accent-color:var(--ui203-accent)}
:host(.ui203) .field>label,:host(.ui203) label.field{font-weight:550;font-size:.9rem;line-height:1.5}
:host(.ui203) .field small,:host(.ui203) .field .muted{font-weight:400}
:host(.ui203) .rx-overlay{background:#0008!important;backdrop-filter:blur(3px)}
:host(.ui203) .rx-dialog:not(.rx-v66-fullscreen){border:1px solid var(--ui203-line)!important;border-radius:20px!important;background:var(--ui203-surface)!important;box-shadow:0 18px 60px #0004;padding:22px!important}
:host(.ui203) .rx-dialog>header{gap:16px!important;align-items:center;border-bottom:1px solid var(--ui203-line);padding-bottom:14px}
:host(.ui203) .rx-dialog h2{font-size:1.3rem}
:host(.ui203) [data-filter-dialog] .rx-dialog>label:has(input[type=checkbox]),:host(.ui203) [data-filter-dialog] label:has(>input[data-list]){padding:11px 12px!important;border-radius:10px;background:var(--ui203-raised);border:1px solid transparent;margin:6px 0!important;gap:10px!important}
:host(.ui203) [data-filter-dialog] label:has(input[data-list]:checked){background:var(--ui203-soft)!important;border-color:color-mix(in srgb,var(--ui203-accent) 30%,var(--ui203-line))!important}
:host(.ui203) .rx-dialog details:not(.ui203-more)>summary{padding:12px 0!important;line-height:1.5;font-weight:600;cursor:pointer}
/* Dialog actions stay on the card edge; content never passes behind them. */
:host(.ui203) .rx-overlay>.rx-dialog.ui234-dialog,:host(.ui203) dialog.ui234-dialog{display:flex!important;flex-direction:column;box-sizing:border-box;min-width:0;min-height:0;max-width:calc(100vw - 24px)!important;max-height:calc(100dvh - 24px)!important;padding:0!important;overflow:hidden!important;transition:none!important}
:host(.ui203) dialog.ui234-dialog:not([open]){display:none!important}
:host(.ui203) .ui234-dialog>.ui234-dialog-header{display:flex;flex:0 0 auto;flex-wrap:nowrap;align-items:center;justify-content:space-between;gap:12px;min-width:0;margin:0!important;padding:16px 22px!important;border-bottom:1px solid var(--ui203-line);background:var(--ui203-surface);overflow-wrap:anywhere}
:host(.ui203) .ui234-dialog-header :is(h2,h3){margin:0!important}
:host(.ui203) .ui234-dialog-header>:first-child{flex:1 1 auto;min-width:0}
:host(.ui203) .ui234-dialog-header>button{flex:0 0 auto}
:host(.ui203) .ui234-dialog>.ui234-dialog-form{display:flex;flex-direction:column;flex:1 1 auto;min-height:0;min-width:0;margin:0;overflow:hidden}
:host(.ui203) .ui234-dialog-body{flex:1 1 auto;min-height:0;min-width:0;box-sizing:border-box;padding:18px 22px;overflow:auto;overscroll-behavior:contain;overflow-wrap:anywhere;scroll-padding-block:18px}
:host(.ui203) .ui234-dialog :is(.ui234-dialog-footer){position:static!important;inset:auto!important;flex:0 0 auto;display:flex;flex-wrap:wrap;align-items:center;justify-content:flex-end;gap:12px;box-sizing:border-box;margin:0!important;padding:12px 22px max(12px,env(safe-area-inset-bottom))!important;border:0;border-top:1px solid var(--ui203-line);border-radius:0!important;background:var(--ui203-surface)}
:host(.ui203) .ui234-dialog-footer .btn{max-width:100%;min-width:0;white-space:normal;overflow-wrap:anywhere}
:host(.ui203) .ui234-dialog-body :is(input,select,textarea){min-width:0;max-width:100%}
:host(.ui203) [data-device-settings] .ui234-dialog .v72-fields{grid-template-columns:repeat(2,minmax(0,1fr))}
:host(.ui203) [data-filter-dialog] .ui234-dialog-body>label:has(input[type=checkbox]){padding:11px 12px!important;border-radius:10px;background:var(--ui203-raised);border:1px solid transparent;margin:6px 0!important;gap:10px!important}
:host(.ui203) .ui234-dialog .v131-history-usage{grid-template-columns:minmax(0,1.5fr) minmax(0,1.35fr) minmax(70px,.55fr) minmax(65px,.5fr) auto}
:host(.ui203) .ui234-dialog .v131-history-usage :is(input,select){width:100%}
:host(.ui203) .ui234-dialog .v154-weigh-body{padding:0;min-width:0}
@media(max-width:760px){:host(.ui203) .ui234-dialog .v131-history-usage{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:560px){
 :host(.ui203) .ui234-dialog>.ui234-dialog-header{padding:12px 14px!important}
 :host(.ui203) .ui234-dialog-body{padding:14px;scroll-padding-block:14px}
 :host(.ui203) .ui234-dialog .ui234-dialog-footer{padding:12px 14px max(12px,env(safe-area-inset-bottom))!important;gap:8px;flex-direction:row}
 :host(.ui203) .ui234-dialog-footer .btn{flex:1 1 120px}
 :host(.ui203) [data-device-settings] .ui234-dialog .v72-fields{grid-template-columns:minmax(0,1fr)}
 :host(.ui203) .ui234-dialog .v131-history-usage{grid-template-columns:minmax(0,1fr)}
}
:host(.ui203) .rx-v66-fullscreen .rx-v67-photo-side{background:var(--ui203-surface);border:1px solid var(--ui203-line);border-radius:16px;overflow:auto}
:host(.ui203) .rx-v66-fullscreen .rx-v69-media{border-radius:0!important}
:host(.ui203) .rx-v66-fullscreen .rx-v66-body{padding:0 18px 24px!important}
:host(.ui203) .rx-v66-fullscreen header{border-bottom:1px solid var(--ui203-line);padding:16px 24px!important;background:var(--ui203-surface)}
:host(.ui203) .rx-v66-fullscreen #recipeDetail{padding:24px!important;gap:24px!important}
:host(.ui203) .rx-v66-steps .step{padding:16px!important;margin-block:10px!important;border:1px solid var(--ui203-line);border-radius:12px;background:var(--ui203-raised);line-height:1.7!important}
:host(.ui203) .rx-v66-ingredients li{border-color:var(--ui203-line)!important}
:host(.ui203) .rx-v67-nutrient{background:var(--ui203-raised)!important;border-color:var(--ui203-line)!important;border-radius:11px!important}
/* Manual entry is a form on a calm surface, not a form floating on a camera. */
:host(.ui203) dialog.v78-capture{background:var(--ui203-page)!important;color:var(--ui203-ink)}
:host(.ui203) dialog.v78-capture>header{background:var(--ui203-surface)!important;border-bottom:1px solid var(--ui203-line);gap:16px;padding:16px 24px!important}
:host(.ui203) dialog.v78-capture>header h2{font-size:1.22rem!important;margin:0}
:host(.ui203) .ui203-form .v78-capture-body{padding:20px 20px calc(var(--ui203-footer-height,110px) + 32px)!important;max-width:1060px!important;width:100%!important;margin:0 auto;box-sizing:border-box}
:host(.ui203) .ui203-form [data-v111-frame]{height:auto!important;min-height:0!important;max-height:none!important;aspect-ratio:auto!important;background:transparent!important;border:0!important;overflow:visible!important;--secondary-text-color:var(--ui203-muted)}
:host(.ui203) .ui203-form [data-v112-editor],:host(.ui203) .ui203-form [data-v112-editor] :is(h2,h3,label){color:var(--ui203-ink)!important}
:host(.ui203) .ui203-form [data-v112-editor]{position:relative!important;inset:auto!important;padding:24px!important;margin:12px 0 0;border:1px solid var(--ui203-line)!important;border-radius:18px!important;background:var(--ui203-surface)!important;backdrop-filter:none!important;box-shadow:var(--ui203-shadow);max-height:none!important;overflow:visible!important}
:host(.ui203) .ui203-form .v111-modes{position:relative!important;inset:auto!important;margin:0!important;padding:6px!important;background:var(--ui203-surface)!important;border:1px solid var(--ui203-line);border-radius:13px!important;gap:6px!important;flex-wrap:wrap}
:host(.ui203) .ui203-form [data-v111-frame]>video,:host(.ui203) .ui203-form [data-v111-guide-wrap],:host(.ui203) .ui203-form .v111-bottom,:host(.ui203) .ui203-form .v111-result{display:none!important}
:host(.ui203) .ui203-form [data-v112-editor] main{padding:0!important}
:host(.ui203) .ui203-form [data-v112-editor] :is(input,select,textarea):not([type=checkbox]):not([type=radio]):not([type=range]):not([type=file]){background:var(--ui203-raised)!important;color:var(--ui203-ink)!important;border-color:var(--ui203-line)!important}
:host(.ui203) .ui203-form .v78-review-section h3 span{color:var(--ui203-muted)!important}
:host(.ui203) .ui203-form .v111-icon:not([aria-pressed=true]){background:var(--ui203-raised)!important;color:var(--ui203-ink)!important;border-color:var(--ui203-line)!important}

:host(.ui203) .ui203-form [data-v78-form] fieldset{padding:0!important;border:0!important;min-width:0}
:host(.ui203) .ui203-form .ui203-number-field:has([data-v116-weight]){display:grid!important;grid-template-columns:minmax(0,1fr) auto;gap:8px!important;align-items:center}
:host(.ui203) .ui203-number-field [data-draft=quantity]{grid-column:1;grid-row:2}
:host(.ui203) .ui203-number-field [data-v116-weight]{grid-column:2;grid-row:2;align-self:stretch}
:host(.ui203) .ui203-form [data-v78-form] details{margin-top:18px;border-top:1px solid var(--ui203-line);padding-top:8px}
:host(.ui203) .ui203-form [data-v78-form] details>summary{font-size:.96rem;padding:12px 0!important;font-weight:600}
:host(.ui203) .v196-actions{background:var(--ui203-surface)!important;border-color:var(--ui203-line)!important;padding:14px max(20px,env(safe-area-inset-right)) calc(14px + env(safe-area-inset-bottom))!important;gap:10px!important;flex-direction:row!important;justify-content:flex-end!important}
:host(.ui203) .v196-actions button{width:auto!important;min-width:96px!important;flex:0 0 auto!important;min-height:44px!important}
:host(.ui203) .v196-actions [data-v196-status]{font-weight:450;max-width:78ch;color:var(--ui203-muted)}
:host(.ui203) .v111-icon{border-radius:10px!important}
:host(.ui203) .r195-tools{max-width:1060px;box-sizing:border-box;margin:16px auto 0;border:1px solid var(--ui203-line)!important;border-radius:16px;padding:20px!important;gap:14px!important;background:var(--ui203-surface)!important}
:host(.ui203) .r195-list button{padding:10px 12px!important;border-radius:10px!important}
:host(.ui203) .r195-list [aria-current=true]{background:var(--ui203-soft)!important;border-color:var(--ui203-accent)!important}
:host(.ui203) .v78-discard{padding:16px!important;border:1px solid var(--ui203-line);background:var(--ui203-soft)!important;gap:12px;flex-wrap:wrap}
:host(.ui203) .rx-v59-op{border:1px solid var(--ui203-line)!important;border-radius:16px!important;background:var(--ui203-surface)!important;box-shadow:0 8px 36px #0003!important}
:host(.ui203) .rx-v59-op-title{font-size:.93rem!important;line-height:1.4;font-weight:650}
:host(.ui203) .rx-v59-op-detail,:host(.ui203) [data-v143-eta]{font-size:.83rem;line-height:1.5}
@media(hover:hover){
 :host(.ui203) #tabs .tab:hover,:host(.ui203) .btn.secondary:not(:disabled):hover,:host(.ui203) .ui203-more>summary:hover{background:var(--ui203-soft)!important;border-color:color-mix(in srgb,var(--ui203-accent) 32%,var(--ui203-line))!important}
 :host(.ui203) article.ui203-recipe:hover{border-color:color-mix(in srgb,var(--ui203-accent) 35%,var(--ui203-line))!important}
}
@media(min-width:1500px){:host(.ui203) .rx-week-grid{grid-template-columns:repeat(4,minmax(0,1fr))!important}}
@media(max-width:760px){
 :host(.ui203) .wrap{padding:12px 12px 28px!important}
 :host(.ui203) .wrap>.top.v100-top{padding:12px!important;gap:10px!important}
 :host(.ui203) .v100-navigation{padding:7px!important;gap:8px!important;margin-top:14px!important}
 :host(.ui203) #tabs{flex-basis:100%}
 :host(.ui203) #tabs .tab{flex-direction:column!important;gap:4px!important;font-size:.74rem;padding:9px 11px!important}
 :host(.ui203) .v100-filter-slot{flex:1;max-width:100%}
 :host(.ui203) #content>[data-v100-section]{padding:18px 16px!important;margin-bottom:18px!important}
 :host(.ui203) .rx-week-grid{grid-template-columns:repeat(auto-fit,minmax(min(100%,285px),1fr))!important;gap:16px!important}
 :host(.ui203) .rx-week-day{padding:14px!important}
 :host(.ui203) [data-v179-fold],:host(.ui203) [data-v137-week-panel],:host(.ui203) .v145-week-pattern{padding:16px!important}
 :host(.ui203) .v78-nav button{font-size:.81rem;padding:10px!important;flex:0 0 auto}
 :host(.ui203) .v78-launch{padding:18px!important;gap:12px!important}
 :host(.ui203) .v78-fields{gap:14px!important}
 :host(.ui203) .rx-dialog:not(.rx-v66-fullscreen){padding:18px!important;max-width:calc(100vw - 20px)!important}
 :host(.ui203) .rx-v66-fullscreen #recipeDetail{padding:14px!important;gap:14px!important}
 :host(.ui203) .rx-v66-fullscreen header{padding:12px 14px!important}
 :host(.ui203) .rx-v66-fullscreen .rx-v66-body{padding:0 4px 18px!important}
 :host(.ui203) .ui203-form .v78-capture-body{padding:12px 12px calc(var(--ui203-footer-height,130px) + 24px)!important}
 :host(.ui203) .ui203-form [data-v112-editor],:host(.ui203) .ui203-form [data-v112-editor] :is(h2,h3,label){color:var(--ui203-ink)!important}
:host(.ui203) .ui203-form [data-v112-editor]{padding:16px!important;border-radius:14px!important}
 :host(.ui203) dialog.v78-capture>header{padding:12px 16px!important}
 :host(.ui203) .r195-tools{margin:12px;padding:16px!important}
 :host(.ui203) .v196-actions [data-v196-status]{flex-basis:100%;max-width:none}
}
@media(max-width:420px){
 :host(.ui203) .rx-week-grid{grid-template-columns:minmax(0,1fr)!important}
 :host(.ui203) .v78-fields,:host(.ui203) .v78-place-form .v78-fields{grid-template-columns:minmax(0,1fr)!important}
 :host(.ui203) .ui203-action-dock{gap:6px!important;padding:10px!important}
 :host(.ui203) .ui203-action-dock .rx-v66-icon{width:40px!important;min-width:40px!important}
}
@media(prefers-reduced-motion:reduce){:host(.ui203) .btn,:host(.ui203) article.ui203-recipe,:host(.ui203) :is(input,select,textarea){transition:none!important}}
@media(forced-colors:active){:host(.ui203) .ui203-day-meta span,:host(.ui203) .rx-week-day,:host(.ui203) article.ui203-recipe{border-color:CanvasText!important}}
`;
