import mesop as me

# CSC Design System
# Unified design tokens for consistent UI across all components

# Color Palette - CSC Blue Theme
CSC_COLORS = {
    # Primary CSC Blue
    'primary_blue': '#0066CC',
    'primary_blue_dark': '#004499',
    'primary_blue_light': '#3385D6',
    'primary_blue_hover': '#0052A3',
    
    # Secondary Colors
    'secondary_blue': '#1E88E5',
    'accent_blue': '#2196F3',
    
    # Neutral Colors
    'white': '#FFFFFF',
    'black': '#000000',
    'grey_50': '#FAFAFA',
    'grey_100': '#F5F5F5',
    'grey_200': '#EEEEEE',
    'grey_300': '#E0E0E0',
    'grey_400': '#BDBDBD',
    'grey_500': '#9E9E9E',
    'grey_600': '#757575',
    'grey_700': '#616161',
    'grey_800': '#424242',
    'grey_900': '#212121',
    
    # Dark Theme Colors
    'dark_bg_primary': '#1A1A1A',
    'dark_bg_secondary': '#2D2D2D',
    'dark_bg_tertiary': '#3A3A3A',
    'dark_text_primary': '#FFFFFF',
    'dark_text_secondary': '#E0E0E0',
    'dark_text_tertiary': '#BDBDBD',
    'dark_border': 'rgba(255,255,255,0.12)',
    
    # Status Colors
    'success': '#4CAF50',
    'warning': '#FF9800',
    'error': '#F44336',
    'info': '#2196F3',
}

# Table theme tokens (reusable across components)
TABLE_THEME = {
    'light': {
        'text_primary': '#0f0f0f',
        'text_secondary': '#4d4f52',
        'header_bg': '#f5f5f5',
        'row_even': '#ffffff',
        'row_odd': '#fafafa',
        'divider': 'rgba(0,0,0,0.08)',
    },
    'dark': {
        'text_primary': '#eaeaea',
        'text_secondary': '#cfd2d6',
        'header_bg': '#3a3a3a',
        'row_even': '#2f2f2f',
        'row_odd': '#262626',
        'divider': 'rgba(255,255,255,0.08)',
    },
}

def get_table_theme(is_dark: bool) -> dict:
    """Return table theme dictionary for given mode."""
    return TABLE_THEME['dark' if is_dark else 'light']

def is_dark_mode(app_state) -> bool:
    """Compute dark mode using app setting and system preference.

    Dark when:
    - theme_mode == 'dark', or
    - theme_mode == 'system' and system brightness is dark.
    """
    effective_brightness = me.theme_brightness()
    return (
        getattr(app_state, 'theme_mode', None) == 'dark'
        or (
            getattr(app_state, 'theme_mode', None) == 'system'
            and effective_brightness == 'dark'
        )
    )

# Typography System
CSC_TYPOGRAPHY = {
    'font_family_primary': '\"DaimlerCS\", \"MBCorpoATitle\", system-ui, -apple-system, \"Segoe UI\", Roboto, Helvetica, Arial, sans-serif',
    'font_family_mono': '"Roboto Mono", "Monaco", "Consolas", monospace',
    
    # Font Sizes
    'font_size_xs': '12px',
    'font_size_sm': '14px',
    'font_size_base': '16px',
    'font_size_lg': '18px',
    'font_size_xl': '20px',
    'font_size_2xl': '24px',
    'font_size_3xl': '30px',
    'font_size_4xl': '36px',
    
    # Font Weights
    'font_weight_normal': '400',
    'font_weight_medium': '500',
    'font_weight_semibold': '600',
    'font_weight_bold': '700',
    
    # Line Heights
    'line_height_tight': '1.25',
    'line_height_normal': '1.5',
    'line_height_relaxed': '1.75',
}

# Spacing System
CSC_SPACING = {
    'xs': '4px',
    'sm': '8px',
    'md': '16px',
    'lg': '24px',
    'xl': '32px',
    '2xl': '48px',
    '3xl': '64px',
}

# Border Radius
CSC_RADIUS = {
    'sm': '4px',
    'md': '8px',
    'lg': '12px',
    'xl': '16px',
    'full': '9999px',
}

# Shadows
CSC_SHADOWS = {
    'sm': '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
    'md': '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
    'lg': '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
    'xl': '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
}

# Component Styles

# Headings
CSC_HEADING_1 = me.Style(
    font_family=CSC_TYPOGRAPHY['font_family_primary'],
    font_size=CSC_TYPOGRAPHY['font_size_3xl'],
    font_weight=CSC_TYPOGRAPHY['font_weight_bold'],
    line_height=CSC_TYPOGRAPHY['line_height_tight'],
    margin=me.Margin(bottom=CSC_SPACING['lg']),
)

CSC_HEADING_1_DARK = me.Style(
    font_family=CSC_TYPOGRAPHY['font_family_primary'],
    font_size=CSC_TYPOGRAPHY['font_size_3xl'],
    font_weight=CSC_TYPOGRAPHY['font_weight_bold'],
    line_height=CSC_TYPOGRAPHY['line_height_tight'],
    color=CSC_COLORS['dark_text_primary'],
    margin=me.Margin(bottom=CSC_SPACING['lg']),
)

CSC_HEADING_2 = me.Style(
    font_family=CSC_TYPOGRAPHY['font_family_primary'],
    font_size=CSC_TYPOGRAPHY['font_size_2xl'],
    font_weight=CSC_TYPOGRAPHY['font_weight_semibold'],
    line_height=CSC_TYPOGRAPHY['line_height_tight'],
    margin=me.Margin(bottom=CSC_SPACING['md']),
)

CSC_HEADING_3 = me.Style(
    font_family=CSC_TYPOGRAPHY['font_family_primary'],
    font_size=CSC_TYPOGRAPHY['font_size_xl'],
    font_weight=CSC_TYPOGRAPHY['font_weight_semibold'],
    line_height=CSC_TYPOGRAPHY['line_height_normal'],
    margin=me.Margin(bottom=CSC_SPACING['sm']),
)

# Body Text
CSC_BODY_TEXT = me.Style(
    font_family=CSC_TYPOGRAPHY['font_family_primary'],
    font_size=CSC_TYPOGRAPHY['font_size_base'],
    font_weight=CSC_TYPOGRAPHY['font_weight_normal'],
    line_height=CSC_TYPOGRAPHY['line_height_normal'],
)

CSC_BODY_TEXT_SM = me.Style(
    font_family=CSC_TYPOGRAPHY['font_family_primary'],
    font_size=CSC_TYPOGRAPHY['font_size_sm'],
    font_weight=CSC_TYPOGRAPHY['font_weight_normal'],
    line_height=CSC_TYPOGRAPHY['line_height_normal'],
)

CSC_CAPTION_TEXT = me.Style(
    font_family=CSC_TYPOGRAPHY['font_family_primary'],
    font_size=CSC_TYPOGRAPHY['font_size_xs'],
    font_weight=CSC_TYPOGRAPHY['font_weight_normal'],
    line_height=CSC_TYPOGRAPHY['line_height_normal'],
    color=CSC_COLORS['grey_600'],
)

# Buttons
CSC_BUTTON_PRIMARY = me.Style(
    background=CSC_COLORS['primary_blue'],
    color=CSC_COLORS['white'],
    border=me.Border.all(me.BorderSide(width=0)),
    border_radius=CSC_RADIUS['md'],
    padding=me.Padding(top=12, bottom=12, left=24, right=24),
    font_family=CSC_TYPOGRAPHY['font_family_primary'],
    font_weight=CSC_TYPOGRAPHY['font_weight_medium'],
    font_size=CSC_TYPOGRAPHY['font_size_sm'],
    cursor='pointer',
)

CSC_BUTTON_SECONDARY = me.Style(
    background='transparent',
    color=CSC_COLORS['primary_blue'],
    border=me.Border.all(me.BorderSide(color=CSC_COLORS['primary_blue'], width=1)),
    border_radius=CSC_RADIUS['md'],
    padding=me.Padding(top=12, bottom=12, left=24, right=24),
    font_family=CSC_TYPOGRAPHY['font_family_primary'],
    font_weight=CSC_TYPOGRAPHY['font_weight_medium'],
    font_size=CSC_TYPOGRAPHY['font_size_sm'],
    cursor='pointer',
)

CSC_BUTTON_GHOST = me.Style(
    background='transparent',
    color=CSC_COLORS['grey_700'],
    border=me.Border.all(me.BorderSide(width=0)),
    border_radius=CSC_RADIUS['md'],
    padding=me.Padding(top=12, bottom=12, left=16, right=16),
    font_family=CSC_TYPOGRAPHY['font_family_primary'],
    font_weight=CSC_TYPOGRAPHY['font_weight_medium'],
    font_size=CSC_TYPOGRAPHY['font_size_sm'],
    cursor='pointer',
)

# Cards
CSC_CARD = me.Style(
    background=CSC_COLORS['white'],
    border=me.Border.all(me.BorderSide(color=CSC_COLORS['grey_200'], width=1)),
    border_radius=CSC_RADIUS['lg'],
    box_shadow=CSC_SHADOWS['sm'],
    padding=me.Padding.all(CSC_SPACING['lg']),
)

CSC_CARD_DARK = me.Style(
    background=CSC_COLORS['dark_bg_secondary'],
    border=me.Border.all(me.BorderSide(color=CSC_COLORS['dark_border'], width=1)),
    border_radius=CSC_RADIUS['lg'],
    box_shadow=CSC_SHADOWS['sm'],
    padding=me.Padding.all(CSC_SPACING['lg']),
)

# Tables
CSC_TABLE_HEADER = me.Style(
    background=CSC_COLORS['grey_50'],
    border=me.Border(bottom=me.BorderSide(color=CSC_COLORS['grey_200'], width=1)),
    padding=me.Padding(top=16, bottom=16, left=16, right=16),
    font_family=CSC_TYPOGRAPHY['font_family_primary'],
    font_size=CSC_TYPOGRAPHY['font_size_sm'],
    font_weight=CSC_TYPOGRAPHY['font_weight_semibold'],
    color=CSC_COLORS['grey_700'],
)

CSC_TABLE_HEADER_DARK = me.Style(
    background=CSC_COLORS['dark_bg_tertiary'],
    border=me.Border(bottom=me.BorderSide(color=CSC_COLORS['dark_border'], width=1)),
    padding=me.Padding(top=16, bottom=16, left=16, right=16),
    font_family=CSC_TYPOGRAPHY['font_family_primary'],
    font_size=CSC_TYPOGRAPHY['font_size_sm'],
    font_weight=CSC_TYPOGRAPHY['font_weight_semibold'],
    color=CSC_COLORS['dark_text_secondary'],
)

CSC_TABLE_CELL = me.Style(
    border=me.Border(bottom=me.BorderSide(color=CSC_COLORS['grey_200'], width=1)),
    padding=me.Padding(top=16, bottom=16, left=16, right=16),
    font_family=CSC_TYPOGRAPHY['font_family_primary'],
    font_size=CSC_TYPOGRAPHY['font_size_sm'],
    font_weight=CSC_TYPOGRAPHY['font_weight_normal'],
    color=CSC_COLORS['grey_800'],
)

CSC_TABLE_CELL_DARK = me.Style(
    border=me.Border(bottom=me.BorderSide(color=CSC_COLORS['dark_border'], width=1)),
    padding=me.Padding(top=16, bottom=16, left=16, right=16),
    font_family=CSC_TYPOGRAPHY['font_family_primary'],
    font_size=CSC_TYPOGRAPHY['font_size_sm'],
    font_weight=CSC_TYPOGRAPHY['font_weight_normal'],
    color=CSC_COLORS['dark_text_primary'],
)

# Inputs
CSC_INPUT = me.Style(
    border=me.Border.all(me.BorderSide(color=CSC_COLORS['grey_300'], width=1)),
    border_radius=CSC_RADIUS['md'],
    padding=me.Padding(top=12, bottom=12, left=16, right=16),
    font_family=CSC_TYPOGRAPHY['font_family_primary'],
    font_size=CSC_TYPOGRAPHY['font_size_base'],
    font_weight=CSC_TYPOGRAPHY['font_weight_normal'],
    background=CSC_COLORS['white'],
    width='100%',
)

# Starter Questions
CSC_STARTER_QUESTION = me.Style(
    background=CSC_COLORS['grey_50'],
    color=CSC_COLORS['grey_800'],
    border=me.Border.all(me.BorderSide(color=CSC_COLORS['grey_200'], width=1)),
    border_radius=CSC_RADIUS['xl'],
    padding=me.Padding(top=16, bottom=16, left=20, right=20),
    font_family=CSC_TYPOGRAPHY['font_family_primary'],
    font_size=CSC_TYPOGRAPHY['font_size_sm'],
    font_weight=CSC_TYPOGRAPHY['font_weight_medium'],
    cursor='pointer',
    min_height='48px',
    max_width='280px',
    display='flex',
    align_items='center',
    justify_content='center',
    text_align='center',
    line_height=CSC_TYPOGRAPHY['line_height_normal'],
)

CSC_STARTER_QUESTION_DARK = me.Style(
    background=CSC_COLORS['dark_bg_secondary'],
    color=CSC_COLORS['dark_text_primary'],
    border=me.Border.all(me.BorderSide(color=CSC_COLORS['dark_border'], width=1)),
    border_radius=CSC_RADIUS['xl'],
    padding=me.Padding(top=16, bottom=16, left=20, right=20),
    font_family=CSC_TYPOGRAPHY['font_family_primary'],
    font_size=CSC_TYPOGRAPHY['font_size_sm'],
    font_weight=CSC_TYPOGRAPHY['font_weight_medium'],
    cursor='pointer',
    min_height='48px',
    max_width='280px',
    display='flex',
    align_items='center',
    justify_content='center',
    text_align='center',
    line_height=CSC_TYPOGRAPHY['line_height_normal'],
)

# Layout
CSC_CONTAINER = me.Style(
    max_width='1200px',
    margin=me.Margin(left=0, right=0),
    padding=me.Padding(left=CSC_SPACING['lg'], right=CSC_SPACING['lg']),
)

CSC_FLEX_ROW = me.Style(
    display='flex',
    flex_direction='row',
    align_items='center',
    gap=CSC_SPACING['md'],
)

CSC_FLEX_COLUMN = me.Style(
    display='flex',
    flex_direction='column',
    gap=CSC_SPACING['md'],
)
