import asyncio

import mesop as me
import mesop.labs as mel
import os
import time
from components.mui_icon import mui_icon

from components.agent_list import agents_list
from components.dialog import dialog, dialog_actions
from state.agent_state import AgentState
from state.host_agent_service import AddRemoteAgent, ListRemoteAgents
from state.state import AppState
from styles.mbui_styles import (
    MBUI_HEADING_1_STYLE,
    MBUI_HEADING_1_STYLE_DARK,
    MBUI_CONTENT_PADDING_STYLE,
)
from utils.agent_card import get_agent_card
from styles.design_system import CSC_TYPOGRAPHY


def agent_list_page(app_state: AppState):
    """Agents List Page with MBUI styling"""
    state = me.state(AgentState)
    with me.box(style=MBUI_CONTENT_PADDING_STYLE):
        # Theme-aware icon + text header
        effective_brightness = me.theme_brightness()
        is_dark = (
            app_state.theme_mode == 'dark'
            or (app_state.theme_mode == 'system' and effective_brightness == 'dark')
        )
        with me.box(
            style=me.Style(
                display='flex',
                flex_direction='row',
                align_items='baseline',
                gap=8,
            )
        ):
            mui_icon(
                'smart_toy',
                size=28,
                color=("#e8eaed" if is_dark else '#000000'),
                style=me.Style(
                    margin=me.Margin(top=-1),
                    padding=me.Padding(left=2, right=0, top=0, bottom=0),
                    overflow='visible',
                    vertical_align='baseline',
                ),
            )
            me.text(
                "Remote Agents",
                style=MBUI_HEADING_1_STYLE_DARK if is_dark else MBUI_HEADING_1_STYLE,
            )
            agents = asyncio.run(ListRemoteAgents())

            # This box will grow to push the link to the right
            with me.box(style=me.Style(flex_grow=1)):
                pass

            me.link(
                text="Agent Garden",
                url="https://backstage.i.mercedes-benz.com/aiecosystem/agentgarden",
                open_in_new_tab=True,
                style=me.Style(
                    # MUI contained button-like styling
                    display="inline-flex",
                    align_items="center",
                    justify_content="center",
                    text_decoration="none",
                    cursor="pointer",
                    font_family=CSC_TYPOGRAPHY['font_family_primary'],
                    font_weight="500",
                    font_size=14,  # 0.875rem
                    line_height=1.75,
                    letter_spacing="0.02857em",
                    min_width=64,
                    padding=me.Padding(left=16, right=16, top=6, bottom=6),
                    border_radius=4,
                    color=("rgb(26, 26, 26)" if is_dark else "#ffffff"),
                    background=("rgb(144, 202, 249)" if is_dark else "#1976d2"),
                ),
            )

        agents_list(agents)
        with dialog(state.agent_dialog_open):
            with me.box(
                style=me.Style(
                    display='flex', flex_direction='column', gap=12
                )
            ):
                me.input(
                    label='Agent Address',
                    on_blur=set_agent_address,
                    placeholder='localhost:10000',
                )
                input_modes_string = ', '.join(state.input_modes)
                output_modes_string = ', '.join(state.output_modes)

                if state.error != '':
                    me.text(state.error, style=me.Style(color='red'))
                if state.agent_name != '':
                    me.text(f'Agent Name: {state.agent_name}')
                if state.agent_description:
                    me.text(f'Agent Description: {state.agent_description}')
                if state.agent_framework_type:
                    me.text(
                        f'Agent Framework Type: {state.agent_framework_type}'
                    )
                if state.input_modes:
                    me.text(f'Input Modes: {input_modes_string}')
                if state.output_modes:
                    me.text(f'Output Modes: {output_modes_string}')

                if state.agent_name:
                    me.text(
                        f'Streaming Supported: {state.stream_supported}'
                    )
                    me.text(
                        f'Push Notifications Supported: {state.push_notifications_supported}'
                    )
            with dialog_actions():
                # Cancel on the left as flat button
                me.button('Cancel', type='flat', on_click=cancel_agent_dialog)
                # Primary action on the right as raised button
                if not state.agent_name:
                    with me.content_button(type='raised', on_click=load_agent_info):
                        me.text('Read')
                elif not state.error:
                    with me.content_button(type='raised', on_click=save_agent):
                        me.text('Save')


def set_agent_address(e: me.InputBlurEvent):
    state = me.state(AgentState)
    state.agent_address = e.value


def load_agent_info(e: me.ClickEvent):
    state = me.state(AgentState)
    try:
        state.error = None
        agent_card_response = get_agent_card(state.agent_address)
        state.agent_name = agent_card_response.name
        state.agent_description = agent_card_response.description
        state.agent_framework_type = (
            agent_card_response.provider.organization
            if agent_card_response.provider
            else ''
        )
        state.input_modes = agent_card_response.defaultInputModes
        state.output_modes = agent_card_response.defaultOutputModes
        state.stream_supported = agent_card_response.capabilities.streaming
        state.push_notifications_supported = (
            agent_card_response.capabilities.pushNotifications
        )
    except Exception as e:
        print(e)
        state.agent_name = None
        state.error = f'Cannot connect to agent as {state.agent_address}'


def cancel_agent_dialog(e: me.ClickEvent):
    state = me.state(AgentState)
    state.agent_dialog_open = False


async def save_agent(e: me.ClickEvent):
    state = me.state(AgentState)
    await AddRemoteAgent(state.agent_address)
    state.agent_address = ''
    state.agent_name = ''
    state.agent_description = ''
    state.agent_dialog_open = False
    # Refresh the page so the newly added agent appears immediately
    me.navigate('/agents')
