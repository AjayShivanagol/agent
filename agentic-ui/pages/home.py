import mesop as me
from components.mui_icon import mui_icon

from components.conversation_list import conversation_list
from components.poller import polling_buttons
from state.state import AppState
from styles.mbui_styles import MBUI_HEADING_1_STYLE, MBUI_HEADING_1_STYLE_DARK, MBUI_CONTENT_PADDING_STYLE


@me.stateclass
class PageState:
    """Local Page State"""

    temp_name: str = ''


def on_blur_set_name(e: me.InputBlurEvent):
    """Input handler"""
    state = me.state(PageState)
    state.temp_name = e.value


def on_enter_change_name(e: me.components.input.input.InputEnterEvent):  # pylint: disable=unused-argument
    """Change name button handler"""
    state = me.state(PageState)
    app_state = me.state(AppState)
    app_state.name = state.temp_name
    app_state.greeting = ''  # reset greeting
    yield


def on_click_change_name(e: me.ClickEvent):  # pylint: disable=unused-argument
    """Change name button handler"""
    state = me.state(PageState)
    app_state = me.state(AppState)
    app_state.name = state.temp_name
    app_state.greeting = ''  # reset greeting
    yield


def home_page_content(app_state: AppState):
    """Home Page with MBUI styling"""
    with me.box(style=MBUI_CONTENT_PADDING_STYLE):
        # Page title with MBUI styling
        effective_brightness = me.theme_brightness()
        is_dark = (
            app_state.theme_mode == 'dark'
            or (app_state.theme_mode == 'system' and effective_brightness == 'dark')
        )
        with me.box(
            style=me.Style(
                display='flex',
                flex_direction='row',
                align_items='center',
                justify_content='space-between',
                gap=8,
            )
        ):
            # Left: title group
            with me.box(
                style=me.Style(
                    display='flex',
                    flex_direction='row',
                    align_items='baseline',
                    gap=8,
                )
            ):
                mui_icon(
                    'chat',
                    size=25,
                    color=("#e8eaed" if is_dark else '#000000'),
                    style=me.Style(
                        margin=me.Margin(top=0),
                        padding=me.Padding(left=2, right=0, top=0, bottom=0),
                        overflow='visible',
                        vertical_align='baseline',
                    ),
                )
                me.text(
                    "Conversations",
                    style=MBUI_HEADING_1_STYLE_DARK if is_dark else MBUI_HEADING_1_STYLE,
                )
            # Right: polling controls
            polling_buttons()
        
        # Conversations list
        conversation_list(app_state.conversations)

        # Spacer
        me.box(style=me.Style(height=16))

        # Simple list of Conversation IDs below (removed)

        def _open_conv(e: me.ClickEvent):  # pylint: disable=unused-argument
            s = me.state(AppState)
            conv_id = e.key or ''
            if not conv_id:
                return
            s.current_conversation_id = conv_id
            me.query_params.update({'conversation_id': conv_id})
            me.navigate('/conversation', query_params=me.query_params)