// Announcement Hub is an exclusive delivery mode; the cooking-event switches remain active.
const LABELS = {
 en: {
  hub: 'Announcement Hub', unavailable: 'Announcement Hub is not available. Install and configure it first.',
  auto: 'Automatic routing', autoHint: 'Announcement Hub chooses recipients using its occupancy and fallback rules.',
  rooms: 'Rooms', people: 'People', choose: 'Choose rooms and/or people to receive the announcement.',
  noRooms: 'No Home Assistant rooms available.', noPeople: 'No accessible people found.',
 },
 de: {
  hub: 'Announcement Hub', unavailable: 'Announcement Hub ist nicht verfügbar. Bitte zuerst installieren und einrichten.',
  auto: 'Automatische Weiterleitung', autoHint: 'Announcement Hub wählt Empfänger anhand der Belegung und Fallback-Regeln.',
  rooms: 'Räume', people: 'Personen', choose: 'Räume und/oder Personen für die Ansage auswählen.',
  noRooms: 'Keine Home-Assistant-Räume verfügbar.', noPeople: 'Keine zugänglichen Personen gefunden.',
 },
 el: {
  hub: 'Announcement Hub', unavailable: 'Το Announcement Hub δεν είναι διαθέσιμο. Εγκαταστήστε και ρυθμίστε το πρώτα.',
  auto: 'Αυτόματη δρομολόγηση', autoHint: 'Το Announcement Hub επιλέγει παραλήπτες με βάση την παρουσία και τους κανόνες εφεδρείας.',
  rooms: 'Δωμάτια', people: 'Άτομα', choose: 'Επιλέξτε δωμάτια ή/και άτομα που θα λάβουν την ανακοίνωση.',
  noRooms: 'Δεν υπάρχουν διαθέσιμα δωμάτια.', noPeople: 'Δεν βρέθηκαν προσβάσιμα άτομα.',
 },
};

export const AnnouncementHubMixin = Base => class extends Base {
 _v294Labels() {
  const language = String(this._langCode?.() || 'en').split(/[-_]/)[0];
  return LABELS[language] || LABELS.en;
 }

 _v72RenderSettings() {
  super._v72RenderSettings();
  const overlay = this._v72Dialog, draft = this._v72Draft, choices = this._v72Data?.choices;
  if (!overlay || !draft || !choices) return;
  const labels = this._v294Labels(), escape = value => this._escape(String(value ?? ''));
  const available = choices.announcementHubAvailable === true;
  const hubEnabled = draft.announcement_hub === true;
  const automatic = draft.hub_auto_routing !== false;
  const switches = overlay.querySelector('.v72-switches');
  if (!switches) return;

  const toggle = document.createElement('label');
  toggle.className = 'v294-hub-toggle';
  toggle.innerHTML = `<input type="checkbox" data-v294-hub ${hubEnabled ? 'checked' : ''} ${!available && !hubEnabled ? 'disabled' : ''}><strong>${escape(labels.hub)}</strong>`;
  const enableRow = switches.querySelector('[data-setting="enabled"]')?.closest('label');
  if (enableRow) enableRow.after(toggle); else switches.prepend(toggle);

  const unique = rows => [...new Map(rows.map(row => [row.id, row])).values()];
  const areaIds = Array.isArray(draft.hub_areas) ? draft.hub_areas : [];
  const personIds = Array.isArray(draft.hub_persons) ? draft.hub_persons : [];
  const areas = unique([...(choices.hubAreas || []), ...areaIds.filter(id => !(choices.hubAreas || []).some(item => item.id === id)).map(id => ({id, name: id}))]);
  const people = unique([...(choices.hubPersons || []), ...personIds.filter(id => !(choices.hubPersons || []).some(item => item.id === id)).map(id => ({id, name: id}))]);
  const items = (rows, selected, attribute, empty) => rows.length
   ? rows.map(row => `<label><input type="checkbox" data-v294-${attribute}="${escape(row.id)}" ${selected.includes(row.id) ? 'checked' : ''}><span>${escape(row.name)}</span></label>`).join('')
   : `<p class="muted">${escape(empty)}</p>`;

  const section = document.createElement('section');
  section.className = 'v294-hub-options';
  section.hidden = !hubEnabled;
  section.innerHTML = `
   ${!available ? `<p class="muted" role="alert">${escape(labels.unavailable)}</p>` : ''}
   <label class="v294-hub-auto"><input type="checkbox" data-v294-hub-auto ${automatic ? 'checked' : ''}>
    <strong>${escape(labels.auto)}</strong></label>
   <p class="muted">${escape(labels.autoHint)}</p>
   <div class="v294-hub-manual" ${automatic ? 'hidden' : ''}>
    <p class="muted">${escape(labels.choose)}</p>
    <div class="v294-hub-targets">
     <details><summary>${escape(labels.rooms)} (<span data-v294-area-count>${areaIds.length}</span>)</summary>
      <div>${items(areas, areaIds, 'area', labels.noRooms)}</div></details>
     <details><summary>${escape(labels.people)} (<span data-v294-person-count>${personIds.length}</span>)</summary>
      <div>${items(people, personIds, 'person', labels.noPeople)}</div></details>
    </div>
   </div>`;
  switches.after(section);

  // Disable all legacy output controls in Hub mode, but not the recipe/step/state
  // event selectors. Preserve their values in case the user switches back to TTS.
  const form = overlay.querySelector('form');
  const speakers = form?.querySelector('.v72-players')?.closest('.field');
  for (const node of [speakers, form?.querySelector('.v72-fields'),
                      ...(form?.querySelectorAll(':scope > p.muted') || [])]) {
   if (node) node.classList.toggle('v294-native-hidden', hubEnabled);
  }

  toggle.querySelector('input').onchange = event => {
   draft.announcement_hub = event.target.checked;
   this._v72RenderSettings();
   this._v72Dialog?.querySelector('[data-v294-hub]')?.focus();
  };
  section.querySelector('[data-v294-hub-auto]').onchange = event => {
   draft.hub_auto_routing = event.target.checked;
   this._v72RenderSettings();
   this._v72Dialog?.querySelector('[data-v294-hub-auto]')?.focus();
  };
  for (const [attribute, key, count] of [
   ['area', 'hub_areas', '[data-v294-area-count]'],
   ['person', 'hub_persons', '[data-v294-person-count]'],
  ]) {
   section.querySelectorAll(`[data-v294-${attribute}]`).forEach(input => {
    input.onchange = () => {
     draft[key] = [...section.querySelectorAll(`[data-v294-${attribute}]:checked`)]
      .map(element => element.getAttribute(`data-v294-${attribute}`));
     section.querySelector(count).textContent = String(draft[key].length);
    };
   });
  }
  if (!this.shadowRoot.querySelector('#v294HubStyles')) {
   const style = document.createElement('style');
   style.id = 'v294HubStyles';
   style.textContent = `
    [data-device-settings] .v294-hub-toggle{font-weight:600}
    [data-device-settings] .v294-hub-options{margin:10px 0 14px;padding:12px;border-radius:12px;background:var(--secondary-background-color,var(--card-background-color));}
    [data-device-settings] .v294-hub-options[hidden],[data-device-settings] .v294-hub-manual[hidden],[data-device-settings] .v294-native-hidden{display:none!important}
    [data-device-settings] .v294-hub-auto{display:flex;gap:9px;align-items:center}
    [data-device-settings] .v294-hub-targets{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;min-width:0}
    [data-device-settings] .v294-hub-targets details{min-width:0;border:1px solid var(--divider-color);border-radius:9px;padding:8px}
    [data-device-settings] .v294-hub-targets summary{cursor:pointer;font-weight:600}
    [data-device-settings] .v294-hub-targets details>div{display:grid;gap:6px;max-height:215px;overflow-y:auto;padding-top:8px}
    [data-device-settings] .v294-hub-targets label{display:flex;gap:8px;align-items:center;overflow-wrap:anywhere}
    [data-device-settings] .v294-hub-targets label span{min-width:0}
    [data-device-settings] .v294-hub-options input{margin:0}
   `;
   this.shadowRoot.append(style);
  }
 }
};
