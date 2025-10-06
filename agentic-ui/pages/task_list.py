import mesop as me
from components.mui_icon import mui_icon

from components.task_card import task_card
from state.state import AppState
from styles.mbui_styles import (
    MBUI_HEADING_1_STYLE,
    MBUI_HEADING_1_STYLE_DARK,
    MBUI_CONTENT_PADDING_STYLE,
)


def task_list_page(app_state: AppState):
    """Task List Page with MBUI styling"""
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
                'task_alt',
                size=28,
                color=("#e8eaed" if is_dark else '#000000'),
                style=me.Style(
                    margin=me.Margin(top=-2),
                    padding=me.Padding(left=2, right=0, top=0, bottom=0),
                    overflow='visible',
                    vertical_align='baseline',
                ),
            )
            me.text(
                "Task List",
                style=MBUI_HEADING_1_STYLE_DARK if is_dark else MBUI_HEADING_1_STYLE,
            )
        
        task_card(app_state.task_list)