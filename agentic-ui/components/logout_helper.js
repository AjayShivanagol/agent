class LogoutHelper extends HTMLElement {
  static get observedAttributes() { return []; }
  connectedCallback() {
    const to = this.properties?.redirect_to || '/logout';
    try { this.#clearAllCookies(); } catch (e) { /* ignore */ }
    try { window.location.href = to; } catch (e) { /* ignore */ }
  }

  set properties(p) { this._props = p; }
  get properties() { return this._props || {}; }

  #clearAllCookies() {
    const cookies = document.cookie ? document.cookie.split(';') : [];
    const opts = [
      { path: '/' },
      // Try current domain and parent domain variants
      { path: '/', domain: window.location.hostname },
    ];
    for (const raw of cookies) {
      const eq = raw.indexOf('=');
      const name = (eq > -1 ? raw.substring(0, eq) : raw).trim();
      for (const o of opts) {
        let cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Lax;`;
        if (o.path) cookie += ` path=${o.path};`;
        if (o.domain) cookie += ` domain=${o.domain};`;
        document.cookie = cookie;
      }
    }
  }
}

customElements.define('logout-helper', LogoutHelper);
