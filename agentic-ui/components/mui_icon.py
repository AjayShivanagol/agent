import mesop as me
import re
from urllib.parse import quote

# Minimal inline SVG paths for required icons. Shapes are simplified to avoid CDN/fonts.
# All icons drawn at viewBox 0 0 24 24 and honor provided color via fill.

ICON_SVGS = {
    'menu': '<path d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zM3 7v2h18V7H3z"/>',
    'expand_more': '<path d="M7.41 8.59 12 13.17l4.59-4.58L18 10l-6 6-6-6z"/>',
    'chevron_right': '<path d="M10 6l6 6-6 6-1.41-1.41L13.17 12 8.59 7.41z"/>',
    'home': '<path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"/>',
    'chat_bubble': (
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-chat-left-text" viewBox="0 0 16 16">'
        '<path d="M14 1a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H4.414A2 2 0 0 0 3 11.586l-2 2V2a1 1 0 0 1 1-1zM2 0a2 2 0 0 0-2 2v12.793a.5.5 0 0 0 .854.353l2.853-2.853A1 1 0 0 1 4.414 12H14a2 2 0 0 0 2-2V2a2 2 0 0 0-2-2z"/>'
        '<path d="M3 3.5a.5.5 0 0 1 .5-.5h9a.5.5 0 0 1 0 1h-9a.5.5 0 0 1-.5-.5M3 6a.5.5 0 0 1 .5-.5h9a.5.5 0 0 1 0 1h-9A.5.5 0 0 1 3 6m0 2.5a.5.5 0 0 1 .5-.5h5a.5.5 0 0 1 0 1h-5a.5.5 0 0 1-.5-.5"/>'
        '</svg>'
    ),
    'add': '<path d="M19 11H13V5h-2v6H5v2h6v6h2v-6h6z"/>',
    'forum': '<path d="M22 2H2v14h4v4l6-4h10z"/>',
    'admin_panel_settings': (
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-shield-lock" viewBox="0 0 16 16">'
        '<path d="M5.338 1.59a61 61 0 0 0-2.837.856.48.48 0 0 0-.328.39c-.554 4.157.726 7.19 2.253 9.188a10.7 10.7 0 0 0 2.287 2.233c.346.244.652.42.893.533q.18.085.293.118a1 1 0 0 0 .101.025 1 1 0 0 0 .1-.025q.114-.034.294-.118c.24-.113.547-.29.893-.533a10.7 10.7 0 0 0 2.287-2.233c1.527-1.997 2.807-5.031 2.253-9.188a.48.48 0 0 0-.328-.39c-.651-.213-1.75-.56-2.837-.855C9.552 1.29 8.531 1.067 8 1.067c-.53 0-1.552.223-2.662.524zM5.072.56C6.157.265 7.31 0 8 0s1.843.265 2.928.56c1.11.3 2.229.655 2.887.87a1.54 1.54 0 0 1 1.044 1.262c.596 4.477-.787 7.795-2.465 9.99a11.8 11.8 0 0 1-2.517 2.453 7 7 0 0 1-1.048.625c-.28.132-.581.24-.829.24s-.548-.108-.829-.24a7 7 0 0 1-1.048-.625 11.8 11.8 0 0 1-2.517-2.453C1.928 10.487.545 7.169 1.141 2.692A1.54 1.54 0 0 1 2.185 1.43 63 63 0 0 1 5.072.56"/>'
        '<path d="M9.5 6.5a1.5 1.5 0 0 1-1 1.415l.385 1.99a.5.5 0 0 1-.491.595h-.788a.5.5 0 0 1-.49-.595l.384-1.99a1.5 1.5 0 1 1 2-1.415"/>'
        '</svg>'
    ),
    'smart_toy': (
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-robot" viewBox="0 0 16 16">'
        '<path d="M6 12.5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 0 1h-3a.5.5 0 0 1-.5-.5M3 8.062C3 6.76 4.235 5.765 5.53 5.886a26.6 26.6 0 0 0 4.94 0C11.765 5.765 13 6.76 13 8.062v1.157a.93.93 0 0 1-.765.935c-.845.147-2.34.346-4.235.346s-3.39-.2-4.235-.346A.93.93 0 0 1 3 9.219zm4.542-.827a.25.25 0 0 0-.217.068l-.92.9a25 25 0 0 1-1.871-.183.25.25 0 0 0-.068.495c.55.076 1.232.149 2.02.193a.25.25 0 0 0 .189-.071l.754-.736.847 1.71a.25.25 0 0 0 .404.062l.932-.97a25 25 0 0 0 1.922-.188.25.25 0 0 0-.068-.495c-.538.074-1.207.145-1.98.189a.25.25 0 0 0-.166.076l-.754.785-.842-1.7a.25.25 0 0 0-.182-.135"/>'
        '<path d="M8.5 1.866a1 1 0 1 0-1 0V3h-2A4.5 4.5 0 0 0 1 7.5V8a1 1 0 0 0-1 1v2a1 1 0 0 0 1 1v1a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-1a1 1 0 0 0 1-1V9a1 1 0 0 0-1-1v-.5A4.5 4.5 0 0 0 10.5 3h-2zM14 7.5V13a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V7.5A3.5 3.5 0 0 1 5.5 4h5A3.5 3.5 0 0 1 14 7.5"/>'
        '</svg>'
    ),
    'event_note': (
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-list-ul" viewBox="0 0 16 16">'
        '<path fill-rule="evenodd" d="M5 11.5a.5.5 0 0 1 .5-.5h9a.5.5 0 0 1 0 1h-9a.5.5 0 0 1-.5-.5m0-4a.5.5 0 0 1 .5-.5h9a.5.5 0 0 1 0 1h-9a.5.5 0 0 1-.5-.5m0-4a.5.5 0 0 1 .5-.5h9a.5.5 0 0 1 0 1h-9a.5.5 0 0 1-.5-.5m-3 1a1 1 0 1 0 0-2 1 1 0 0 0 0 2m0 4a1 1 0 1 0 0-2 1 1 0 0 0 0 2m0 4a1 1 0 1 0 0-2 1 1 0 0 0 0 2"/>'
        '</svg>'
    ),
    'task_alt': (
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-check-circle-fill" viewBox="0 0 16 16">'
        '<path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0m-3.97-3.03a.75.75 0 0 0-1.08.022L7.477 9.417 5.384 7.323a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-.01-1.05z"/>'
        '</svg>'
    ),
    # Outlined sun icon
    'light_mode': (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<g fill="none" stroke="{COLOR}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="4"/>'
        '<path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5.64 5.64 4.22 4.22M19.78 19.78 18.36 18.36M5.64 18.36 4.22 19.78M19.78 4.22 18.36 5.64"/>'
        '</g>'
        '</svg>'
    ),
    'dark_mode': '<path d="M9.37 5.51A7 7 0 0012 19a7 7 0 006.49-9.37A7.003 7.003 0 019.37 5.51z"/>',
    'account_circle': '<path d="M12 12a5 5 0 100-10 5 5 0 000 10zm0 2c-5 0-9 2.5-9 5v3h18v-3c0-2.5-4-5-9-5z"/>',
    # Outlined settings gear (simplified)
    'settings': (
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-gear-fill" viewBox="0 0 16 16">'
        '<path d="M9.405 1.05c-.413-1.4-2.397-1.4-2.81 0l-.1.34a1.464 1.464 0 0 1-2.105.872l-.31-.17c-1.283-.698-2.686.705-1.987 1.987l.169.311c.446.82.023 1.841-.872 2.105l-.34.1c-1.4.413-1.4 2.397 0 2.81l.34.1a1.464 1.464 0 0 1 .872 2.105l-.17.31c-.698 1.283.705 2.686 1.987 1.987l.311-.169a1.464 1.464 0 0 1 2.105.872l.1.34c.413 1.4 2.397 1.4 2.81 0l.1-.34a1.464 1.464 0 0 1 2.105-.872l.31.17c1.283.698 2.686-.705 1.987-1.987l-.169-.311a1.464 1.464 0 0 1 .872-2.105l.34-.1c1.4-.413 1.4-2.397 0-2.81l-.34-.1a1.464 1.464 0 0 1-.872-2.105l.17-.31c.698-1.283-.705-2.686-1.987-1.987l-.311.169a1.464 1.464 0 0 1-2.105-.872zM8 10.93a2.929 2.929 0 1 1 0-5.86 2.929 2.929 0 0 1 0 5.858z"/>'
        '</svg>'
    ),
    # Outlined logout icon: door with arrow
    'logout': (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<g fill="none" stroke="{COLOR}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M10 5H6a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h4"/>'
        '<path d="M17 16l4-4-4-4"/>'
        '<path d="M21 12H10"/>'
        '</g>'
        '</svg>'
    ),
    'open_in_new': '<path d="M19 19H5V5h7V3H5a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7h-2v7zM14 3v2h3.59l-8.83 8.83 1.41 1.41L19 6.41V10h2V3h-7z"/>',
    # Outlined delete (trash can)
        'delete': ('<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-trash" viewBox="0 0 16 16">'
        '<path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0z"/>'
        '<path d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4zM2.5 3h11V2h-11z"/>'
        '</svg>'),
    # Outlined upload (arrow into tray)
    'upload': (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<g fill="none" stroke="{COLOR}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M12 16V4"/>'
        '<path d="M8 8l4-4 4 4"/>'
        '<path d="M4 20h16"/>'
        '</g>'
        '</svg>'
    ),
    # Outlined refresh (circular arrow)
    'refresh': (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<g fill="none" stroke="{COLOR}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M20 12a8 8 0 1 1-2.34-5.66"/>'
        '<path d="M20 4v4h-4"/>'
        '</g>'
        '</svg>'
    ),
    # Outlined check_circle
    'check_circle': (
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-check-circle-fill" viewBox="0 0 16 16">'
        '<path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0m-3.97-3.03a.75.75 0 0 0-1.08.022L7.477 9.417 5.384 7.323a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-.01-1.05z"/>'
        '</svg>'
    ),
    # Aliased simple chat icon name used elsewhere
    'chat': (
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-chat-left-text" viewBox="0 0 16 16">'
        '<path d="M14 1a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H4.414A2 2 0 0 0 3 11.586l-2 2V2a1 1 0 0 1 1-1zM2 0a2 2 0 0 0-2 2v12.793a.5.5 0 0 0 .854.353l2.853-2.853A1 1 0 0 1 4.414 12H14a2 2 0 0 0 2-2V2a2 2 0 0 0-2-2z"/>'
        '<path d="M3 3.5a.5.5 0 0 1 .5-.5h9a.5.5 0 0 1 0 1h-9a.5.5 0 0 1-.5-.5M3 6a.5.5 0 0 1 .5-.5h9a.5.5 0 0 1 0 1h-9A.5.5 0 0 1 3 6m0 2.5a.5.5 0 0 1 .5-.5h5a.5.5 0 0 1 0 1h-5a.5.5 0 0 1-.5-.5"/>'
        '</svg>'
    ),
    # SupportAgent outlined (headset with person)
    'support_agent': (
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-robot" viewBox="0 0 16 16">'
        '<path d="M6 12.5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 0 1h-3a.5.5 0 0 1-.5-.5M3 8.062C3 6.76 4.235 5.765 5.53 5.886a26.6 26.6 0 0 0 4.94 0C11.765 5.765 13 6.76 13 8.062v1.157a.93.93 0 0 1-.765.935c-.845.147-2.34.346-4.235.346s-3.39-.2-4.235-.346A.93.93 0 0 1 3 9.219zm4.542-.827a.25.25 0 0 0-.217.068l-.92.9a25 25 0 0 1-1.871-.183.25.25 0 0 0-.068.495c.55.076 1.232.149 2.02.193a.25.25 0 0 0 .189-.071l.754-.736.847 1.71a.25.25 0 0 0 .404.062l.932-.97a25 25 0 0 0 1.922-.188.25.25 0 0 0-.068-.495c-.538.074-1.207.145-1.98.189a.25.25 0 0 0-.166.076l-.754.785-.842-1.7a.25.25 0 0 0-.182-.135"/>'
        '<path d="M8.5 1.866a1 1 0 1 0-1 0V3h-2A4.5 4.5 0 0 0 1 7.5V8a1 1 0 0 0-1 1v2a1 1 0 0 0 1 1v1a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-1a1 1 0 0 0 1-1V9a1 1 0 0 0-1-1v-.5A4.5 4.5 0 0 0 10.5 3h-2zM14 7.5V13a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V7.5A3.5 3.5 0 0 1 5.5 4h5A3.5 3.5 0 0 1 14 7.5"/>'
        '</svg>'
    ),
    # Outlined send (paper plane)
    'send': '<path d="M2.01 21 23 12 2.01 3 2 10l15 2-15 2z"/>',
}


def _svg_data_uri(path_d: str, size_px: int, color: str) -> str:
    # If a full <svg> snippet is provided, inject dynamic color and size.
    if path_d.strip().startswith('<svg'):
        svg = path_d
        # Replace placeholder tokens and currentColor usages
        svg = svg.replace('{COLOR}', color)
        svg = svg.replace('currentColor', color)
        # Remove any pre-existing width/height to honor requested size
        svg = re.sub(r'\swidth="[^"]*"', '', svg)
        svg = re.sub(r'\sheight="[^"]*"', '', svg)
        # Inject normalized width/height at root, but do not force fill/stroke globally
        svg = svg.replace('<svg ', f'<svg width="{size_px}" height="{size_px}" ', 1)
        return 'data:image/svg+xml;utf8,' + quote(svg)
    # Otherwise wrap the provided path(s) with a group fill
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="{size_px}" height="{size_px}">'
        f'<g fill="{color}">{path_d}</g>'
        f'</svg>'
    )
    return 'data:image/svg+xml;utf8,' + quote(svg)


def mui_icon(
    name: str,
    *,
    size: int = 18,
    color: str | None = None,
    style: me.Style | None = None,
):
    # Compute a theme-aware default color if none provided
    if color is None:
        is_dark = me.theme_brightness() == 'dark'
        color = '#9aa0a6' if is_dark else '#5f6368'
    else:
        # If a CSS variable is passed (e.g., 'var(--token)'), it won't resolve inside
        # a data URI image. Substitute with a safe theme-aware fallback.
        if isinstance(color, str) and color.strip().startswith('var('):
            is_dark = me.theme_brightness() == 'dark'
            # Use general on-surface text colors as safe defaults
            color = '#e8eaed' if is_dark else '#202124'
    path = ICON_SVGS.get(name)
    if not path:
        # Fallback to a simple square if unknown
        path = '<rect x="4" y="4" width="16" height="16" rx="2"/>'
    src = _svg_data_uri(path, size, color)
    me.image(
        src=src,
        style=me.Style(width=f"{size}px", height=f"{size}px") if style is None else style,
    )
