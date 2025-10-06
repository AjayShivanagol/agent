import mesop as me
from components.mui_icon import mui_icon

from state.state import AppState
from styles.styles import (
    DEFAULT_MENU_STYLE,
    SIDENAV_MAX_WIDTH,
    SIDENAV_MIN_WIDTH,
    _FANCY_TEXT_GRADIENT,
)
from components.conversation_list import add_conversation


# Admin section pages
page_json = [
    {'display': 'Remote Agents', 'icon': 'smart_toy', 'route': '/agents'},
    {'display': 'Event List', 'icon': 'event_note', 'route': '/event_list'},
    {'display': 'Task List', 'icon': 'task_alt', 'route': '/task_list'},
]


def on_sidenav_menu_click(e: me.ClickEvent):  # pylint: disable=unused-argument
    """Side navigation menu click handler"""
    state = me.state(AppState)
    state.sidenav_open = not state.sidenav_open


def navigate_to(e: me.ClickEvent):
    """Navigate to a specific page"""
    s = me.state(AppState)
    idx = int(e.key)
    if idx > len(page_json):
        return
    page = page_json[idx]
    s.current_page = page['route']
    me.navigate(s.current_page)
    yield


def navigate_to_conversation(e: me.ClickEvent):
    """Navigate to a conversation by ID (from sidenav list)."""
    s = me.state(AppState)
    conv_id = e.key or ''
    if not conv_id:
        return
    s.current_conversation_id = conv_id
    # Replace any existing params with only conversation_id for cleanliness
    me.query_params.clear()
    me.query_params.update({'conversation_id': conv_id})
    s.current_page = '/conversation'
    me.navigate('/conversation', query_params=me.query_params)
    yield


def navigate_to_current_conversation(e: me.ClickEvent):  # pylint: disable=unused-argument
    """Navigate Home from the Conversations header arrow."""
    print("DEBUG: Home button clicked")  # Add debug
    s = me.state(AppState)
    s.current_page = '/'
    s.current_conversation_id = ''
    me.query_params.clear()
    me.navigate('/', query_params={})
    yield


def _toggle_section(section: str):
    """Return a click handler that toggles the given section expand state."""
    def _handler(e: me.ClickEvent):  # pylint: disable=unused-argument
        print(f"DEBUG: Toggle section clicked: {section}")  # Add debug
        s = me.state(AppState)
        if section == 'conversations':
            s.nav_expand_conversations = not s.nav_expand_conversations
        else:
            s.nav_expand_admin = not s.nav_expand_admin
        # Force UI update
        yield

    return _handler


@me.component
def sidenav(current_page: str):
    """Render side navigation"""
    app_state = me.state(AppState)
    # Theme-aware background matching the main content container
    effective_brightness = me.theme_brightness()
    is_dark = (
        app_state.theme_mode == 'dark'
        or (app_state.theme_mode == 'system' and effective_brightness == 'dark')
    )
    sidenav_bg = '#2d2d2d' if is_dark else '#ffffff'
    with me.sidenav(
        opened=True,
        style=me.Style(
            width=SIDENAV_MAX_WIDTH
            if app_state.sidenav_open
            else SIDENAV_MIN_WIDTH,
            background=sidenav_bg,
            padding=me.Padding(left=0, right=0),
            z_index=50,
        ),
    ):
        with me.box(
            style=me.Style(
                margin=me.Margin(top=16, left=0, right=0, bottom=16),
                display='flex',
                flex_direction='column',
                gap=5,
            ),
        ):
            with me.box(
                style=me.Style(
                    display='flex',
                    flex_direction='row',
                    gap=5,
                    align_items='center',
                ),
            ):
                with me.content_button(
                    type='icon',
                    on_click=on_sidenav_menu_click,
                ):
                    with me.box():
                        with me.tooltip(message='Expand menu'):
                            mui_icon('menu')
                if app_state.sidenav_open:
                    me.text('STUDIO', style=_FANCY_TEXT_GRADIENT)
            me.box(style=me.Style(height=16))

            # Conversations expandable section
            with me.box(style=me.Style(margin=me.Margin(top=8, left=0))):
                # Header row container
                with me.box(
                    style=me.Style(
                        display='flex',
                        flex_direction='row',
                        gap=8,
                        align_items='center',
                        justify_content='flex-start',
                        padding=me.Padding.symmetric(vertical=8),
                        width='100%',
                        margin=me.Margin(left=0, right=0),
                    )
                ):
                    # Left clickable area toggles expand/collapse only
                    with me.content_button(
                        type='flat',
                        on_click=lambda e: _toggle_section('conversations')(e),
                        style=me.Style(
                            background='transparent',
                            border_radius='0px',
                            padding=me.Padding(left=0, right=0, top=0, bottom=0),
                            cursor='pointer',  # Add this
                            pointer_events='auto',  # Add this
                        ),
                    ):
                        with me.box(
                            style=me.Style(
                                display='flex',
                                flex_direction='row',
                                gap=8,
                                align_items='center',
                                justify_content='flex-start',
                            )
                        ):
                            mui_icon(
                                'expand_more' if app_state.nav_expand_conversations else 'chevron_right',
                                color='#9aa0a6' if is_dark else '#5f6368',
                            )
                            # Fixed-width spacer to align header label with conversation labels
                            with me.box(style=me.Style(width='18px')):
                                mui_icon(
                                    'chat_bubble',
                                    color='#9aa0a6' if is_dark else '#5f6368',
                                )
                            if app_state.sidenav_open:
                                me.text(
                                    'Conversations',
                                    style=me.Style(
                                        color='#e8eaed' if is_dark else '#202124',
                                        text_align='left',
                                    ),
                                )

                    # Spacer to push buttons to the right
                    with me.box(style=me.Style(flex='1')):
                        pass

                    # Navigate to home/current conversation (arrow)
                    with me.content_button(
                        type='icon',
                        on_click=navigate_to_current_conversation,
                    ):
                        with me.tooltip(message='Go to Conversations'):
                            mui_icon('home')

                    # New chat button (same behavior as plus button on lists)
                    with me.content_button(type='icon', on_click=add_conversation):
                        with me.tooltip(message='New chat'):
                            mui_icon('add')

                if app_state.nav_expand_conversations:
                    # Full-width list; indent items similar to Admin section
                    with me.box(style=me.Style(display='flex', flex_direction='column', width='100%', padding=me.Padding(left=0, right=0, top=0, bottom=0), margin=me.Margin(left=30))):
                        for conv in app_state.conversations:
                            is_active_conv = app_state.current_conversation_id == conv.conversation_id
                            with me.content_button(
                                key=conv.conversation_id,
                                on_click=navigate_to_conversation,
                                style=me.Style(
                                    width='100%',
                                    background=('rgba(0,0,0,0.06)' if (is_active_conv and not is_dark) else ('rgba(255,255,255,0.08)' if (is_active_conv and is_dark) else 'transparent')),
                                    border_radius='0px',
                                    padding=me.Padding(left=0, right=0, top=6, bottom=6),
                                    display='flex',
                                    justify_content='flex-start',
                                    align_items='center',
                                    text_align='left',
                                    margin=me.Margin(left=0, right=0, top=0, bottom=0),
                                ),
                                type='flat',
                            ):
                                with me.box(style=me.Style(display='flex', flex_direction='row', align_items='center', justify_content='flex-start', gap=8, width='100%', margin=me.Margin(left=0, right=0, top=0, bottom=0), padding=me.Padding(left=0, right=0, top=0, bottom=0))):
                                    # Fixed-width icon slot so all labels align to the same x-position
                                    with me.box(style=me.Style(width='18px', display='flex', justify_content='center')):
                                        mui_icon('forum', color='#9aa0a6' if is_dark else '#5f6368', size=16)
                                    if app_state.sidenav_open:
                                        # Show friendly conversation name with truncation fallback
                                        name = (conv.conversation_name or '').strip() or (f"Conversation {conv.conversation_id[:8]}" if conv.conversation_id else 'Conversation')
                                        me.text(
                                            name,
                                            style=me.Style(
                                                color='#e8eaed' if is_dark else '#202124',
                                                font_size='12px',
                                                white_space='nowrap',
                                                text_overflow='ellipsis',
                                                overflow='hidden',
                                                flex='1',
                                                margin=me.Margin(left=0, right=0, top=0, bottom=0),
                                            ),
                                        )

            # Admin expandable section
            with me.box(style=me.Style(margin=me.Margin(top=8, left=0))):
                with me.content_button(
                    type='flat',
                    on_click=lambda e: _toggle_section('admin')(e),
                    style=me.Style(background='transparent', border_radius='0px', padding=me.Padding(left=0, right=0, top=0, bottom=0)),
                ):
                    with me.box(style=me.Style(display='flex', flex_direction='row', gap=8, align_items='center', justify_content='flex-start', padding=me.Padding.symmetric(vertical=8), width='auto', margin=me.Margin(left=0))):
                        mui_icon('expand_more' if app_state.nav_expand_admin else 'chevron_right', color='#9aa0a6' if is_dark else '#5f6368')
                        mui_icon('admin_panel_settings', color='#9aa0a6' if is_dark else '#5f6368')
                        if app_state.sidenav_open:
                            me.text('Admin', style=me.Style(color='#e8eaed' if is_dark else '#202124', text_align='left'))

                if app_state.nav_expand_admin:
                    with me.box(style=me.Style(display='flex', flex_direction='column', align_items='flex-start', width='100%', margin=me.Margin(left=30))):
                        for idx, page in enumerate(page_json):
                            is_active = app_state.current_page == page['route']
                            menu_item(
                                idx,
                                page['icon'],
                                page['display'],
                                not app_state.sidenav_open,
                                is_active=is_active,
                                is_dark=is_dark,
                                align_right=False,
                                align_center=False,  # Keep children left-aligned with parent
                            )
            # settings placeholder (theme toggle removed)
            # with me.box(style=MENU_BOTTOM):
            #     pass


def menu_item(
    key: int,
    icon: str,
    text: str,
    minimized: bool = True,
    content_style: me.Style = DEFAULT_MENU_STYLE,
    *,
    is_active: bool = False,
    is_dark: bool = False,
    align_right: bool = False,
    align_center: bool = False,
):
    """Render menu item"""
    # Theme-aware colors
    inactive_color = '#9aa0a6' if is_dark else '#5f6368'
    active_color = '#4285f4'  # brand accent
    bg_active = 'rgba(255,255,255,0.08)' if is_dark else 'rgba(0,0,0,0.06)'
    bg_hover = 'rgba(255,255,255,0.06)' if is_dark else 'rgba(0,0,0,0.04)'

    # Base container styles for rows (layout/padding only; background is on container/button)
    row_style_expanded = me.Style(
        display='flex',
        flex_direction='row',
        gap=8,
        align_items='center',
        justify_content=(
            'flex-end' if align_right else ('center' if align_center else 'flex-start')
        ),
        padding=me.Padding(top=8, bottom=8, left=0, right=0),
        border=me.Border(left=me.BorderSide(color='transparent', width=0)),
        border_radius='0px',
        width='100%',
    )

    # Minimized: center the icon horizontally
    row_style_min = me.Style(
        display='flex',
        flex_direction='row',
        gap=0,
        align_items='center',
        justify_content=(
            'flex-end' if align_right else ('center' if align_center else 'flex-start')
        ),
        padding=me.Padding(top=8, bottom=8, left=0, right=0),
        border=me.Border(left=me.BorderSide(color='transparent', width=0)),
        border_radius='0px',
        width='100%',
    )

    # Button style takes full width and carries the active background
    button_style = me.Style(
        width='100%',
        background='transparent',
        border_radius='0px',
        display='block',
        padding=me.Padding(left=0, right=0, top=0, bottom=0),
        border=me.Border(
            top=me.BorderSide(width=0, color='transparent'),
            right=me.BorderSide(width=0, color='transparent'),
            bottom=me.BorderSide(width=0, color='transparent'),
            left=me.BorderSide(width=0, color='transparent'),
        ),
    )

    # Full-width container that carries the active background
    container_style = me.Style(
        width='100%',
        background=(bg_active if is_active else 'transparent'),
        border_radius='0px',
    )

    icon_style = me.Style(
        color=(active_color if is_active else inactive_color),
        font_size='22px',
        line_height='1.1',
        margin=me.Margin(top=0),
        padding=me.Padding(left=0, right=0, top=0, bottom=0),
    )
    text_style = me.Style(
        color=(active_color if is_active else ("#e8eaed" if is_dark else '#202124')),
        text_align=(
            'right' if align_right else ('center' if align_center else 'left')
        ),
    )

    if minimized:  # minimized
        with me.box(style=container_style):
            with me.box(style=row_style_min):
                with me.content_button(
                    key=str(key),
                    on_click=navigate_to,
                    style=button_style,
                    type='icon',
                ):
                    with me.tooltip(message=text):
                        mui_icon(icon, color=(active_color if is_active else inactive_color), size=16)

    else:  # expanded
        with me.box(style=container_style):
            with me.content_button(
                key=str(key),
                on_click=navigate_to,
                style=button_style,
            ):
                with me.box(style=row_style_expanded):
                    mui_icon(icon, color=(active_color if is_active else inactive_color), size=16)
                    me.text(text, style=text_style)


def toggle_theme(e: me.ClickEvent):  # pylint: disable=unused-argument
    """Toggle theme event"""
    s = me.state(AppState)
    if me.theme_brightness() == 'light':
        me.set_theme_mode('dark')
        s.theme_mode = 'dark'
    else:
        me.set_theme_mode('light')
        s.theme_mode = 'light'


def theme_toggle_icon(key: int, icon: str, text: str, min: bool = True):
    """Theme toggle icon"""
    # THEME_TOGGLE_STYLE = me.Style(position="absolute", bottom=50, align_content="left")
    if min:  # minimized
        with me.box(
            style=me.Style(
                display='flex',
                flex_direction='row',
                gap=5,
                align_items='center',
            ),
        ):
            with me.content_button(
                key=str(key),
                on_click=toggle_theme,
                # style=THEME_TOGGLE_STYLE,
                type='icon',
            ):
                with me.tooltip(message=text):
                    mui_icon('light_mode' if me.theme_brightness() == 'dark' else 'dark_mode')

    else:  # expanded
        with me.content_button(
            key=str(key),
            on_click=toggle_theme,
            # style=THEME_TOGGLE_STYLE,
        ):
            with me.box(
                style=me.Style(
                    display='flex',
                    flex_direction='row',
                    gap=5,
                    align_items='center',
                ),
            ):
                mui_icon('light_mode' if me.theme_brightness() == 'dark' else 'dark_mode')
                me.text(
                    'Light mode'
                    if me.theme_brightness() == 'dark'
                    else 'Dark mode'
                )


MENU_BOTTOM = me.Style(
    display='flex',
    flex_direction='column',
    position='absolute',
    bottom=8,
    align_content='left',
)