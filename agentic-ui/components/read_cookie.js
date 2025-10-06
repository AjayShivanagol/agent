class CookieReader extends HTMLElement {
  static get observedAttributes() { return []; }
  connectedCallback() {
    // Read cookie name from property set by Mesop web component wrapper
    const cookieName = this.properties?.cookie_name || 'userinfo';
    const value = this.#getCookie(cookieName);
    if (value) {
      this.dispatchEvent(new CustomEvent('userInfo', {
        detail: { value },
        bubbles: true,
        composed: true,
      }));
    }
  }

  // Mesop injects properties via element.properties
  set properties(p) { this._props = p; }
  get properties() { return this._props || {}; }

  #getCookie(name) {
    const nameEQ = name + '=';
    const ca = document.cookie.split(';');
    for (let i = 0; i < ca.length; i++) {
      let c = ca[i];
      while (c.charAt(0) === ' ') c = c.substring(1, c.length);
      if (c.indexOf(nameEQ) === 0) return decodeURIComponent(c.substring(nameEQ.length, c.length));
    }
    return '';
  }
}

customElements.define('cookie-reader', CookieReader);
