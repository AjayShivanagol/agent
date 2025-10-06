import mesop as me
import mesop.labs as mel
from urllib.parse import quote
import base64
import json
from state.state import AppState
from .cookie_reader import cookie_reader
from .logout_helper import logout_helper
from components.mui_icon import mui_icon
from utils.request_context import current_userinfo
from utils.user_info import decode_userinfo


def on_click_logo(e: me.ClickEvent):
    """Handle logo click to navigate to home"""
    me.navigate("/")


def on_click_hamburger_menu(e: me.ClickEvent):
    """Handle hamburger menu click to toggle sidebar"""
    state = me.state(AppState)
    state.sidenav_open = not state.sidenav_open


def on_click_user_menu(e: me.ClickEvent):
    """Handle user menu click"""
    state = me.state(AppState)
    # Close language menu if open
    if state.show_language_menu:
        state.show_language_menu = False
    state.show_user_menu = not state.show_user_menu


def on_click_settings(e: me.ClickEvent):
    """Navigate to settings via profile menu"""
    state = me.state(AppState)
    state.show_user_menu = False
    me.navigate('/settings')


def on_click_logout(e: me.ClickEvent):
    """Logout clears API key and prompts API key dialog again"""
    state = me.state(AppState)
    state.api_key = ''
    state.show_user_menu = False
    # Trigger browser-side cookie clear + hard redirect to /logout
    state.trigger_logout = True


def on_click_backdrop(e: me.ClickEvent):
    """Close the user menu when clicking outside."""
    state = me.state(AppState)
    if state.show_user_menu:
        state.show_user_menu = False
    if state.show_language_menu:
        state.show_language_menu = False


def on_click_language_menu(e: me.ClickEvent):
    """Toggle the language selector menu"""
    state = me.state(AppState)
    # Close user menu if open
    if state.show_user_menu:
        state.show_user_menu = False
    state.show_language_menu = not state.show_language_menu


def on_select_language(lang: str):
    def _handler(e: me.ClickEvent):
        state = me.state(AppState)
        state.language = lang
        state.show_language_menu = False
    return _handler


def on_userinfo(e: mel.WebEvent):  # type: ignore[unused-argument]
    """Receive cookie value from web component, decode base64 JSON and store name."""
    try:
        detail = getattr(e, 'detail', {}) or {}
        value = detail.get('value', '')
        if not value:
            return
        data: dict = {}
        # Try URL-safe base64 (with auto padding), then raw JSON, then JWT payload
        try:
            pad = '=' * (-len(value) % 4)
            decoded = base64.urlsafe_b64decode((value + pad).encode('utf-8')).decode('utf-8')
            data = json.loads(decoded)
        except Exception:
            # Raw JSON
            try:
                data = json.loads(value)
            except Exception:
                # JWT: header.payload.signature
                try:
                    parts = value.split('.')
                    if len(parts) >= 2:
                        p = parts[1]
                        pad2 = '=' * (-len(p) % 4)
                        decoded2 = base64.urlsafe_b64decode((p + pad2).encode('utf-8')).decode('utf-8')
                        data = json.loads(decoded2)
                    else:
                        data = {}
                except Exception:
                    data = {}
        if not isinstance(data, dict):
            return
        # Map common identity fields from various IdPs
        first = (
            data.get('given_name')
            or data.get('firstName')
            or (data.get('preferred_name') or data.get('displayName') or data.get('name') or '').split(' ')[0]
        )
        last = (
            data.get('family_name')
            or data.get('lastName')
            or ' '.join((data.get('preferred_name') or data.get('displayName') or data.get('name') or '').split(' ')[1:])
        )
        email = (
            data.get('email')
            or data.get('mail')
            or data.get('upn')
            or data.get('preferred_username')
            or (data.get('emails')[0] if isinstance(data.get('emails'), list) and data.get('emails') else '')
            or ''
        )
        user_id = data.get('id', '')
        state = me.state(AppState)
        state.user_first_name = first or ''
        state.user_last_name = last or ''
        state.user_email = email or ''
        state.user_id = user_id or ''
    except Exception as ex:
        # Do not crash header if cookie parsing fails
        pass


def on_click_theme_toggle(e: me.ClickEvent):
    """Handle theme toggle between light and dark"""
    state = me.state(AppState)
    # Toggle should work even when current is 'system' by assuming dark system
    current = (state.theme_mode or "system").lower()
    if current == "system":
        # Assume user's system is dark if unspecified; flip to the opposite on first click
        assumed_effective = "dark"
        state.theme_mode = "light" if assumed_effective == "dark" else "dark"
    else:
        state.theme_mode = "dark" if current == "light" else "light"
    me.set_theme_mode(state.theme_mode)


def mb_header():
    """Mercedes-Benz UI Header Component - Official MBUI Style"""
    state = me.state(AppState)
    
    # Resolve effective theme when state is 'system' so initial render matches system (assume dark by default)
    effective_theme = (state.theme_mode or "system").lower()
    if effective_theme == "system":
        effective_theme = "dark"
    me.set_theme_mode(effective_theme)
    
    # Main toolbar container with Mercedes-Benz styling
    with me.box(
        style=me.Style(
            background="linear-gradient(90deg, #000000 0%, #3F3F3F 100%)",
            height="48px",
            box_shadow="0px 2px 4px -1px rgba(0,0,0,0.2), 0px 4px 5px 0px rgba(0,0,0,0.14), 0px 1px 10px 0px rgba(0,0,0,0.12)",
            position="fixed",
            top="0",
            left="0",
            right="0",
            z_index=100,
            pointer_events="none",  # Add this to prevent blocking clicks
        )
    ):
        # Get userinfo from request context (already processed by middleware)
        try:
            userinfo_header = current_userinfo.get()
            if userinfo_header and (not state.user_id and not state.user_email):
                user_data = decode_userinfo(userinfo_header)
                
                if user_data:
                    # Map the user data to state
                    first = (
                        user_data.get('given_name') or 
                        user_data.get('firstName') or 
                        (user_data.get('name') or '').split(' ')[0] if user_data.get('name') else ''
                    )
                    last = (
                        user_data.get('family_name') or 
                        user_data.get('lastName') or 
                        ' '.join((user_data.get('name') or '').split(' ')[1:]) if user_data.get('name') else ''
                    )
                    email = (
                        user_data.get('email') or 
                        user_data.get('mail') or 
                        user_data.get('upn') or ''
                    )
                    user_id = user_data.get('id', '')
                    state.user_first_name = first or ''
                    state.user_last_name = last or ''
                    state.user_email = email or ''
                    state.user_id = user_id or ''
            elif state.user_id or state.user_email:
                pass  # User info already in state
            else:
                pass  # No userinfo in context
        except Exception as ex:
            print(f"DEBUG: Error accessing userinfo context: {ex}")
        
        # Debug: Add a simple JavaScript to log all cookies to browser console
        me.html("""
        <script>
        console.log('DEBUG: All cookies:', document.cookie);
        ['userinfo', 'userInfo', 'user'].forEach(name => {
            const value = document.cookie.split('; ').find(row => row.startsWith(name + '='));
            console.log(`DEBUG: Cookie '${name}':`, value ? value.split('=')[1] : 'NOT FOUND');
        });
        </script>
        """, mode='sandboxed')

        # If logout was requested, insert helper that clears cookies and redirects
        if state.trigger_logout:
            logout_helper(redirect_to='/logout', key='logout-helper')

        # Left section - Menu button + Logo + Title (positioned on the left)
        with me.box(
            style=me.Style(
                position="absolute",
                left="24px",
                top="50%",
                transform="translateY(-50%)",
                display="flex",
                align_items="center",
                gap="12px",
                z_index=1,
                pointer_events="auto",  # Enable clicks on left section
            )
        ):
            # Hamburger menu button using provided SVG icon
            HAMBURGER_SVG = (
                '<svg xmlns="http://www.w3.org/2000/svg" class="MuiSvgIcon-root MuiSvgIcon-fontSizeMedium css-15zs5ps" focusable="false" aria-hidden="true" viewBox="0 0 24 24" data-testid="MenuIcon">'
                '<path fill="#fff" d="M3 18h18v-2H3zm0-5h18v-2H3zm0-7v2h18V6z"></path>'
                '</svg>'
            )
            hamburger_data_uri = 'data:image/svg+xml;utf8,' + quote(HAMBURGER_SVG)
            with me.content_button(
                type="flat",
                on_click=on_click_hamburger_menu,
                style=me.Style(
                    background="transparent",
                    border=me.Border.all(me.BorderSide(width=0)),
                    min_width="48px",
                    height="48px",
                    border_radius="4px",
                    padding=me.Padding(top=12, bottom=12, left=12, right=12)
                )
            ):
                me.image(src=hamburger_data_uri, style=me.Style(width="24px", height="24px"))
            # Mercedes-Benz logo next to hamburger
            # Provided SVG logo embedded as data URI (original center logo)
            LOGO_SVG = (
                '<svg xmlns="http://www.w3.org/2000/svg" class="MuiSvgIcon-root MuiSvgIcon-fontSizeMedium css-125yufo" focusable="false" aria-hidden="true" viewBox="0 0 64 64">'
                '<linearGradient id="a" x1="114" x2="162" y1="-142.9" y2="-183.1" gradientTransform="matrix(1 0 0 -1 -106 -131)" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#FFF"></stop><stop offset=".1" stop-color="#E7E8E6"></stop><stop offset=".1" stop-color="#CDD0D0"></stop><stop offset=".2" stop-color="#B5BBBD"></stop><stop offset=".2" stop-color="#A5ACAF"></stop><stop offset=".3" stop-color="#9BA3A7"></stop><stop offset=".3" stop-color="#98A0A4"></stop><stop offset=".4" stop-color="#828A8F"></stop><stop offset=".5" stop-color="#667075"></stop><stop offset=".6" stop-color="#535C63"></stop><stop offset=".7" stop-color="#475158"></stop><stop offset=".8" stop-color="#434D54"></stop><stop offset="1" stop-color="#475157"></stop></linearGradient><path fill="url(#a)" d="M63.3 32c0 17.3-14 31.3-31.3 31.3S.7 49.3.7 32 14.7.7 32 .7s31.3 14 31.3 31.3zM32 2.6C15.7 2.6 2.6 15.7 2.6 32S15.8 61.4 32 61.4c16.3 0 29.4-13.2 29.4-29.4C61.4 15.7 48.3 2.6 32 2.6z"></path><linearGradient id="b" x1="115.47" x2="160.47" y1="-144.06" y2="-181.86" gradientTransform="matrix(1 0 0 -1 -106 -131)" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#0B1F2A"></stop><stop offset=".2" stop-color="#333F47"></stop><stop offset=".5" stop-color="#777F84"></stop><stop offset=".5" stop-color="#81898D"></stop><stop offset=".7" stop-color="#B3B8B8"></stop><stop offset=".8" stop-color="#D2D5D3"></stop><stop offset=".8" stop-color="#DEE0DD"></stop><stop offset="1" stop-color="#FBFBFB"></stop></linearGradient><path fill="url(#b)" d="M32 2.6C15.7 2.6 2.6 15.7 2.6 32S15.8 61.4 32 61.4c16.3 0 29.4-13.2 29.4-29.4C61.4 15.7 48.3 2.6 32 2.6zm0 56.9C16.8 59.5 4.5 47.2 4.5 32S16.8 4.5 32 4.5 59.5 16.8 59.5 32 47.2 59.5 32 59.5z"></path><linearGradient id="c" x1="1933.73" x2="1955.63" y1="-176.94" y2="-237.14" gradientTransform="matrix(-1 0 0 1 1976.672 239.007)" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#E1E3E1"></stop><stop offset=".1" stop-color="#C1C5C4"></stop><stop offset=".3" stop-color="#9BA1A2"></stop><stop offset=".5" stop-color="#7D8487"></stop><stop offset=".7" stop-color="#687074" stop-opacity="0"></stop><stop offset=".8" stop-color="#5b6469" stop-opacity="0"></stop><stop offset="1" stop-color="#576065" stop-opacity="0"></stop></linearGradient><path fill="url(#c)" d="M32 63.3c17.3 0 31.3-14 31.3-31.3S49.3.7 32 .7.7 14.7.7 32s14 31.3 31.3 31.3zM32 0c17.6 0 32 14.4 32 32S49.6 64 32 64 0 49.6 0 32 14.4 0 32 0z" opacity=".4"></path><path fill="#FFF" d="M2.2 32.1C2.2 15.7 15.5 2.2 32 2.2s29.8 13.4 29.8 29.9c0 16.4-13.3 29.7-29.8 29.7S2.2 48.5 2.2 32.1zm9.3-20.6c-5.3 5.3-8.6 12.6-8.6 20.6 0 8 3.3 15.3 8.5 20.5 5.3 5.2 12.6 8.5 20.6 8.5 8 0 15.3-3.2 20.5-8.5 5.3-5.2 8.5-12.5 8.5-20.5s-3.3-15.3-8.5-20.6C47.3 6.2 40 2.9 32 2.9s-15.3 3.3-20.5 8.6z"></path><linearGradient id="d" x1="124.2" x2="151.8" y1="-139.1" y2="-186.9" gradientTransform="matrix(1 0 0 -1 -106 -131)" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#E1E3E1"></stop><stop offset=".1" stop-color="#C1C5C4"></stop><stop offset=".3" stop-color="#9BA1A2"></stop><stop offset=".5" stop-color="#7D8487"></stop><stop offset=".7" stop-color="#687074" stop-opacity="0"></stop><stop offset=".8" stop-color="#5b6469" stop-opacity="0"></stop><stop offset="1" stop-color="#576065" stop-opacity="0"></stop></linearGradient><path fill="url(#d)" d="M32 59.6c-7.4 0-14.3-2.9-19.5-8.1S4.4 39.4 4.4 32s2.9-14.3 8.1-19.5S24.6 4.4 32 4.4s14.3 2.9 19.5 8.1 8.1 12.1 8.1 19.5-2.9 14.3-8.1 19.5-12.1 8.1-19.5 8.1zm0-.8c7.1 0 13.9-2.8 18.9-7.8 5.1-5.1 7.8-11.8 7.8-18.9s-2.8-13.9-7.8-18.9C45.8 8.1 39.1 5.4 32 5.4c-7.1 0-13.9 2.8-18.9 7.8C8 18.1 5.2 24.9 5.2 32c0 7.1 2.8 13.9 7.8 18.9 5.1 5.1 11.9 7.9 19 7.9z" opacity=".4"></path><path fill="#FFF" d="M56.3 45c-.5-.4-19.8-15.7-19.8-15.7L32 3.6c-.3.1-.7.4-.9.8l-3.2 25L8 44.7s-.4.5-.6.8c-.1.2-.1.5-.1.8l24.6-10.1 24.6 10.1c.2-.5 0-1-.2-1.3z"></path><path fill="#565F64" d="m32.2 32.8-.2 4.6 22.6 9.1c.8.4 1.4.2 2-.2L32.5 32.7c-.1-.1-.3 0-.3.1z"></path><linearGradient id="e" x1="150.49" x2="148.79" y1="-170.39" y2="-173.19" gradientTransform="matrix(1 0 0 -1 -106 -131)" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#27343C"></stop><stop offset="1" stop-color="#00111e" stop-opacity="0"></stop></linearGradient><path fill="url(#e)" d="M32.2 32.8s1.3 2.3 2.8 3.9c2.1 2.3 4.9 3.9 4.9 3.9l14.7 5.9c.8.4 1.4.2 2-.2L32.5 32.7c-.1-.1-.3 0-.3.1z"></path><path fill="#A4AAAE" fill-opacity=".6" d="M56.5 45.4c0-.1-.1-.2-.2-.4L35.7 29.9l-2.8 1.8s.2.1.3 0c.3-.1.9-.2 1.5 0 .5.2 21.8 13.8 21.8 13.8v-.1z"></path><path fill="#333E46" d="M55.8 44.5 36.6 29.3l-.9.6 20.6 15.2c-.1-.2-.3-.4-.5-.6z"></path><path fill="#565F64" d="m32.5 31.3-.1.1s0 .2.2.1c.1-.1 3-1.6 4-2.2l-3.5-24c-.1-.9-.5-1.3-1.2-1.6l.4 27.8.2-.2z"></path><path fill="#A4AAAE" fill-opacity=".6" d="M30.8 5.3v1.3l-2.2 22.1c0 .3.1.6.4.8l1.3 1 .9-24.4.1-1.9c-.3.2-.4.6-.5 1.1zm-1.2 25.6-1.2-1L8.1 44.6s-.6.4-.7.8l.7-.4 21.3-13.4c.4-.2.5-.4.2-.7z"></path><path fill="#565F64" d="M31.7 32.8c0-.1-.1-.2-.2-.1L7.3 46.4c.6.4 1.2.5 2 .2l22.6-9.1-.2-4.7z"></path><linearGradient id="f" x1="145.58" x2="142.78" y1="-160.11" y2="-155.61" gradientTransform="matrix(1 0 0 -1 -106 -131)" gradientUnits="userSpaceOnUse"><stop offset=".1" stop-color="#02131F"></stop><stop offset=".9" stop-color="#02131f" stop-opacity="0"></stop></linearGradient><path fill="url(#f)" d="m32.4 31.4.1-.1-.1.1s0 .1.1.1h.1c.1-.1 3-1.6 4-2.2l-.4-2.9-3.1-21.1c0-.4-.1-.7-.3-.9 0 0 1.5 20.2 1.5 22.4 0 2.9-1.9 4.6-1.9 4.6z"></path><linearGradient id="g" x1="137.98" x2="133.78" y1="-167.34" y2="-168.54" gradientTransform="matrix(1 0 0 -1 -106 -131)" gradientUnits="userSpaceOnUse"><stop offset=".2" stop-color="#02131F"></stop><stop offset=".9" stop-color="#02131f" stop-opacity="0"></stop></linearGradient><path fill="url(#g)" fill-opacity=".8" d="M31.7 32.8c0-.1-.1-.2-.2-.1L7.3 46.4c.6.4 1.2.5 2 .2l22.6-9.1-.2-4.7z"></path><linearGradient id="h" x1="126.79" x2="126.19" y1="-172.9" y2="-171.4" gradientTransform="matrix(1 0 0 -1 -106 -131)" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#02131F"></stop><stop offset=".1" stop-color="#02131F"></stop><stop offset="1" stop-color="#02131f" stop-opacity="0"></stop></linearGradient><path fill="url(#h)" d="m9.3 46.5 22.6-9.1-.2-4.4c-.4 1.2-1.1 2.5-3 3.5-1.4.8-14.8 7.4-19.6 9.7-.3.2-.7.3-.9.4.4.2.7.1 1.1-.1z" opacity=".8"></path><linearGradient id="i" x1="141.6" x2="138.2" y1="-148.21" y2="-148.61" gradientTransform="matrix(1 0 0 -1 -106 -131)" gradientUnits="userSpaceOnUse"><stop offset=".3" stop-color="#02131F"></stop><stop offset=".3" stop-color="#02131F"></stop><stop offset=".8" stop-color="#02131f" stop-opacity="0"></stop></linearGradient><path fill="url(#i)" d="m32.5 31.3-.1.1s0 .2.2.1c.1-.1 3-1.6 4-2.2l-3.5-24c-.1-.9-.5-1.3-1.2-1.6l.4 27.8.2-.2z"></path><linearGradient id="j" x1="141.71" x2="139.41" y1="-148.16" y2="-148.46" gradientTransform="matrix(1 0 0 -1 -106 -131)" gradientUnits="userSpaceOnUse"><stop offset=".4" stop-color="#27343C"></stop><stop offset="1" stop-color="#3b474e" stop-opacity="0"></stop></linearGradient><path fill="url(#j)" d="m32.5 31.3-.1.1s0 .2.2.1c.1-.1 3-1.6 4-2.2l-3.5-24c-.1-.9-.5-1.3-1.2-1.6l.4 27.8.2-.2z"></path><linearGradient id="k" x1="105.64" x2="133.54" y1="-163.83" y2="-179.93" gradientTransform="matrix(1 0 0 -1 -106 -131)" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#24303a" stop-opacity="0"></stop><stop offset="0" stop-color="#25323b" stop-opacity="0"></stop><stop offset=".1" stop-color="#27343C"></stop></linearGradient><path fill="url(#k)" d="M5.1 44.4C4.4 42.8.4 35 4.8 20H3.1c-.9 3-1.6 4.8-2 7.5 0 0-.2 1-.3 2.1C.7 30.7.7 31.3.7 32c0 6 1.5 9.5 1.5 9.5 1.6 5 4.4 9.5 8.2 12.9 3.3 2.9 8.4 5.1 12.6 5.9-.7-.1-12.7-5.2-17.9-15.9z"></path><linearGradient id="l" x1="137.95" x2="137.95" y1="-168.4" y2="-163.6" gradientTransform="matrix(1 0 0 -1 -106 -131)" gradientUnits="userSpaceOnUse"><stop offset=".3" stop-color="#A5ABAF"></stop><stop offset="1" stop-color="#a5abaf" stop-opacity="0"></stop></linearGradient><path fill="url(#l)" d="M32.4 32.6h-.9c.1 0 .2 0 .2.1l.2 4.6h.1l.2-4.6c0-.1.1-.2.2-.1z"></path><linearGradient id="m" x1="153.65" x2="153.65" y1="-133.3" y2="-194.3" gradientTransform="matrix(1 0 0 -1 -106 -131)" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#DEE0DD"></stop><stop offset="0" stop-color="#C5C9C7"></stop><stop offset="0" stop-color="#9EA4A5"></stop><stop offset="0" stop-color="#82898C"></stop><stop offset="0" stop-color="#71797D"></stop><stop offset="0" stop-color="#6B7378"></stop><stop offset=".2" stop-color="#333F47"></stop><stop offset=".5" stop-color="#27343C"></stop><stop offset=".8" stop-color="#333F47"></stop><stop offset="1" stop-color="#434D54"></stop></linearGradient><path fill="url(#m)" d="M42 2.3c10.5 4 20.4 15 20.4 28.9C62.4 48 49 61.7 32 61.7v1.6c17 0 31.3-14 31.3-31.3 0-13.8-8.8-25.4-21.3-29.7z"></path><linearGradient id="n" x1="138" x2="138.3" y1="-131.7" y2="-131.7" gradientTransform="matrix(1 0 0 -1 -106 -131)" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#DEE0DD"></stop><stop offset="0" stop-color="#C5C9C7"></stop><stop offset="0" stop-color="#9EA4A5"></stop><stop offset="0" stop-color="#82898C"></stop><stop offset="0" stop-color="#71797D"></stop><stop offset="0" stop-color="#6B7378"></stop><stop offset=".2" stop-color="#333F47"></stop><stop offset=".5" stop-color="#27343C"></stop><stop offset=".8" stop-color="#333F47"></stop><stop offset="1" stop-color="#434D54"></stop></linearGradient><path fill="url(#n)" d="M32.3.7H32h.3z"></path><linearGradient id="o" x1="163.29" x2="149.79" y1="-139.09" y2="-158.89" gradientTransform="matrix(1 0 0 -1 -106 -131)" gradientUnits="userSpaceOnUse"><stop offset=".7" stop-color="#27343C"></stop><stop offset=".7" stop-color="#2B373F"></stop><stop offset=".7" stop-color="#36424A"></stop><stop offset=".7" stop-color="#49545B"></stop><stop offset=".8" stop-color="#646d73" stop-opacity="0"></stop><stop offset=".8" stop-color="#868d92" stop-opacity="0"></stop><stop offset=".8" stop-color="#b0b5b8" stop-opacity="0"></stop><stop offset=".8" stop-color="#e1e3e4" stop-opacity="0"></stop><stop offset=".8" stop-color="#fff" stop-opacity="0"></stop></linearGradient><path fill="url(#o)" d="M58.8 20.2C51.8 4.1 36 3.2 35.1 3.1H35c12.1 2.2 19.8 10.1 22.5 18.4v.1c1.2 3.2 1.8 6.6 1.9 10.3.1 3.5-.7 7.4-2.2 11-.1.5-.2 1.1-.3 1.1h1.6c4.8-9 2.7-18.1.3-23.8z"></path><path fill="#FBFBFB" d="M2.2 32.1C2.2 15.7 15.5 2.2 32 2.2s29.8 13.4 29.8 29.9c0 16.4-13.3 29.7-29.8 29.7S2.2 48.5 2.2 32.1zm9.3-20.6c-5.3 5.3-8.6 12.6-8.6 20.6 0 8 3.3 15.3 8.5 20.5 5.3 5.2 12.6 8.5 20.6 8.5 8 0 15.3-3.2 20.5-8.5 5.3-5.2 8.5-12.5 8.5-20.5s-3.3-15.3-8.5-20.6C47.3 6.2 40 2.9 32 2.9s-15.3 3.3-20.5 8.6z"></path><path fill="#333F47" d="m7.9 44.8 20.4-14.7c1.1.6 2.9 1.4 3.1 1.4.2.1.2-.1.2-.1l-2.5-2.1c-.3-.2-.4-.5-.4-.8l2.4-24.1c-.1.1-.1.3-.2.4-.1.2-.1.3-.1.5l-3.5 24.1L8.1 44.5c-.1.1-.2.2-.2.3z"></path></svg>'
            )
            data_uri_left_logo = 'data:image/svg+xml;utf8,' + quote(LOGO_SVG)
            with me.content_button(
                type="flat",
                on_click=on_click_logo,
                style=me.Style(
                    background="transparent",
                    border=me.Border.all(me.BorderSide(width=0)),
                    padding=me.Padding(top=4, bottom=4, left=4, right=4),
                    min_width="auto",
                    height="auto",
                    border_radius="4px"
                )
            ):
                me.image(src=data_uri_left_logo, style=me.Style(width="28px", height="28px"))
            # App title text next to hamburger
            me.text(
                "FC<OS> | Agentic Studio - CSC Agent",
                style=me.Style(
                    color="#FFFFFF",
                    font_size="16px",
                    font_weight="500",
                    letter_spacing="0.3px"
                )
            )
        
        # No center spacer needed with absolute positioning
        
        # Right section - Theme toggle and user avatar + name (positioned on the right)
        with me.box(
            style=me.Style(
                position="absolute",
                right="24px",
                top="50%",
                transform="translateY(-50%)",
                display="flex",
                align_items="center",
                gap="20px",
                z_index=1,
                pointer_events="auto",  # Enable clicks on right section
            )
        ):
            # Theme toggle button (show the action icon: sun when dark, moon when light)
            theme_icon = "light_mode" if effective_theme == "dark" else "dark_mode"

            with me.content_button(
                type="flat",
                on_click=on_click_theme_toggle,
                style=me.Style(
                    background="transparent",
                    border=me.Border.all(me.BorderSide(width=0)),
                    min_width="35px",
                    height="35px",
                    border_radius="50%",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                    padding=me.Padding.all(0),
                ),
            ):
                mui_icon(theme_icon, color="#FFFFFF")
            
            # Language switcher globe icon button
            # Provided SVG from user; will render if #icon-menu-language is defined in sprite.
            LANGUAGE_SVG = (
                '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="#FFFFFF" class="bi bi-globe" viewBox="0 0 16 16">'
                '<path d="M0 8a8 8 0 1 1 16 0A8 8 0 0 1 0 8m7.5-6.923c-.67.204-1.335.82-1.887 1.855A8 8 0 0 0 5.145 4H7.5zM4.09 4a9.3 9.3 0 0 1 .64-1.539 7 7 0 0 1 .597-.933A7.03 7.03 0 0 0 2.255 4zm-.582 3.5c.03-.877.138-1.718.312-2.5H1.674a7 7 0 0 0-.656 2.5zM4.847 5a12.5 12.5 0 0 0-.338 2.5H7.5V5zM8.5 5v2.5h2.99a12.5 12.5 0 0 0-.337-2.5zM4.51 8.5a12.5 12.5 0 0 0 .337 2.5H7.5V8.5zm3.99 0V11h2.653c.187-.765.306-1.608.338-2.5zM5.145 12q.208.58.468 1.068c.552 1.035 1.218 1.65 1.887 1.855V12zm.182 2.472a7 7 0 0 1-.597-.933A9.3 9.3 0 0 1 4.09 12H2.255a7 7 0 0 0 3.072 2.472M3.82 11a13.7 13.7 0 0 1-.312-2.5h-2.49c.062.89.291 1.733.656 2.5zm6.853 3.472A7 7 0 0 0 13.745 12H11.91a9.3 9.3 0 0 1-.64 1.539 7 7 0 0 1-.597.933M8.5 12v2.923c.67-.204 1.335-.82 1.887-1.855q.26-.487.468-1.068zm3.68-1h2.146c.365-.767.594-1.61.656-2.5h-2.49a13.7 13.7 0 0 1-.312 2.5m2.802-3.5a7 7 0 0 0-.656-2.5H12.18c.174.782.282 1.623.312 2.5zM11.27 2.461c.247.464.462.98.64 1.539h1.835a7 7 0 0 0-3.072-2.472c.218.284.418.598.597.933M10.855 4a8 8 0 0 0-.468-1.068C9.835 1.897 9.17 1.282 8.5 1.077V4z"/>'
                '</svg>'
            )
            globe_data_uri = 'data:image/svg+xml;utf8,' + quote(LANGUAGE_SVG)
            with me.content_button(
                type="flat",
                on_click=on_click_language_menu,
                style=me.Style(
                    background="transparent",
                    border=me.Border.all(me.BorderSide(width=0)),
                    min_width="35px",
                    height="35px",
                    border_radius="50%",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                    padding=me.Padding.all(0),
                ),
            ):
                # Render SVG larger to better match avatar glyph height
                me.image(src=globe_data_uri, style=me.Style(width="22px", height="22px"))

            # User avatar: gray circle with initials, clickable
            initials = ""
            full_name_calc = (state.user_first_name + (" " if state.user_first_name and state.user_last_name else "") + state.user_last_name).strip()
            if full_name_calc:
                parts = [p for p in full_name_calc.split(" ") if p]
                if parts:
                    first = parts[0][0].upper()
                    last = parts[-1][0].upper() if len(parts) > 1 else ""
                    initials = (first + last)[:2]
            elif state.user_email:
                local = state.user_email.split('@')[0]
                filtered = "".join(ch for ch in local if ch.isalnum()).upper()
                initials = filtered[:2]
            # Enforce exactly two characters, otherwise fallback to icon
            if len(initials) != 2:
                initials = ""

            with me.content_button(
                type="flat",
                on_click=on_click_user_menu,
                style=me.Style(
                    background="#9e9e9e",
                    border=me.Border.all(me.BorderSide(width=0)),
                    min_width="27px",
                    height="27px",
                    border_radius="50%",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                    box_shadow="0 2px 6px rgba(0,0,0,0.25)",
                    padding=me.Padding.all(0),
                ),
            ):
                if initials:
                    me.text(initials, style=me.Style(color="#FFFFFF", font_weight="700", font_size="12px"))
                else:
                    mui_icon("account_circle", color="#FFFFFF", size=16)

            # Backdrop to close menu when clicking anywhere
            if state.show_user_menu:
                with me.box(
                    style=me.Style(
                        position="fixed",
                        top="0",
                        left="0",
                        right="0",
                        bottom="0",
                        z_index=1150,
                        background="rgba(0,0,0,0)"
                    )
                ):
                    me.button(
                        "",
                        type="flat",
                        on_click=on_click_backdrop,
                        style=me.Style(
                            background="transparent",
                            border=me.Border.all(me.BorderSide(width=0)),
                            width="100%",
                            height="100%"
                        )
                    )

            # Backdrop for language menu as well
            if state.show_language_menu:
                with me.box(
                    style=me.Style(
                        position="fixed",
                        top="0",
                        left="0",
                        right="0",
                        bottom="0",
                        z_index=1150,
                        background="rgba(0,0,0,0)"
                    )
                ):
                    me.button(
                        "",
                        type="flat",
                        on_click=on_click_backdrop,
                        style=me.Style(
                            background="transparent",
                            border=me.Border.all(me.BorderSide(width=0)),
                            width="100%",
                            height="100%"
                        )
                    )

            # Profile dropdown menu
            state = me.state(AppState)
            if state.show_user_menu:
                with me.box(
                    style=me.Style(
                        position="absolute",
                        top="56px",
                        right="24px",
                        background="#ffffff",
                        border_radius="8px",
                        box_shadow="0 10px 20px rgba(0,0,0,0.25)",
                        padding=me.Padding(top=10, bottom=10, left=12, right=12),
                        min_width="160px",
                        border=me.Border.all(me.BorderSide(color="rgba(0,0,0,0.12)", width=1)),
                        z_index=1200
                    )
                ):
                    # Header: Full name and email (styled as menu items)
                    full_name_hdr = (state.user_first_name + (" " if state.user_first_name and state.user_last_name else "") + state.user_last_name).strip()
                    
                    # Vertical menu items like reference
                    def menu_item_row(icon: str, label: str, on_click=None):
                        with me.content_button(
                            type="flat",
                            on_click=on_click if on_click else (lambda e: None),
                            style=me.Style(
                                width="100%",
                                background="transparent",
                                border=me.Border.all(me.BorderSide(width=0)),
                                border_radius="6px",
                                padding=me.Padding(top=8, bottom=8, left=6, right=6),
                            ),
                        ):
                            with me.box(
                                style=me.Style(
                                    display="flex",
                                    align_items="center",
                                    justify_content="flex-start",
                                    gap="8px",
                                    margin=me.Margin.all(0),
                                    padding=me.Padding.all(0),
                                )
                            ):
                                mui_icon(icon, color="#212121")
                                me.text(label, style=me.Style(color="#212121", font_size="14px", text_align="left"))

                    # User info items with dynamic box for proper left alignment
                    def user_info_item(label: str):
                        with me.box(
                            style=me.Style(
                                width="100%",
                                background="transparent",
                                border_radius="6px",
                                padding=me.Padding(top=8, bottom=8, left=6, right=6),
                                cursor="pointer",
                                display="block",
                            ),
                        ):
                            me.text(label, style=me.Style(
                                color="#212121", 
                                font_size="14px", 
                                text_align="left",
                                display="block",
                                width="auto",
                                margin=me.Margin.all(0),
                                padding=me.Padding.all(0)
                            ))

                    # Display user info using the same button style but without icons
                    if full_name_hdr or state.user_email:
                        # Show name as a menu item
                        display_name = full_name_hdr or (state.user_email.split('@')[0] if state.user_email else '')
                        if display_name:
                            user_info_item(display_name)
                        
                        # Show email as a menu item if available
                        if state.user_email:
                            user_info_item(state.user_email)
                        
                        # Add divider after user info
                        with me.box(style=me.Style(margin=me.Margin(top=4, bottom=4))):
                            me.divider()

                    # Settings
                    menu_item_row('settings', 'Settings', on_click_settings)
                    # Logout
                    menu_item_row('logout', 'Logout', on_click_logout)

            # Language dropdown menu
            state = me.state(AppState)
            if state.show_language_menu:
                with me.box(
                    style=me.Style(
                        position="absolute",
                        top="56px",
                        # Position a bit left from the profile menu so it appears under globe
                        right="80px",
                        background="#ffffff",
                        border_radius="8px",
                        box_shadow="0 10px 20px rgba(0,0,0,0.25)",
                        padding=me.Padding(top=10, bottom=10, left=12, right=12),
                        min_width="160px",
                        border=me.Border.all(me.BorderSide(color="rgba(0,0,0,0.12)", width=1)),
                        z_index=1200
                    )
                ):
                    def lang_item(label: str, code: str):
                        with me.content_button(
                            type="flat",
                            on_click=on_select_language(code),
                            style=me.Style(
                                width="100%",
                                background="transparent",
                                border=me.Border.all(me.BorderSide(width=0)),
                                border_radius="6px",
                                padding=me.Padding(top=8, bottom=8, left=6, right=6),
                            ),
                        ):
                            me.text(label, style=me.Style(color="#212121", font_size="16px", text_align="left", font_weight="600"))

                    lang_item('English', 'en')
                    lang_item('Deutsch', 'de')


def mb_header_spacer():
    """Spacer to account for fixed header"""
    with me.box(
        style=me.Style(
            height="48px",
            width="100%"
        )
    ):
        pass