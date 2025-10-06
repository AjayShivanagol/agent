import mesop as me
from state.state import AppState


@me.content_component
def dialog(is_open: bool):
    # Get app state for theme detection
    app_state = me.state(AppState)
    effective_brightness = me.theme_brightness()
    is_dark = (
        app_state.theme_mode == 'dark'
        or (app_state.theme_mode == 'system' and effective_brightness == 'dark')
    )
    
    # Use consistent gray background for dark theme dialogs
    dialog_bg = "#3a3a3a" if is_dark else me.theme_var('background')
    
    with me.box(
        style=me.Style(
            background='rgba(0,0,0,0.5)',
            display='block' if is_open else 'none',
            height='100vh',
            width='100vw',
            position='fixed',
            top='0',
            left='0',
            z_index=1300,  # closer to MUI modal z-index
        )
    ):
        with me.box(
            style=me.Style(
                align_items='center',
                display='grid',
                height='100vh',
                justify_items='center',
            )
        ):
            with me.box(
                style=me.Style(
                    background=dialog_bg,
                    border_radius=12,
                    box_sizing='border-box',
                    box_shadow=(
                        '0px 11px 15px -7px rgba(0,0,0,0.2), '
                        '0px 24px 38px 3px rgba(0,0,0,0.14), '
                        '0px 9px 46px 8px rgba(0,0,0,0.12)'
                    ),
                    # Avoid string-based 'auto' margins; the parent grid already centers content
                    margin=me.Margin(top=0, bottom=0, left=0, right=0),
                    padding=me.Padding(top=24, bottom=24, left=24, right=24),
                    width='100%',
                    max_width=600,
                    min_width=320,
                    max_height='80vh',
                    overflow_y='auto',
                )
            ):
                me.slot()


@me.content_component
def dialog_actions():
    with me.box(
        style=me.Style(
            display='flex',
            justify_content='end',
            gap=12,
            margin=me.Margin(top=20),
        )
    ):
        me.slot()
