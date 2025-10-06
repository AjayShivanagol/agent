class ScrollBottomEl extends HTMLElement {
  connectedCallback() {
    // Defer to ensure content is rendered
    requestAnimationFrame(() => this.scrollNow());
    // Also scroll once more after a tick in case images load late
    setTimeout(() => this.scrollNow(), 50);
  }

  scrollNow() {
    let el = this.parentElement;
    // Walk up until we find a scrollable container
    while (el && !(el.scrollHeight > el.clientHeight)) {
      el = el.parentElement;
    }
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }
}

customElements.define('scroll-bottom-el', ScrollBottomEl);
