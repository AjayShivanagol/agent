import mesop as me
import mesop.labs as mel

from state.host_agent_service import UpdateAppState
from state.state import AppState
from .async_poller import AsyncAction, async_poller
from .mb_header import mb_header, mb_header_spacer
from .mb_footer import mb_footer
from .side_nav import sidenav
from styles.styles import SIDENAV_MAX_WIDTH, SIDENAV_MIN_WIDTH


async def refresh_app_state(e: mel.WebEvent):  # pylint: disable=unused-argument
    """Refresh app state event handler"""
    yield
    app_state = me.state(AppState)
    await UpdateAppState(app_state, app_state.current_conversation_id)
    yield


@me.content_component
def mbui_page_scaffold():
    """Mercedes-Benz UI Page Scaffold Component"""
    app_state = me.state(AppState)
    action = (
        AsyncAction(
            value=app_state, duration_seconds=app_state.polling_interval
        )
        if app_state
        else None
    )
    async_poller(action=action, trigger_event=refresh_app_state)

    # Mercedes-Benz Header (fixed at top)
    mb_header()
    
    # Side navigation
    sidenav('')

    # Main content area with proper spacing for header and sidebar
    with me.box(
        style=me.Style(
            display='flex',
            flex_direction='column',
            min_height='100vh',
            margin=me.Margin(
                left=SIDENAV_MAX_WIDTH
                if app_state.sidenav_open
                else SIDENAV_MIN_WIDTH,
            ),
            background=me.theme_var('background')
        ),
    ):
        # Header spacer to account for fixed header
        mb_header_spacer()
        
        # Main content container
        effective_brightness = me.theme_brightness()
        is_dark = (
            app_state.theme_mode == 'dark'
            or (app_state.theme_mode == 'system' and effective_brightness == 'dark')
        )
        # Softer dark background and base text color for content container
        content_bg = "#2f3136" if is_dark else "#ffffff"
        base_text = "#e8eaed" if is_dark else "#000000"
        with me.box(
            style=me.Style(
                flex="1",
                display="flex",
                flex_direction="column",
                background=content_bg,
                color=base_text,
                margin=me.Margin(left=16, right=16, top=16, bottom=16),
                border_radius="8px",
                box_shadow="0 2px 8px rgba(0,0,0,0.1)",
                overflow="hidden"
            )
        ):
            # Content slot
            with me.box(
                style=me.Style(
                    flex="1",
                    padding=me.Padding(top=24, bottom=24, left=24, right=24),
                    overflow_y="auto"
                )
            ):
                me.slot()
        
        # Mercedes-Benz Footer (conditionally shown)
        if app_state.show_footer:
            mb_footer()


@me.content_component
def mbui_page_frame():
    """Mercedes-Benz UI Page Frame for content"""
    with me.box(
        style=me.Style(
            display='flex',
            flex_direction='column',
            height='100%',
            background="#ffffff"
        )
    ):
        me.slot()


@me.content_component
def mbui_content_container():
    """Mercedes-Benz UI Content Container with proper spacing"""
    with me.box(
        style=me.Style(
            display="flex",
            flex_direction="column",
            gap="24px",
            max_width="1200px",
            margin=me.Margin.symmetric(horizontal="auto"),
            width="100%"
        )
    ):
        me.slot()