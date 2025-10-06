import mesop as me
from components.mui_icon import mui_icon
import pandas as pd

from a2a.types import AgentCard
from state.agent_state import AgentState
from state.state import AppState
from state.host_agent_service import DeleteRemoteAgent
from components.dialog import dialog, dialog_actions
from styles.design_system import get_table_theme, is_dark_mode, CSC_TYPOGRAPHY
import asyncio


@me.component
def agents_list(
    agents: list[AgentCard],
):
    """Agents list component."""
    df_data: dict[str, list[str | bool | None]] = {
        'Address': [],
        'Name': [],
        'Description': [],
        'Organization': [],
        'Input Modes': [],
        'Output Modes': [],
        'Streaming': [],
    }
    for agent_info in agents:
        df_data['Address'].append(agent_info.url)
        df_data['Name'].append(agent_info.name)
        df_data['Description'].append(agent_info.description)
        df_data['Organization'].append(
            agent_info.provider.organization if agent_info.provider else ''
        )
        df_data['Input Modes'].append(', '.join(agent_info.defaultInputModes))
        df_data['Output Modes'].append(', '.join(agent_info.defaultOutputModes))
        df_data['Streaming'].append(agent_info.capabilities.streaming)
    df = pd.DataFrame(
        pd.DataFrame(df_data),
        columns=[
            'Address',
            'Name',
            'Description',
            'Organization',
            'Input Modes',
            'Output Modes',
            'Streaming',
        ],
    )
    # Theme-aware colors
    app_state = me.state(AppState)
    is_dark = is_dark_mode(app_state)
    theme = get_table_theme(is_dark)
    container_bg = '#2d2d2d' if is_dark else '#ffffff'
    text_primary = theme['text_primary']
    text_secondary = theme['text_secondary']
    header_bg = theme['header_bg']
    row_even = theme['row_even']
    row_odd = theme['row_odd']
    divider_color = theme['divider']
    # Container
    with me.box(
        style=me.Style(
            background=container_bg,
            color=text_primary,
            font_family=CSC_TYPOGRAPHY['font_family_primary'],
            border_radius=8,
            overflow='hidden',
            border=me.Border.all(me.BorderSide(color=divider_color, width=1)),
        )
    ):
        # Header
        with me.box(
            style=me.Style(
                display='flex',
                gap=12,
                padding=me.Padding.symmetric(vertical=10, horizontal=12),
                background=header_bg,
                position='sticky',
                top=0,
                z_index=1,
            )
        ):
            with me.box(style=me.Style(flex=2)):
                me.text('Address')
            with me.box(style=me.Style(flex=1)):
                me.text('Name')
            with me.box(style=me.Style(flex=2)):
                me.text('Description')
            with me.box(style=me.Style(flex=1)):
                me.text('Organization')
            with me.box(style=me.Style(flex=1)):
                me.text('Input Modes')
            with me.box(style=me.Style(flex=1)):
                me.text('Output Modes')
            with me.box(style=me.Style(flex=1)):
                me.text('Streaming')
            with me.box(style=me.Style(flex=1)):
                me.text('Actions')

    # No inline edit — remote agents are read-only

        def _delete_factory(url: str, name: str):
            def _open_confirm(e: me.ClickEvent):  # pylint: disable=unused-argument
                state = me.state(AgentState)
                state.agent_to_delete = url
                state.agent_to_delete_name = name
                state.delete_dialog_open = True

            return _open_confirm

        # Rows
        for idx, agent_info in enumerate(agents):
            # extract fields
            address = agent_info.url
            name = agent_info.name
            description = agent_info.description
            organization = agent_info.provider.organization if agent_info.provider else ''
            input_modes = ', '.join(agent_info.defaultInputModes)
            output_modes = ', '.join(agent_info.defaultOutputModes)
            streaming = 'Yes' if agent_info.capabilities.streaming else 'No'

            # Per-row style: alternating background for separation
            row_bg = row_even if idx % 2 == 0 else row_odd
            with me.box(
                style=me.Style(
                    display='flex',
                    gap=12,
                    align_items='flex-start',
                    padding=me.Padding.symmetric(vertical=10, horizontal=12),
                    background=row_bg,
                    border=me.Border(bottom=me.BorderSide(color=divider_color, width=1)),
                )
            ):
                with me.box(style=me.Style(flex=2)):
                    me.text(address)
                with me.box(style=me.Style(flex=1)):
                    me.text(name)
                with me.box(style=me.Style(flex=2)):
                    me.text(description)
                with me.box(style=me.Style(flex=1)):
                    me.text(organization)
                with me.box(style=me.Style(flex=1)):
                    me.text(input_modes)
                with me.box(style=me.Style(flex=1)):
                    me.text(output_modes)
                with me.box(style=me.Style(flex=1)):
                    me.text(streaming)
                with me.box(style=me.Style(flex=1, display='flex', justify_content='center', gap=8)):
                    # Use icon-only content buttons for a compact, visible control
                    # No edit button (remote agents are read-only)

                    with me.content_button(
                        type='raised',
                        color='warn',
                        on_click=_delete_factory(address, name),
                        key=f'delete_agent_{idx}',
                        style=me.Style(padding=me.Padding.symmetric(vertical=6, horizontal=12), min_width=80, border_radius=20, display='flex', justify_content='center'),
                    ):
                        mui_icon('delete')
                # row divider
                with me.box(style=me.Style(height=1, background=divider_color)):
                    pass

    # Add agent button below the table
        with me.content_button(
            type='raised',
            on_click=add_agent,
            key='new_agent',
            style=me.Style(
                display='flex',
                flex_direction='row',
                gap=5,
                align_items='center',
                margin=me.Margin(top=10),
            ),
        ):
            mui_icon('upload')

        # confirmation dialog for deletion
        state = me.state(AgentState)
        with dialog(state.delete_dialog_open):
            me.text(
                f"Delete agent: {state.agent_to_delete_name}?",
                style=me.Style(margin=me.Margin(bottom=10)),
            )
            with dialog_actions():
                def _confirm_delete(e: me.ClickEvent):  # pylint: disable=unused-argument
                    try:
                        asyncio.run(DeleteRemoteAgent(state.agent_to_delete))
                    except Exception as ex:
                        # If already deleted elsewhere, proceed to refresh anyway
                        print('Delete agent warning:', ex)
                    finally:
                        state.delete_dialog_open = False
                        state.agent_to_delete = None
                        me.navigate('/agents')

                def _cancel_delete(e: me.ClickEvent):  # pylint: disable=unused-argument
                    state.delete_dialog_open = False
                    state.agent_to_delete = None

                me.button('Cancel', type='flat', on_click=_cancel_delete)
                with me.content_button(type='raised', color='warn', on_click=_confirm_delete):
                    me.text('Confirm')

    # No edit dialog — remote agents are read-only


def add_agent(e: me.ClickEvent):  # pylint: disable=unused-argument
    """Import agent button handler."""
    state = me.state(AgentState)
    state.agent_dialog_open = True
