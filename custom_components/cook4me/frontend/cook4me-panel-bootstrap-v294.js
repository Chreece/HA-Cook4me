// This tiny custom panel registers immediately instead of awaiting the entire
// historical panel/mixin import chain on the HA navigation critical path.
// The real panel is mounted once its module graph has finished loading.
const PANEL_TAG = 'cook4me-recipe-hub-panel-v180-runtime-v294';
const LABEL = {
  en: 'Opening Cook4Me dashboard…',
  de: 'Cook4Me-Dashboard wird geöffnet…',
  el: 'Άνοιγμα πίνακα Cook4Me…',
};
const moduleReady = import('./cook4me-panel-v180.js?v=2026.11.4.1');

class Cook4MeQuickPanelV294 extends HTMLElement {
  constructor() {
    super();
    this._panelProperties = Object.create(null);
    const root = this.attachShadow({mode: 'open'});
    root.innerHTML = `
      <style>
        :host {display:block;min-height:calc(100dvh - 56px);background:var(--primary-background-color,#fafafa);color:var(--primary-text-color,#222)}
        .status {display:flex;align-items:center;justify-content:center;gap:14px;min-height:46vh;padding:24px;box-sizing:border-box;font:500 16px/1.5 var(--paper-font-body1_-_font-family,Roboto,sans-serif)}
        .spinner {width:24px;height:24px;flex:0 0 auto;border:3px solid var(--divider-color,#ddd);border-top-color:var(--primary-color,#03a9f4);border-radius:50%;animation:spin .8s linear infinite}
        @keyframes spin {to{transform:rotate(360deg)}}
        button {cursor:pointer;border:1px solid var(--divider-color,#ccc);padding:10px 16px;background:var(--card-background-color,#fff);color:inherit;border-radius:9px;font:inherit}
        @media (prefers-reduced-motion:reduce){.spinner{animation:none}}
      </style>
      <div class="status" role="status" aria-live="polite">
        <span class="spinner" aria-hidden="true"></span>
        <span id="message"></span>
      </div>`;
  }

  connectedCallback() {
    this._updateMessage();
    void this._mount();
  }

  _updateMessage() {
    const language = String(this._panelProperties.hass?.language ||
      this._panelProperties.hass?.config?.language || 'en').split(/[-_]/)[0];
    const message = this.shadowRoot.getElementById('message');
    if (message) message.textContent = LABEL[language] || LABEL.en;
  }

  async _mount() {
    if (this._inner || this._mounting) return;
    this._mounting = true;
    try {
      await moduleReady;
      if (!this.isConnected || this._inner) return;
      if (!customElements.get(PANEL_TAG)) throw new Error('Cook4Me panel module did not register');
      const inner = document.createElement(PANEL_TAG);
      this._inner = inner;
      this.shadowRoot.replaceChildren(inner);
      // Route/panel metadata precedes hass so initial render uses correct context.
      for (const name of ['panel', 'route', 'params', 'narrow', 'active', 'isActive', 'hass']) {
        if (Object.prototype.hasOwnProperty.call(this._panelProperties, name)) {
          inner[name] = this._panelProperties[name];
        }
      }
    } catch (error) {
      if (!this.isConnected) return;
      const message = this.shadowRoot.getElementById('message');
      if (message) message.textContent = 'Cook4Me could not load. Please reload the dashboard.';
      const status = this.shadowRoot.querySelector('.status');
      status?.querySelector('.spinner')?.remove();
      if (status && !status.querySelector('button')) {
        const retry = document.createElement('button');
        retry.type = 'button';
        retry.textContent = 'Reload';
        retry.onclick = () => globalThis.location.reload();
        status.append(retry);
      }
      console.error('Cook4Me panel module failed to load', error);
    } finally {
      this._mounting = false;
    }
  }
}
for (const property of ['hass', 'panel', 'route', 'params', 'narrow', 'active', 'isActive']) {
  Object.defineProperty(Cook4MeQuickPanelV294.prototype, property, {
    get() { return this._panelProperties[property]; },
    set(value) {
      this._panelProperties[property] = value;
      if (this._inner) this._inner[property] = value;
      else if (property === 'hass') this._updateMessage();
    },
  });
}
customElements.define('cook4me-quick-panel-v294', Cook4MeQuickPanelV294);
