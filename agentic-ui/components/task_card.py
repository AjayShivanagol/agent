import json

import mesop as me
import pandas as pd

from state.state import ContentPart, SessionTask, StateTask
from state.state import AppState
from styles.design_system import get_table_theme, is_dark_mode, CSC_TYPOGRAPHY


def message_string(content: ContentPart) -> str:
    if isinstance(content, str):
        return content
    return json.dumps(content)


@me.component
def task_card(tasks: list[SessionTask]):
    """Task card component"""
    columns = ['Conversation ID', 'Task ID', 'Description', 'Status', 'Output']
    df_data: dict[str, list[str]] = dict([(c, []) for c in columns])
    # Sort tasks latest-first: prefer timestamp fields if available; fallback to reverse order
    try:
        def _ts(t: SessionTask):
            st = t.task
            # Try common timestamp fields on task/status
            return (
                getattr(st, 'updated_at', None)
                or getattr(st, 'created_at', None)
                or getattr(getattr(st, 'status', object()), 'timestamp', None)
                or 0
            )
        tasks_iter = sorted(tasks, key=_ts, reverse=True)
    except Exception:
        tasks_iter = list(tasks)[::-1]
    for task in tasks_iter:
        df_data['Conversation ID'].append(task.context_id)
        df_data['Task ID'].append(task.task.task_id or '')
        df_data['Description'].append(
            '\n'.join(message_string(x[0]) for x in task.task.message.content)
        )
        df_data['Status'].append(task.task.state)
        df_data['Output'].append(flatten_artifacts(task.task))
    df = pd.DataFrame(pd.DataFrame(df_data), columns=columns)
    # Theme-aware colors (respect system preference when selected)
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
                me.text('Task ID')
            with me.box(style=me.Style(flex=3)):
                me.text('Description')
            with me.box(style=me.Style(flex=1)):
                me.text('Status')
            with me.box(style=me.Style(flex=3)):
                me.text('Output')

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
                    me.text(str(row['Task ID']))
                with me.box(style=me.Style(flex=3)):
                    desc = str(row['Description']).strip()
                    desc = (desc[:140] + '…') if len(desc) > 140 else desc
                    me.text(desc, style=me.Style(color=text_secondary))
                with me.box(style=me.Style(flex=1)):
                    me.text(str(row['Status']))
                with me.box(style=me.Style(flex=3)):
                    out = str(row['Output']).strip()
                    out = (out[:140] + '…') if len(out) > 140 else out
                    me.text(out, style=me.Style(color=text_secondary))


def flatten_artifacts(task: StateTask) -> str:
    parts = []
    for a in task.artifacts:
        for p in a:
            if p[1] == 'text/plain' or p[1] == 'application/json':
                parts.append(message_string(p[0]))
            else:
                parts.append(p[1])

    return '\n'.join(parts)
