import mesop as me
import pandas as pd
from functools import partial

from state.host_agent_service import CreateConversation
from state.state import AppState, StateConversation
from components.dialog import dialog, dialog_actions
from state.host_agent_service import DeleteConversation, UpdateAppState
from components.mui_icon import mui_icon


@me.component
def conversation_list(conversations: list[StateConversation]):
    """Conversation list component"""
    df_data: dict[str, list[str | int]] = {
        'ID': [], 'Name': [], 'Status': [], 'Messages': [],
    }
    for conversation in conversations:
        df_data['ID'].append(conversation.conversation_id)
        df_data['Name'].append(conversation.conversation_name)
        df_data['Status'].append('Open' if conversation.is_active else 'Closed')
        df_data['Messages'].append(len(conversation.message_ids))
    df = pd.DataFrame(
        pd.DataFrame(df_data), columns=['ID', 'Name', 'Status', 'Messages']
    )
    with me.box(
        style=me.Style(
            display='flex',
            justify_content='space-between',
            flex_direction='column',
        )
    ):
        # Theme-aware colors
        app_state = me.state(AppState)
        effective_brightness = me.theme_brightness()
        is_dark = (
            app_state.theme_mode == 'dark'
            or (app_state.theme_mode == 'system' and effective_brightness == 'dark')
        )
        header_bg = '#3a3d42' if is_dark else '#f5f5f7'
        row_even = '#2f3136' if is_dark else '#ffffff'
        row_odd = '#36393f' if is_dark else '#fbfbfb'
        text_color = '#e8eaed' if is_dark else '#000000'
        divider_color = 'rgba(255,255,255,0.06)' if is_dark else 'rgba(0,0,0,0.04)'
        # Render a table-like list so we can add per-row actions (delete)
        # We render rows manually to match the agent list pattern for actions.
        # Header
        with me.box(style=me.Style(display='flex', gap=12, padding=me.Padding.symmetric(vertical=10, horizontal=12), background=header_bg)):
            with me.box(style=me.Style(flex=1)):
                me.text('ID', style=me.Style(color=text_color))
            with me.box(style=me.Style(flex=2)):
                me.text('Name', style=me.Style(color=text_color))
            with me.box(style=me.Style(flex=1)):
                me.text('Status', style=me.Style(color=text_color))
            with me.box(style=me.Style(flex=1)):
                me.text('Messages', style=me.Style(color=text_color))
            with me.box(style=me.Style(flex=1)):
                me.text('Actions', style=me.Style(color=text_color))

        # Handlers (hard-bound)
        def _open_confirm(e: me.ClickEvent, conversation_id: str, name: str):  # <- strictly bound values
            state = me.state(AppState)
            state.conversation_to_delete = conversation_id
            state.conversation_to_delete_name = name
            state.delete_dialog_open = True

        def _open(e: me.ClickEvent, conversation_id: str):  # <- strictly bound value
            state = me.state(AppState)
            state.current_conversation_id = conversation_id
            me.query_params.update({'conversation_id': conversation_id})
            me.navigate('/conversation', query_params=me.query_params)

        # Rows with actions
        for idx, conversation in enumerate(conversations):
            row_bg = row_even if idx % 2 == 0 else row_odd
            cid = conversation.conversation_id
            cname = conversation.conversation_name

            with me.box(
                key=f"row_{cid}",  # stable key
                style=me.Style(
                    display='flex',
                    gap=12,
                    align_items='center',
                    padding=me.Padding.symmetric(vertical=10, horizontal=12),
                    background=row_bg,
                )
            ):
                with me.box(style=me.Style(flex=1)):
                    me.text(cid, style=me.Style(color=text_color))
                with me.box(style=me.Style(flex=2)):
                    me.text(cname, style=me.Style(color=text_color))
                with me.box(style=me.Style(flex=1)):
                    me.text('Open' if conversation.is_active else 'Closed', style=me.Style(color=text_color))
                with me.box(style=me.Style(flex=1)):
                    me.text(str(len(conversation.message_ids)), style=me.Style(color=text_color))

                with me.box(style=me.Style(flex=1, display='flex', justify_content='center', gap=8)):
                    # Open button (bound)
                    with me.content_button(
                        type='raised',
                        on_click=partial(_open, conversation_id=cid),
                        key=f'open_conversation_{cid}',  # key uses id, not idx
                        style=me.Style(
                            padding=me.Padding.symmetric(vertical=6, horizontal=12),
                            min_width=80, border_radius=20, display='flex',
                            justify_content='center', color=text_color
                        ),
                    ):
                        mui_icon('open_in_new', color=text_color)

                    # Delete button
                    with me.content_button(
                        type='raised',
                        color='warn',
                        on_click=partial(_open_confirm, conversation_id=cid, name=cname),
                        key=f'delete_conversation_{cid}',  # key uses id, not idx
                        style=me.Style(
                            padding=me.Padding.symmetric(vertical=6, horizontal=12),
                            min_width=80, border_radius=20, display='flex',
                            justify_content='center', color=text_color
                        ),
                    ):
                        mui_icon('delete', color=text_color)

            with me.box(style=me.Style(height=1, background=divider_color)):  # divider
                pass

        # Add new conversation
        with me.content_button(
            type='raised',
            on_click=add_conversation,
            key='new_conversation',
            style=me.Style(
                display='flex',
                flex_direction='row',
                gap=5,
                align_items='center',
                margin=me.Margin(top=10),
            ),
        ):
            mui_icon('add')

        # Single global confirmation dialog (reads the bound ID from state)
        state = me.state(AppState)
        with dialog(state.delete_dialog_open):
            me.text(
                f"Delete conversation: {state.conversation_to_delete_name}?",
                style=me.Style(margin=me.Margin(bottom=10)),
            )
            with dialog_actions():
                def _confirm_delete(e: me.ClickEvent):  # pylint: disable=unused-argument
                    try:
                        import asyncio
                        cid = state.conversation_to_delete or ''
                        if not cid:
                            print('No conversation_to_delete set')
                            return
                        asyncio.run(DeleteConversation(cid))
                        asyncio.run(UpdateAppState(me.state(AppState), ''))
                    except Exception as ex:
                        print('Failed to delete conversation:', ex)
                    finally:
                        state.delete_dialog_open = False
                        state.conversation_to_delete = None
                        state.conversation_to_delete_name = None

                def _cancel_delete(e: me.ClickEvent):  # pylint: disable=unused-argument
                    state.delete_dialog_open = False
                    state.conversation_to_delete = None
                    state.conversation_to_delete_name = None

                me.button('Cancel', type='flat', on_click=_cancel_delete)
                with me.content_button(type='raised', color='warn', on_click=_confirm_delete):
                    me.text('Confirm')


async def add_conversation(e: me.ClickEvent):  # pylint: disable=unused-argument
    """Add conversation button handler"""
    response = await CreateConversation()
    me.state(AppState).messages = []
    me.navigate(
        '/conversation',
        query_params={'conversation_id': response.conversation_id},
    )
    yield


def on_click(e: me.TableClickEvent):
    # Navigation on table row click (unchanged)
    state = me.state(AppState)
    conversation = state.conversations[e.row_index]
    state.current_conversation_id = conversation.conversation_id
    me.query_params.update({'conversation_id': conversation.conversation_id})
    me.navigate('/conversation', query_params=me.query_params)
    yield
