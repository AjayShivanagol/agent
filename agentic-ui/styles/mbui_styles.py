import mesop as me

# Mercedes-Benz Color Palette
MBUI_COLORS = {
    # Primary Colors
    'primary_black': '#000000',
    'primary_white': '#FFFFFF',
    'primary_silver': '#C0C0C0',
    
    # Secondary Colors
    'secondary_blue': '#1e3c72',
    'secondary_blue_light': '#2a5298',
    'secondary_grey': '#424242',
    'secondary_grey_light': '#757575',
    
    # Background Colors
    'background_primary': '#FFFFFF',
    'background_secondary': '#F5F5F5',
    'background_tertiary': '#FAFAFA',
    'background_dark': '#000000',
    
    # Text Colors
    'text_primary': '#000000',
    'text_secondary': '#424242',
    'text_tertiary': '#757575',
    'text_inverse': '#FFFFFF',
    'text_muted': 'rgba(0,0,0,0.6)',
    
    # Border Colors
    'border_light': 'rgba(0,0,0,0.12)',
    'border_medium': 'rgba(0,0,0,0.23)',
    'border_dark': 'rgba(0,0,0,0.42)',
    'border_inverse': 'rgba(255,255,255,0.23)',
    
    # Status Colors
    'success': '#4CAF50',
    'warning': '#FF9800',
    'error': '#F44336',
    'info': '#2196F3',
}

# Mercedes-Benz Typography
MBUI_TYPOGRAPHY = {
    'font_family_primary': '"DaimlerCS", "Mercedes-Benz Corporate A", "Roboto", "Helvetica", "Arial", sans-serif',
    'font_family_secondary': '"DaimlerCS", "Roboto", "Helvetica", "Arial", sans-serif',
    'font_family_mono': '"Roboto Mono", "Monaco", "Consolas", monospace',
}

# Mercedes-Benz Component Styles
MBUI_HEADER_STYLE = me.Style(
    background=MBUI_COLORS['primary_black'],
    height="64px",
    display="flex",
    align_items="center",
    justify_content="space-between",
    padding=me.Padding(left=24, right=24),
    box_shadow="0px 2px 4px -1px rgba(0,0,0,0.2), 0px 4px 5px 0px rgba(0,0,0,0.14), 0px 1px 10px 0px rgba(0,0,0,0.12)",
    position="fixed",
    top="0",
    left="0",
    right="0",
    z_index=1100
)

MBUI_FOOTER_STYLE = me.Style(
    background=MBUI_COLORS['primary_black'],
    color=MBUI_COLORS['primary_white'],
    padding=me.Padding(top=64, bottom=32, left=24, right=24),
    # Avoid string-based margins; use numeric values and flex layout for placement
    margin=me.Margin(top=0),
    border=me.Border(top=me.BorderSide(color="rgba(255,255,255,0.15)", width=1))
)

MBUI_CARD_STYLE = me.Style(
    background=MBUI_COLORS['background_primary'],
    border_radius="8px",
    box_shadow="0 2px 8px rgba(0,0,0,0.1)",
    padding=me.Padding(top=24, bottom=24, left=24, right=24),
    margin=me.Margin(bottom=16)
)

MBUI_BUTTON_PRIMARY_STYLE = me.Style(
    background=MBUI_COLORS['primary_black'],
    color=MBUI_COLORS['primary_white'],
    border=me.Border.all(me.BorderSide(width=0)),
    border_radius="4px",
    padding=me.Padding(top=12, bottom=12, left=24, right=24),
    font_family=MBUI_TYPOGRAPHY['font_family_secondary'],
    font_weight="500",
    font_size="14px",
    text_transform="uppercase",
    letter_spacing="0.5px"
)

MBUI_BUTTON_SECONDARY_STYLE = me.Style(
    background="transparent",
    color=MBUI_COLORS['primary_black'],
    border=me.Border.all(me.BorderSide(color=MBUI_COLORS['border_medium'], width=1)),
    border_radius="4px",
    padding=me.Padding(top=12, bottom=12, left=24, right=24),
    font_family=MBUI_TYPOGRAPHY['font_family_secondary'],
    font_weight="500",
    font_size="14px",
    text_transform="uppercase",
    letter_spacing="0.5px"
)

MBUI_INPUT_STYLE = me.Style(
    border=me.Border.all(me.BorderSide(color=MBUI_COLORS['border_medium'], width=1)),
    border_radius="4px",
    padding=me.Padding(top=12, bottom=12, left=16, right=16),
    font_family=MBUI_TYPOGRAPHY['font_family_secondary'],
    font_size="16px",
    background=MBUI_COLORS['background_primary']
)

MBUI_HEADING_1_STYLE = me.Style(
    font_family=MBUI_TYPOGRAPHY['font_family_primary'],
    font_size="32px",
    font_weight="600",
    color=MBUI_COLORS['text_primary'],
    line_height="1.2",
    letter_spacing="0.5px",
    margin=me.Margin(bottom=24)
)

# Dark variant for H1 headings
MBUI_HEADING_1_STYLE_DARK = me.Style(
    font_family=MBUI_TYPOGRAPHY['font_family_primary'],
    font_size="32px",
    font_weight="600",
    color="#e8eaed",
    line_height="1.2",
    letter_spacing="0.5px",
    margin=me.Margin(bottom=24)
)

MBUI_HEADING_2_STYLE = me.Style(
    font_family=MBUI_TYPOGRAPHY['font_family_primary'],
    font_size="24px",
    font_weight="600",
    color=MBUI_COLORS['text_primary'],
    line_height="1.3",
    letter_spacing="0.5px",
    margin=me.Margin(bottom=16)
)

MBUI_HEADING_3_STYLE = me.Style(
    font_family=MBUI_TYPOGRAPHY['font_family_primary'],
    font_size="20px",
    font_weight="500",
    color=MBUI_COLORS['text_primary'],
    line_height="1.4",
    letter_spacing="0.25px",
    margin=me.Margin(bottom=12)
)

MBUI_BODY_TEXT_STYLE = me.Style(
    font_family=MBUI_TYPOGRAPHY['font_family_secondary'],
    font_size="16px",
    font_weight="400",
    color=MBUI_COLORS['text_primary'],
    line_height="1.5"
)

MBUI_CAPTION_TEXT_STYLE = me.Style(
    font_family=MBUI_TYPOGRAPHY['font_family_secondary'],
    font_size="14px",
    font_weight="400",
    color=MBUI_COLORS['text_secondary'],
    line_height="1.4"
)

# Layout Styles
MBUI_CONTAINER_STYLE = me.Style(
    max_width="1200px",
    # Remove 'auto' margins; rely on parent container for centering
    margin=me.Margin(left=0, right=0),
    padding=me.Padding(left=24, right=24)
)

MBUI_GRID_STYLE = me.Style(
    display="grid",
    grid_template_columns="repeat(auto-fit, minmax(300px, 1fr))",
    gap="24px"
)

MBUI_FLEX_ROW_STYLE = me.Style(
    display="flex",
    flex_direction="row",
    align_items="center",
    gap="16px"
)

MBUI_FLEX_COLUMN_STYLE = me.Style(
    display="flex",
    flex_direction="column",
    gap="16px"
)

# Navigation Styles
SIDENAV_MIN_WIDTH = 68
SIDENAV_MAX_WIDTH = 200

MBUI_SIDENAV_STYLE = me.Style(
    background=MBUI_COLORS['background_secondary'],
    border=me.Border(right=me.BorderSide(color=MBUI_COLORS['border_light'], width=1)),
    height="100vh",
    position="fixed",
    top="64px",  # Account for header height
    left="0",
    z_index=1000
)

# Page Layout Styles
MBUI_PAGE_CONTAINER_STYLE = me.Style(
    display='flex',
    flex_direction='column',
    min_height='100vh',
    background=me.theme_var('background')
)

MBUI_MAIN_CONTENT_STYLE = me.Style(
    flex="1",
    display="flex",
    flex_direction="column",
    background=me.theme_var('surface'),
    margin=me.Margin(top=16, bottom=16, left=16, right=16),
    border_radius="8px",
    box_shadow="0 2px 8px rgba(0,0,0,0.1)",
    overflow="hidden"
)

MBUI_CONTENT_PADDING_STYLE = me.Style(
    padding=me.Padding(top=24, bottom=24, left=24, right=24),
    overflow_y="auto"
)