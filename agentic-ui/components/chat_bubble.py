import mesop as me
from components.mui_icon import mui_icon
from components.data_table import render_table_content
from state.state import AppState, StateMessage
from styles.design_system import CSC_COLORS, CSC_TYPOGRAPHY

@me.component
def chat_bubble(message: StateMessage, key: str):
    """Chat bubble component"""
    app_state = me.state(AppState)
    show_progress_bar = (
        message.message_id in app_state.background_tasks
        or message.message_id in app_state.message_aliases.values()
    )
    progress_text = ''
    if show_progress_bar:
        progress_text = app_state.background_tasks.get(message.message_id, '')
    if not message.content:
        print('No message content')
    for pair in message.content:
        chat_box(
            pair[0],
            pair[1],
            message.role,
            key,
            progress_bar=show_progress_bar,
            progress_text=progress_text,
        )

def chat_box(
    content: str,
    media_type: str,
    role: str,
    key: str,
    progress_bar: bool,
    progress_text: str,
):
    # Full-width row; align to left for agent, right for user (UNCHANGED)
    with me.box(
        style=me.Style(
            display='flex',
            justify_content=('flex-start' if role == 'agent' else 'flex-end'),
            width='100%',
            margin=me.Margin(top=6, bottom=6),
        ),
        key=key,
    ):
        # Message line: avatar + bubble (agent) or bubble + avatar (user)
        with me.box(
            style=me.Style(
                display='flex',
                flex_direction='row',
                align_items='center',  # keep as-is per request
                gap=12,
                max_width='100%',
            )
        ):
            def avatar():
                with me.box(
                    style=me.Style(
                        width='36px',
                        height='36px',
                        border_radius='50%',
                        display='grid',
                        align_items='center',
                        justify_items='center',
                        align_self=('flex-end' if role == 'agent' else 'flex-start'),
                        flex='0 0 auto',
                        background=(
                            me.theme_var('secondary-container') if role == 'agent' else me.theme_var('surface-variant')
                        ),
                        box_shadow='0 1px 2px rgba(0,0,0,0.12)',
                        transform=('translateY(4px)' if role == 'agent' else 'translateY(-4px)'),
                    )
                ):
                    mui_icon(
                        ('smart_toy' if role == 'agent' else 'account_circle'),
                        size=20,
                        color=me.theme_var('on-secondary-container' if role == 'agent' else 'on-surface-variant'),
                        style=me.Style(
                            display='block',
                            margin=me.Margin(top=0, right=0, bottom=0, left=0),
                        ),
                    )
            def bubble():
                # container only for local layout; no growth
                with me.box(style=me.Style(display='flex', flex_direction='column', gap=5, flex='0 1 auto')):
                    if media_type == 'image/png':
                        if '/message/file' not in content:
                            content_img = 'data:image/png;base64,' + content
                        else:
                            content_img = content
                        me.image(
                            src=content_img,
                            style=me.Style(
                                width='50%',
                                object_fit='contain',
                                border_radius=(
                                    '16px 16px 16px 0px' if role == 'agent' else '16px 0px 16px 16px'
                                ),
                                margin=me.Margin(top=0, bottom=0, left=0, right=0),
                                # keep avatar stuck to bubble; do not let bubble grow
                                display='inline-flex',
                                flex='0 1 auto',
                                align_self=('flex-end' if role == 'user' else 'auto'),
                            ),
                        )
                    else:
                        # Wrap markdown in a container to guarantee consistent rounded corners
                        with me.box(
                            style=me.Style(
                                font_family=CSC_TYPOGRAPHY['font_family_primary'],
                                box_shadow=(
                                    '0 4px 12px rgba(60,64,67,0.18), '
                                    '0 2px 4px rgba(60,64,67,0.12)'
                                ),
                                background=me.theme_var('surface'),
                                color=me.theme_var('on-surface'),
                                border_radius=(
                                    '16px 16px 16px 0px' if role == 'agent' else '16px 0px 16px 16px'
                                ),
                                overflow='hidden',
                                # Maximum width for tables - nearly full screen
                                max_width='min(1500px, 98%)',
                                width='auto',
                                display='inline-flex',
                                flex='0 1 auto',
                                align_self=('flex-end' if role == 'user' else 'auto'),
                            )
                        ):
                            # Check if content contains table data and render accordingly
                            render_table_content(
                                content, 
                                key=f"{key}_content"
                            )
            if role == 'agent':
                avatar()
                bubble()
            else:
                bubble()
                avatar()
    if progress_bar:
        # Always render progress as agent-side (assistant is working)
        p_role = 'agent'
        # Mirror layout of main bubble with avatar
        with me.box(
            style=me.Style(
                display='flex',
                justify_content=('flex-start' if p_role == 'agent' else 'flex-end'),
                width='100%',
                margin=me.Margin(top=6, bottom=0),
            ),
            key=key + '-progress',
        ):
            with me.box(
                style=me.Style(
                    display='flex',
                    flex_direction='row',
                    align_items='center',
                    gap=6,
                    max_width='min(780px, 90%)',
                )
            ):
                def progress_avatar():
                    with me.box(
                        style=me.Style(
                            width='28px',
                            height='28px',
                            border_radius='50%',
                            display='grid',
                            align_items='center',
                            justify_items='center',
                            align_self=('flex-end' if p_role == 'agent' else 'flex-start'),
                            flex='0 0 auto',
                            background=(
                                me.theme_var('secondary-container') if p_role == 'agent' else me.theme_var('surface-variant')
                            ),
                            transform=('translateY(4px)' if p_role == 'agent' else 'translateY(-4px)'),
                        )
                    ):
                        mui_icon(
                            ('smart_toy' if p_role == 'agent' else 'account_circle'),
                            size=18,
                            color=me.theme_var('on-secondary-container' if p_role == 'agent' else 'on-surface-variant'),
                            style=me.Style(
                                display='block',
                                margin=me.Margin(top=0, right=0, bottom=0, left=0),
                            ),
                        )
                def progress_bubble():
                    with me.box(
                        style=me.Style(
                            font_family=CSC_TYPOGRAPHY['font_family_primary'],
                            font_size=CSC_TYPOGRAPHY['font_size_base'],
                            line_height=CSC_TYPOGRAPHY['line_height_normal'],
                            box_shadow=(
                                '0 4px 12px rgba(60,64,67,0.18), '
                                '0 2px 4px rgba(60,64,67,0.12)'
                            ),
                            padding=me.Padding(top=12, left=18, right=18, bottom=12),
                            margin=me.Margin(top=0, left=0, right=0, bottom=0),
                            background=me.theme_var('surface'),
                            color=me.theme_var('on-surface'),
                            border_radius=(
                                '16px 16px 16px 0px' if p_role == 'agent' else '16px 0px 16px 16px'
                            ),
                            overflow='hidden',
                            max_width='min(680px, 100%)',
                            display='inline-flex',
                            flex='0 1 auto',
                            align_self='flex-end',  # keep progress bubble near avatar baseline
                        ),
                    ):
                        progress_text_local = progress_text or 'Working...'
                        me.text(progress_text_local)
                        me.progress_bar(color='accent')
                if p_role == 'agent':
                    progress_avatar()
                    progress_bubble()
                else:
                    progress_bubble()
                    progress_avatar()