import asyncio

import mesop as me
from components.mui_icon import mui_icon

from state.host_agent_service import UpdateApiKey
from state.state import AppState, SettingsState
from styles.mbui_styles import (
    MBUI_HEADING_1_STYLE,
    MBUI_HEADING_1_STYLE_DARK,
    MBUI_CONTENT_PADDING_STYLE,
    MBUI_CARD_STYLE,
)


def on_selection_change_output_types(e: me.SelectSelectionChangeEvent):
    s = me.state(SettingsState)
    s.output_mime_types = e.values


def on_api_key_change(e: me.InputBlurEvent):
    s = me.state(AppState)
    s.api_key = e.value


@me.stateclass
class UpdateStatus:
    """Status for API key update"""

    show_success: bool = False


async def update_api_key(e: me.ClickEvent):
    yield  # Allow UI to update

    state = me.state(AppState)
    update_status = me.state(UpdateStatus)

    if state.api_key.strip():
        success = await UpdateApiKey(state.api_key)
        if success:
            update_status.show_success = True

            # Hide success message after 3 seconds
            yield
            await asyncio.sleep(3)
            update_status.show_success = False

    yield  # Allow UI to update after operation completes


def settings_page_content():
    """Settings Page Content with MBUI styling."""
    settings_state = me.state(SettingsState)
    app_state = me.state(AppState)
    update_status = me.state(UpdateStatus)

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
                gap=8
            )
        ):
            mui_icon(
                'settings',
                size=25,
                color=("#e8eaed" if is_dark else '#000000'),
                style=me.Style(
                    line_height='1.1',
                    margin=me.Margin(top=-2),
                    vertical_align='baseline',
                    padding=me.Padding(left=2, right=0, top=0, bottom=0),
                    overflow='visible',
                ),
            )
            me.text(
                "Settings",
                style=(MBUI_HEADING_1_STYLE_DARK if is_dark else MBUI_HEADING_1_STYLE),
            )
        
        with me.box(
            style=me.Style(
                display='flex',
                justify_content='space-between',
                flex_direction='column',
                gap=30,
            )
        ):
            # API Key Settings Section
            if not app_state.uses_vertex_ai:
                with me.box(
                    style=me.Style(
                        display='flex',
                        flex_direction='column',
                        margin=me.Margin(bottom=30),
                    )
                ):
                    me.text(
                        'Google API Key',
                        type='headline-6',
                        style=me.Style(
                            margin=me.Margin(bottom=15),
                            font_family='Google Sans',
                        ),
                    )

                    with me.box(
                        style=me.Style(
                            display='flex',
                            flex_direction='row',
                            gap=10,
                            align_items='center',
                            margin=me.Margin(bottom=5),
                        )
                    ):
                        me.input(
                            label='API Key',
                            value=app_state.api_key,
                            on_blur=on_api_key_change,
                            type='password',
                            appearance='outline',
                            style=me.Style(width='400px'),
                        )

                        me.button(
                            'Update',
                            type='raised',
                            on_click=update_api_key,
                            style=me.Style(
                                color=me.theme_var('primary'),
                            ),
                        )

                    # Success message
                    if update_status.show_success:
                        with me.box(
                            style=me.Style(
                                background=me.theme_var(
                                    'success-container'
                                ),
                                padding=me.Padding(
                                    top=10, bottom=10, left=10, right=10
                                ),
                                border_radius=4,
                                margin=me.Margin(top=10),
                                display='flex',
                                flex_direction='row',
                                align_items='center',
                                width='400px',
                            )
                        ):
                            mui_icon(
                                'check_circle',
                                color=me.theme_var('on-success-container'),
                                style=me.Style(
                                    margin=me.Margin(right=10),
                                ),
                            )
                            me.text(
                                'API Key updated successfully',
                                style=me.Style(
                                    color=me.theme_var(
                                        'on-success-container'
                                    ),
                                ),
                            )

                    # Add spacing instead of divider with style
                    with me.box(
                        style=me.Style(margin=me.Margin(top=10, bottom=10))
                    ):
                        me.divider()

            # Output Types Section
            me.select(
                label='Supported Output Types',
                options=[
                    me.SelectOption(label='Image', value='image/*'),
                    me.SelectOption(
                        label='Text (Plain)', value='text/plain'
                    ),
                ],
                on_selection_change=on_selection_change_output_types,
                style=me.Style(width=500),
                multiple=True,
                appearance='outline',
                value=settings_state.output_mime_types,
            )