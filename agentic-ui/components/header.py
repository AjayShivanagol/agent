import mesop as me
from components.mui_icon import mui_icon
from styles.design_system import CSC_TYPOGRAPHY

from .poller import polling_buttons


@me.content_component
def header(title: str, icon: str):
    """Header component"""
    with me.box(
        style=me.Style(
            display='flex',
            justify_content='space-between',
        )
    ):
        with me.box(
            style=me.Style(display='flex', flex_direction='row', gap=5)
        ):
            mui_icon(icon)
            me.text(
                title,
                type='headline-5',
                style=me.Style(font_family=CSC_TYPOGRAPHY['font_family_primary']),
            )
        me.slot()
        polling_buttons()
