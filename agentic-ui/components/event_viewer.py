import asyncio
from typing import Tuple

import mesop as me
import pandas as pd

from state.host_agent_service import GetEvents
from state.host_agent_service import convert_event_to_state
from state.state import AppState
from styles.design_system import get_table_theme, is_dark_mode, CSC_TYPOGRAPHY


def flatten_content(content: list[tuple[str, str]]) -> str:
    parts = []
    for p in content:
        if p[1] == 'text/plain' or p[1] == 'application/json':
            parts.append(p[0])
        else:
            parts.append(p[1])

    return '\n'.join(parts)


@me.component
def event_list():
    """Events list component"""
    df_data = {
        'Conversation ID': [],
        'Actor': [],
        'Role': [],
        'Id': [],
        'Overview': [],
        'Content': [],
    }
    events = asyncio.run(GetEvents())
    # Sort latest first (descending by timestamp); fallback to 0 if missing
    try:
        events = sorted(events, key=lambda ev: getattr(ev, 'timestamp', 0), reverse=True)
    except Exception:
        pass
    for e in events:
        event = convert_event_to_state(e)
        df_data['Conversation ID'].append(event.context_id)
        df_data['Role'].append(event.role)
        df_data['Id'].append(event.id)
        df_data['Overview'].append(event.overview)
        df_data['Content'].append(flatten_content(event.content))
        df_data['Actor'].append(event.actor)
    if not df_data['Conversation ID']:
        me.text('No events found')
        return
    df = pd.DataFrame(
        df_data,
        columns=['Conversation ID', 'Actor', 'Role', 'Id', 'Overview', 'Content'],
    )
    # Theme-aware colors (shared with Task List)
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
                me.text('Conversation ID')
            with me.box(style=me.Style(flex=1)):
                me.text('Actor')
            with me.box(style=me.Style(flex=1)):
                me.text('Role')
            with me.box(style=me.Style(flex=1)):
                me.text('Id')
            with me.box(style=me.Style(flex=3)):
                me.text('Overview')
            with me.box(style=me.Style(flex=4)):
                me.text('Content')

        # Rows
        for idx, (_, row) in enumerate(df.iterrows()):
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
                    me.text(str(row['Conversation ID']))
                with me.box(style=me.Style(flex=1)):
                    me.text(str(row['Actor']))
                with me.box(style=me.Style(flex=1)):
                    me.text(str(row['Role']))
                with me.box(style=me.Style(flex=1)):
                    me.text(str(row['Id']))
                with me.box(style=me.Style(flex=3)):
                    overview = str(row['Overview']).strip()
                    # Show overview prominently
                    me.text(
                        overview if overview else 'No overview available', 
                        style=me.Style(
                            color=text_primary,
                            font_weight='500'
                        )
                    )
                with me.box(style=me.Style(flex=4)):
                    content = str(row['Content']).strip()
                    # Truncate long content for readability
                    content = (content[:150] + '…') if len(content) > 150 else content
                    me.text(content, style=me.Style(color=text_secondary))
