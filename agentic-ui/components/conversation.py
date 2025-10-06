import mesop as me

import uuid
from functools import partial

from state.state import AppState, SettingsState, StateMessage
from state.host_agent_service import (
    SendMessage,
    ListConversations,
    convert_message_to_state,
)
from styles.styles import SIDENAV_MAX_WIDTH, SIDENAV_MIN_WIDTH
from styles.design_system import is_dark_mode
from .chat_bubble import chat_bubble
from components.mui_icon import mui_icon
from .scroll_bottom import scroll_bottom
from .form_render import is_form, render_form, form_sent
from a2a.types import Message, TextPart, Part, Role
from state.host_agent_service import (
    ListConversations,
    SendMessage,
    convert_message_to_state,
)
from state.host_agent_service import CreateConversation
from state.state import AppState, SettingsState, StateMessage

from .chat_bubble import chat_bubble
from .form_render import form_sent, is_form, render_form


async def suggestion_click_handler(e: me.ClickEvent, question_text: str):
    """Handle suggestion click with specific question text."""
    yield
    app_state = me.state(AppState)
    message_id = str(uuid.uuid4())
    app_state.background_tasks[message_id] = ''
    await send_message(question_text, message_id)
    yield


@me.stateclass
class PageState:
    """Local Page State"""

    conversation_id: str = ''
    message_content: str = ''


def on_blur(e: me.InputBlurEvent):
    """Input handler"""
    state = me.state(PageState)
    state.message_content = e.value


def on_change(e):
    """Live-update input handler so clicking the button without blurring still sends the latest text."""
    state = me.state(PageState)
    state.message_content = e.value


async def send_message(message: str, message_id: str = ''):
    state = me.state(PageState)
    app_state = me.state(AppState)
    c = next(
        (
            x
            for x in await ListConversations()
            if x.conversation_id == state.conversation_id
        ),
        None,
    )
    if not c:
        # Auto-create a conversation when none is found or id is empty
        try:
            new_conv = await CreateConversation()
            if new_conv and new_conv.conversation_id:
                state.conversation_id = new_conv.conversation_id
                app_state.current_conversation_id = new_conv.conversation_id
                c = new_conv
            else:
                print('Failed to auto-create conversation')
        except Exception as e:
            print('Error creating conversation: ', e)
    request = Message(
        messageId=message_id,
        contextId=state.conversation_id,
        role=Role.user,
        parts=[Part(root=TextPart(text=message))],
    )
    # Add message to state until refresh replaces it.
    state_message = convert_message_to_state(request)
    if not app_state.messages:
        app_state.messages = []
    app_state.messages.append(state_message)
    conversation = next(
        filter(
            lambda x: c and x.conversation_id == c.conversation_id,
            app_state.conversations,
        ),
        None,
    )
    if conversation:
        conversation.message_ids.append(state_message.message_id)
    
    await SendMessage(request)


async def send_message_enter(e: me.InputEnterEvent):  # pylint: disable=unused-argument
    """Send message handler"""
    yield
    state = me.state(PageState)
    state.message_content = e.value
    app_state = me.state(AppState)
    message_id = str(uuid.uuid4())
    app_state.background_tasks[message_id] = ''
    yield
    await send_message(state.message_content, message_id)
    yield
    # Clear input after successful send
    state.message_content = ''
    yield


async def send_message_button(e: me.ClickEvent):  # pylint: disable=unused-argument
    """Send message button handler"""
    yield
    state = me.state(PageState)
    app_state = me.state(AppState)
    message_id = str(uuid.uuid4())
    app_state.background_tasks[message_id] = ''
    # Use the current state value (kept updated via on_change/on_blur)
    await send_message(state.message_content, message_id)
    # Clear input after successful send
    state.message_content = ''
    yield


@me.component
def conversation():
    """Conversation component"""
    page_state = me.state(PageState)
    app_state = me.state(AppState)
    if 'conversation_id' in me.query_params:
        page_state.conversation_id = me.query_params['conversation_id']
        app_state.current_conversation_id = page_state.conversation_id
    
    # Determine effective theme for adaptive styling
    is_dark = is_dark_mode(app_state)

    # Base container background (should match scaffold content)
    container_bg = '#2f3136' if is_dark else '#FFFFFF'

    # Dark/light palette for bottom bar and chips (match container)
    input_bar_bg = container_bg
    input_bar_border = 'rgba(255,255,255,0.12)' if is_dark else '#E0E0E0'
    input_text = '#e8eaed' if is_dark else '#1A1A1A'
    placeholder_text = 'rgba(232,234,237,0.7)' if is_dark else 'rgba(0,0,0,0.6)'
    # Chips: in dark, match container; in light, use a subtle grey to be visible on white
    chip_bg = (container_bg if is_dark else '#F7F7F8')
    chip_text = '#e8eaed' if is_dark else '#1A1A1A'
    # Stronger border in dark mode for visibility; clearer grey in light
    chip_border = 'rgba(255,255,255,0.5)' if is_dark else '#D0D5DD'
    chip_border_width = 2 if is_dark else 1
    chip_shadow = (
        '0 0 0 1px rgba(255,255,255,0.20)'
        if is_dark
        else '0 0 0 1px rgba(0,0,0,0.08)'
    )
    # Theme-aware primary accent
    primary_blue = 'rgb(0, 141, 252)' if is_dark else 'rgb(0, 120, 214)'

    # Main container - use available height within scaffold
    with me.box(
        style=me.Style(
            display='flex',
            flex_direction='column',
            height='100%',  # Use full height of parent container instead of viewport
            position='relative',
        )
    ):
        # Scrollable conversation area
        with me.box(
            style=me.Style(
                flex='1',
                overflow_y='auto',
                padding=me.Padding(bottom=120),  # Leave space for input area
                display='flex',
                flex_direction='column',
            )
        ):
            for message in app_state.messages:
                if is_form(message):
                    render_form(message, app_state)
                elif form_sent(message, app_state):
                    chat_bubble(
                        StateMessage(
                            message_id=message.message_id,
                            role=message.role,
                            content=[('Form submitted', 'text/plain')],
                        ),
                        message.message_id,
                    )
                else:
                    chat_bubble(message, message.message_id)
            # Auto-scroll to bottom whenever message count changes
            scroll_bottom(key=f'scroll-{len(app_state.messages)}')
        
        # Fixed input area at bottom - account for sidebar
        with me.box(
            style=me.Style(
                position='fixed',
                bottom='0',
                # Align with content container: sidebar width + 16px inset
                left=(SIDENAV_MAX_WIDTH if app_state.sidenav_open else SIDENAV_MIN_WIDTH) + 16,
                right=16,
                background=input_bar_bg,
                padding=me.Padding(top=16, bottom=16, left=16, right=8),  # Reduce right padding for more input space
                border=me.Border(top=me.BorderSide(color=input_bar_border, width=1)),
                z_index=1000,
            )
        ):
            # Keep suggestion chips mounted even after first message to avoid handler-id drift
            # Toggle visibility instead of unmounting/remounting
            show_suggestions = not app_state.messages
            with me.box(
                style=me.Style(
                    display='flex' if show_suggestions else 'none',
                    flex_direction='column',
                    gap=8,
                    padding=me.Padding.symmetric(horizontal=16, vertical=0),
                )
            ):
                me.text(
                    'Choose a starter question or ask your own:',
                    style=me.Style(font_weight='600', color=chip_text)
                )
                with me.box(
                    style=me.Style(
                        display='flex',
                        flex_direction='row',
                        flex_wrap='wrap',
                        gap=8,
                        margin=me.Margin(bottom=16),
                        align_items='flex-start',
                        justify_content='flex-start',
                    )
                ):
                    for idx, q in enumerate(me.state(AppState).suggested_questions):
                        with me.content_button(
                            type='flat',
                            on_click=partial(suggestion_click_handler, question_text=q),
                            key=f'suggest-q-{idx}',
                            style=me.Style(
                                background=chip_bg,
                                color=chip_text,
                                padding=me.Padding.symmetric(horizontal=20, vertical=16),
                                border_radius=12,
                                border=me.Border.all(me.BorderSide(color=chip_border, width=chip_border_width)),
                                box_shadow=chip_shadow,
                                justify_content='center',
                                align_items='center',
                                max_width=280,
                                min_height=60,
                                cursor='pointer',
                            ),
                        ):
                            me.text(
                                q,
                                style=me.Style(
                                    text_align='center',
                                    white_space='normal',
                                    line_height='20px',
                                    font_size=14,
                                    color=chip_text,
                                ),
                            )

            with me.box(
                style=me.Style(
                    display='flex',
                    flex_direction='row',
                    align_items='center',
                    gap=6,
                    width='100%',
                    max_width='none',
                    margin=me.Margin.symmetric(horizontal=0),
                )
            ):
                # Wrap input in a flex item that controls width; some components size to parent
                with me.box(
                    style=me.Style(
                        flex='1 1 0%',
                        min_width='0',
                        width='100%',
                        max_width='100%',
                    )
                ):
                    me.input(
                        label='How can I help you?',
                        value=page_state.message_content,
                        on_blur=on_blur,
                        on_enter=send_message_enter,
                        style=me.Style(
                            width='100%',
                            max_width='100%',
                            box_sizing='border-box',
                            background=input_bar_bg,
                            color=input_text,
                            border=me.Border.all(me.BorderSide(color=primary_blue, width=1)),
                        ),
                    )
                with me.content_button(
                    type='flat',
                    on_click=send_message_button,
                    style=me.Style(
                        margin=me.Margin(left=6, right=0, top=0, bottom=0),
                        background='transparent',
                        box_shadow='none',
                        border=me.Border.all(me.BorderSide(color='transparent', width=0)),
                        padding=me.Padding.all(0),
                        min_width='44px',
                        width='44px',
                        flex='0 0 auto',
                    )
                ):
                    mui_icon(
                        'send',
                        color=primary_blue,
                        size=24,  # match increased height for crispness
                        style=me.Style(width='32px', height='30px')  # wider icon, transparent button
                    )
