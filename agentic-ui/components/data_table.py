import mesop as me
import re
from typing import List, Dict, Any, Optional, Callable
from functools import partial

from styles.design_system import (
    CSC_COLORS, 
    CSC_TYPOGRAPHY, 
    CSC_SPACING, 
    CSC_RADIUS,
    is_dark_mode,
    get_table_theme
)
from components.mui_icon import mui_icon
from state.state import AppState


def normalize_cell_value(cell_value: str) -> str:
    """Generic cell value normalization."""
    if not cell_value or cell_value.upper() in ['NULL', 'N/A', '-']:
        return ''
    
    # Remove extra whitespace and clean up
    cell_value = cell_value.strip()
    
    # Remove trailing numeric suffixes that might be formatting artifacts
    # This handles cases like "A0004641900 0064" -> "A0004641900"
    cell_value = re.sub(r'\s+\d{4}$', '', cell_value)
    
    return cell_value


def _looks_code_like(token: str) -> bool:
    """Heuristic to detect codes like material numbers, plant codes, numeric IDs."""
    if not token:
        return False
    if any(ch.isdigit() for ch in token) and len(token) >= 3:
        return True
    return bool(re.match(r'[A-Z]{1,4}\d{3,}', token))


def is_valid_table(headers: List[str], rows: List[List[str]]) -> bool:
    """Final gate to decide if parsed content is truly a table.

    Protects against narrative paragraphs being split into faux columns.
    """
    if not headers or not rows:
        return False
    if len(headers) < 2:
        return False
    # Sample up to first 8 rows
    sample = rows[:8]
    total_cells = 0
    dash_cells = 0
    empty_cells = 0
    codeish_cells = 0
    text_cells = 0
    for r in sample:
        for c in r[:len(headers)]:
            total_cells += 1
            cell = (c or '').strip()
            if not cell:
                empty_cells += 1
            if cell == '-':
                dash_cells += 1
            if _looks_code_like(cell):
                codeish_cells += 1
            # Treat multi-word long strings with punctuation as text
            if len(cell.split()) >= 4 or any(p in cell for p in ['.', ',', '!', '?']):
                text_cells += 1

    # If too many filler dashes, likely not a real table
    if total_cells > 0 and (dash_cells / total_cells) > 0.5:
        return False
    # Require at least some "code-like" evidence across sampled rows
    if codeish_cells == 0 and len(sample) >= 2:
        return False
    # If overwhelmingly narrative text, not a table
    if total_cells > 0 and (text_cells / total_cells) > 0.5:
        return False
    return True


def is_likely_table_content(lines: List[str], start_idx: int) -> bool:
    """Validate if content is actually tabular data vs regular text."""
    if start_idx >= len(lines):
        return False
        
    # Look at next few lines to see if they have consistent structure
    table_like_lines = 0
    total_lines_checked = 0
    digit_tokens_total = 0
    
    for i in range(start_idx, min(start_idx + 5, len(lines))):
        line = lines[i].strip()
        if not line:
            continue
        
        total_lines_checked += 1
        words = line.split()
        # Basic sentence-like detection: long sentences with punctuation and very few numbers
        has_sentence_punct = any(p in line for p in ['.', ',', '!', '?'])
        digit_tokens = sum(1 for w in words if any(ch.isdigit() for ch in w))
        digit_tokens_total += digit_tokens
        # Stopword ratio check to detect natural language
        stopwords = {
            'the','and','or','but','with','from','can','how','you','this','that','there','was','were','is','are','an','a','it','seems','which','might','be','due','to','please','check','again','later','if','any','other','need','further','assistance','feel','free','ask'
        }
        stopword_ratio = sum(1 for w in words if w.lower() in stopwords) / max(len(words), 1)
        
        # Check for table-like characteristics:
        # 1. Multiple short words/codes (not long sentences)
        # 2. Contains numbers or codes
        # 3. Consistent word count
        looks_structured = (
            len(words) >= 3 and
            any(any(ch.isdigit() for ch in word) or len(word) <= 15 for word in words) and
            not any(len(word) > 25 for word in words)
        )

        # If line strongly resembles a narrative sentence, don't count as table-like
        if has_sentence_punct and stopword_ratio >= 0.35 and digit_tokens == 0:
            continue

        if looks_structured:
            table_like_lines += 1
    
    # Require at least some numeric/code evidence across sampled lines
    if digit_tokens_total == 0 and table_like_lines <= 1:
        return False

    # At least 60% of lines should look table-like
    return total_lines_checked > 0 and (table_like_lines / total_lines_checked) >= 0.6


def detect_table_format(lines: List[str]) -> tuple[str, int]:
    """Enhanced table detection that distinguishes tables from regular text."""
    markdown_candidates = []
    space_separated_candidates = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line or line.startswith('**'):
            continue
            
        # Check for markdown table format (multiple | characters)
        if '|' in line and line.count('|') >= 2:
            # Count non-empty cells to validate it's a real table
            cells = [cell.strip() for cell in line.split('|') if cell.strip()]
            if len(cells) >= 2:  # At least 2 columns
                # Validate this is actually tabular content
                if is_likely_table_content(lines, i):
                    markdown_candidates.append((i, len(cells)))
                
        # Check for space-separated format with stricter validation
        elif len(line.split()) >= 3:  # At least 3 columns
            # Additional early filters to avoid natural sentences
            words = line.split()
            has_punct = any(p in line for p in ['.', ',', '!', '?'])
            has_any_digit = any(any(ch.isdigit() for ch in w) for w in words)
            # Code-like token patterns (e.g., A0000150400, U0000000139020000, 3010)
            code_like = any(re.match(r'[A-Z]{1,3}\d{3,}', w) or re.match(r'\d{3,}', w) for w in words)
            # Look for lines that could be headers but validate table structure
            if (
                any(c.isalpha() for c in line)
                and is_likely_table_content(lines, i)
                and (has_any_digit or code_like)
                and not has_punct  # avoid typical sentence punctuation
            ):
                space_separated_candidates.append((i, len(line.split())))
    
    # Prefer markdown format if we found consistent candidates
    if markdown_candidates:
        # Find the most consistent markdown table (same column count)
        column_counts = {}
        for idx, count in markdown_candidates:
            column_counts[count] = column_counts.get(count, 0) + 1
        
        if column_counts:
            most_common_count = max(column_counts, key=column_counts.get)
            for idx, count in markdown_candidates:
                if count == most_common_count:
                    return 'markdown', idx
    
    # Fall back to space-separated if we found candidates
    if space_separated_candidates:
        return 'space_separated', space_separated_candidates[0][0]
            
    return 'unknown', 0


def validate_and_clean_row(row: List[str], headers: List[str]) -> List[str]:
    """Generic row validation and cleaning that works with any column structure."""
    cleaned_row = []
    
    for i, cell in enumerate(row):
        if i >= len(headers):
            break
            
        # Generic cell normalization
        cell_value = normalize_cell_value(cell) if cell else ''
        cleaned_row.append(cell_value)
    
    # Ensure row has same length as headers
    while len(cleaned_row) < len(headers):
        cleaned_row.append('')
        
    return cleaned_row


def calculate_column_flex(headers: List[str], rows: List[List[str]]) -> List[int]:
    """Calculate flexible column sizing based on content length and type."""
    if not headers:
        return []
    
    flex_values = []
    
    for i, header in enumerate(headers):
        header_lower = header.lower()
        
        # Calculate average content length for this column
        content_lengths = [len(header)]  # Include header length
        for row in rows[:10]:  # Sample first 10 rows for performance
            if i < len(row) and row[i]:
                content_lengths.append(len(row[i]))
        
        avg_length = sum(content_lengths) / len(content_lengths) if content_lengths else 10
        
        # Assign flex based on content characteristics
        if avg_length > 30:  # Long content (descriptions, etc.)
            flex_values.append(4)
        elif avg_length > 15:  # Medium content
            flex_values.append(2)
        elif avg_length > 8:   # Short-medium content
            flex_values.append(1.5)
        else:  # Short content (codes, numbers)
            flex_values.append(1)
    
    return [int(f) if f >= 1 else 1 for f in flex_values]


def split_mixed_format_content(content: str) -> List[str]:
    """Split content that contains multiple table formats into separate sections."""
    lines = content.strip().split('\n')
    sections = []
    current_section = []
    
    for line in lines:
        line = line.strip()
        
        # Check for section breaks (like "**Page 3:**")
        if line.startswith('**') and ('page' in line.lower() or 'section' in line.lower()):
            # Save current section if it has content
            if current_section:
                sections.append('\n'.join(current_section))
                current_section = []
            # Start new section (don't include the section header)
            continue
        
        current_section.append(line)
    
    # Add the last section
    if current_section:
        sections.append('\n'.join(current_section))
    
    return sections if sections else [content]


def parse_single_table_section(content: str) -> tuple[List[str], List[List[str]], Optional[str], Optional[str], Optional[str]]:
    """Parse a single table section with enhanced validation."""
    lines = content.strip().split('\n')
    headers: List[str] = []
    rows: List[List[str]] = []
    pagination_info = None
    intro_text = None
    outro_text = None
    
    # Quick check: if content looks like regular sentences, don't try to parse as table
    text_content = ' '.join(lines)
    sentence_indicators = ['how can', 'i assist', 'you further', 'do you have', 'remember', 'can also provide']
    if any(indicator in text_content.lower() for indicator in sentence_indicators):
        return [], [], None, text_content, None
    
    # Extract pagination info from anywhere in the content
    filtered_lines = []
    for line in lines:
        line_lower = line.lower().strip()
        if ('showing page' in line_lower or 
            ('page' in line_lower and any(word in line_lower for word in ['next', 'continue', 'similar', 'rows']))):
            pagination_info = line.strip()
        else:
            filtered_lines.append(line)
    
    lines = filtered_lines
    
    # Detect table format and start position
    table_format, table_start_idx = detect_table_format(lines)
    
    # If no table format detected, return as intro text
    if table_format == 'unknown':
        return [], [], None, ' '.join([line.strip() for line in lines if line.strip()]), None
    
    # Extract intro text (everything before the table)
    intro_lines = []
    for i in range(table_start_idx):
        line = lines[i].strip()
        if line and not line.startswith('**'):
            intro_lines.append(line)
    
    if intro_lines:
        intro_text = ' '.join(intro_lines)
    
    last_row_idx: Optional[int] = None

    if table_format == 'markdown':
        # Parse markdown table starting from table_start_idx
        for j, line in enumerate(lines[table_start_idx:]):
            line = line.strip()
            if not line or line.startswith('|:') or line.startswith('|--') or line.startswith('|-'):
                continue
            
            if '|' in line:
                # Split by | and clean up
                cols = [col.strip() for col in line.split('|')]
                # Remove empty first/last elements from leading/trailing |
                if cols and not cols[0]:
                    cols = cols[1:]
                if cols and not cols[-1]:
                    cols = cols[:-1]
                
                # Clean up NULL values and normalize data
                cleaned_cols = []
                for col in cols:
                    if col.upper() == 'NULL' or not col.strip():
                        cleaned_cols.append('')
                    else:
                        cleaned_cols.append(col.strip())
                
                if not headers:
                    headers = cleaned_cols
                else:
                    # Validate and clean the row
                    cleaned_cols = validate_and_clean_row(cleaned_cols, headers)
                    if any(cleaned_cols):  # Only add non-empty rows
                        rows.append(cleaned_cols)
                    last_row_idx = table_start_idx + j
            else:
                # End of markdown table block
                if last_row_idx is None and headers:
                    last_row_idx = table_start_idx + j - 1
                break
    elif table_format == 'space_separated':
        # Enhanced space-separated table parsing
        header_found = False
        data_start_idx = table_start_idx
        last_row_idx = None
        
        # Find and parse headers with better validation
        for i, line in enumerate(lines[table_start_idx:], start=table_start_idx):
            line = line.strip()
            if not line:
                continue
                
            # Enhanced header detection - must look like actual table headers
            if (not header_found and 
                len(line.split()) >= 3 and 
                any(c.isalpha() for c in line) and
                # Additional validation: headers shouldn't be full sentences
                not any(word.lower() in ['the', 'and', 'or', 'but', 'with', 'from', 'can', 'how', 'you', 'this', 'that'] for word in line.split()[:5]) and
                # Require some numeric/code-like evidence in header line
                (any(any(ch.isdigit() for ch in w) for w in line.split()) or any(re.match(r'[A-Z]{1,3}\d{3,}', w) for w in line.split())) and
                # Avoid punctuation-heavy sentences
                not any(p in line for p in ['.', ',', '!', '?'])
               ):
                
                # Try different splitting strategies
                potential_headers = []
                
                # Strategy 1: Split by multiple spaces or tabs
                headers_v1 = re.split(r'\s{2,}|\t+', line)
                headers_v1 = [h.strip() for h in headers_v1 if h.strip()]
                
                # Strategy 2: Split by single space if first strategy gives too few columns
                headers_v2 = line.split()
                
                # Choose the best strategy
                if len(headers_v1) >= 3:  # Prefer multi-space split if it gives good results
                    headers = headers_v1
                elif len(headers_v2) >= 3:  # Fall back to single space split
                    headers = headers_v2
                else:
                    continue  # Skip this line, not a good header candidate
                
                header_found = True
                data_start_idx = i + 1
                break
        
        # Parse data rows with improved column detection
        for i in range(data_start_idx, len(lines)):
            line = lines[i].strip()
            if not line or line.startswith('**'):
                continue
            
            # Try different splitting strategies
            cols = []
            
            # Strategy 1: Split by multiple spaces or tabs
            potential_cols = re.split(r'\s{2,}|\t+', line)
            
            # Strategy 2: If we don't get enough columns, try intelligent reconstruction
            if len(potential_cols) < len(headers) and len(headers) > 0:
                words = line.split()
                if len(words) >= len(headers):
                    # Distribute words across expected columns
                    cols = []
                    words_per_col = len(words) // len(headers)
                    extra_words = len(words) % len(headers)
                    
                    word_idx = 0
                    for col_idx in range(len(headers)):
                        # Give extra words to middle columns (likely descriptions)
                        words_for_this_col = words_per_col + (1 if col_idx < extra_words else 0)
                        
                        if col_idx == len(headers) - 1:  # Last column gets remaining words
                            col_words = words[word_idx:]
                        else:
                            col_words = words[word_idx:word_idx + words_for_this_col]
                            word_idx += words_for_this_col
                        
                        cols.append(' '.join(col_words) if col_words else '')
                else:
                    cols = potential_cols
            else:
                cols = potential_cols
            
            # Clean up columns
            cleaned_cols = []
            for col in cols:
                if col.upper() == 'NULL' or col == '-':
                    cleaned_cols.append('')
                else:
                    cleaned_cols.append(col.strip())
            
            # Validate and clean the row
            cleaned_cols = validate_and_clean_row(cleaned_cols, headers)
            if any(cleaned_cols):  # Only add non-empty rows
                rows.append(cleaned_cols)
            last_row_idx = i

    # Collect outro text if any non-table content remains after the table
    if last_row_idx is not None and last_row_idx + 1 < len(lines):
        trailing = [ln.strip() for ln in lines[last_row_idx + 1 :] if ln.strip()]
        if trailing:
            outro_text = ' '.join(trailing)

    return headers, rows, pagination_info, intro_text, outro_text


def parse_table_data(content: str) -> tuple[List[str], List[List[str]], Optional[str], Optional[str], Optional[str]]:
    """Enhanced parser that handles mixed formats within a single response."""
    # Split content into sections if it contains multiple formats
    sections = split_mixed_format_content(content)
    
    all_headers = []
    all_rows = []
    all_pagination_info = []
    all_intro_text = []
    all_outro_text = []
    
    for section in sections:
        if not section.strip():
            continue
            
        headers, rows, pagination_info, intro_text, outro_text = parse_single_table_section(section)
        
        # Collect results from each section
        if headers and rows:
            # If this is the first table or has the same headers, combine
            if not all_headers:
                all_headers = headers
                all_rows = rows
            elif all_headers == headers:
                # Same headers, just add rows
                all_rows.extend(rows)
            else:
                # Different headers, prioritize the section with more data
                if len(rows) > len(all_rows):
                    all_headers = headers
                    all_rows = rows
        
        # Collect other info
        if pagination_info:
            all_pagination_info.append(pagination_info)
        if intro_text:
            all_intro_text.append(intro_text)
        if outro_text:
            all_outro_text.append(outro_text)
    
    # Combine collected information
    final_pagination = ' | '.join(all_pagination_info) if all_pagination_info else None
    final_intro = ' '.join(all_intro_text) if all_intro_text else None
    final_outro = ' '.join(all_outro_text) if all_outro_text else None
    
    return all_headers, all_rows, final_pagination, final_intro, final_outro


async def send_pagination_message(message: str):
    """Send a pagination message to continue the conversation."""
    # Import here to avoid circular imports
    from components.conversation import send_message
    import uuid
    
    app_state = me.state(AppState)
    message_id = str(uuid.uuid4())
    app_state.background_tasks[message_id] = ''
    await send_message(message, message_id)


async def next_page_handler(e: me.ClickEvent):
    """Handle next page button click."""
    yield
    await send_pagination_message("next")
    yield


async def previous_page_handler(e: me.ClickEvent):
    """Handle previous page button click."""
    yield
    await send_pagination_message("previous")
    yield


async def page_number_handler(e: me.ClickEvent, page_num: int):
    """Handle specific page number click."""
    yield
    await send_pagination_message(f"page {page_num}")
    yield


@me.component
def data_table(content: str, key: str = "data_table"):
    """
    Render a data table with proper styling and pagination controls.
    
    Args:
        content: Raw table content (markdown-like or structured text)
        key: Unique key for the component
    """
    app_state = me.state(AppState)
    is_dark = is_dark_mode(app_state)
    theme = get_table_theme(is_dark)
    
    # Parse the table data
    headers, rows, pagination_info, intro_text, outro_text = parse_table_data(content)

    if not is_valid_table(headers, rows):
        # Fallback: render as markdown if parsing fails or content fails validation
        me.markdown(
            content,
            style=me.Style(
                font_size=CSC_TYPOGRAPHY['font_size_base'],
                font_family=CSC_TYPOGRAPHY['font_family_primary'],
                line_height=CSC_TYPOGRAPHY['line_height_normal'],
                padding=me.Padding(top=0, left=0, right=0, bottom=0),
                margin=me.Margin(top=0, left=0, right=0, bottom=0),
                background='transparent',
                width='100%',
            ),
        )
        return
    
    # Container for intro text and table
    with me.box(
        style=me.Style(
            display='flex',
            flex_direction='column',
            width='100%',
            padding=me.Padding(top=12, left=16, right=16, bottom=12),
        ),
        key=f"{key}_wrapper"
    ):
            # Display intro text if present
            if intro_text:
                me.text(
                    intro_text,
                    style=me.Style(
                        font_family=CSC_TYPOGRAPHY['font_family_primary'],
                        font_size=CSC_TYPOGRAPHY['font_size_base'],
                        color=theme['text_primary'],
                        line_height=CSC_TYPOGRAPHY['line_height_normal'],
                        margin=me.Margin(bottom=16),
                        padding=me.Padding(left=0, right=0),
                        width='100%',
                    )
                )
            
            # Main table container - full width design for chat bubble
            with me.box(
                style=me.Style(
                    display='flex',
                    flex_direction='column',
                    font_family=CSC_TYPOGRAPHY['font_family_primary'],
                    border_radius=8,
                    overflow='hidden',
                    border=me.Border.all(me.BorderSide(color=theme['divider'], width=1)),
                    background=theme['row_even'],
                    width='100%',
                    max_width='100%',
                ),
                key=f"{key}_container"
            ):
                # Header row
                with me.box(
                    style=me.Style(
                        display='flex',
                        gap=8,
                        padding=me.Padding.symmetric(vertical=8, horizontal=12),
                        background=theme['header_bg'],
                        font_weight=CSC_TYPOGRAPHY['font_weight_semibold'],
                        border=me.Border(bottom=me.BorderSide(color=theme['divider'], width=1)),
                    )
                ):
                    # Calculate dynamic column flex values
                    column_flex_values = calculate_column_flex(headers, rows)
                    
                    for i, header in enumerate(headers):
                        flex_value = column_flex_values[i] if i < len(column_flex_values) else 1
                        with me.box(style=me.Style(flex=flex_value, min_width='60px')):
                            me.text(
                                header,
                                style=me.Style(
                                    color=theme['text_primary'],
                                    font_size=CSC_TYPOGRAPHY['font_size_base'],
                                    font_weight=CSC_TYPOGRAPHY['font_weight_semibold'],
                                )
                            )
                
                # Data rows
                for row_idx, row in enumerate(rows):
                    row_bg = theme['row_even'] if row_idx % 2 == 0 else theme['row_odd']
                    
                    with me.box(
                        style=me.Style(
                            display='flex',
                            gap=8,
                            align_items='flex_start',
                            padding=me.Padding.symmetric(vertical=8, horizontal=12),
                            background=row_bg,
                            border=me.Border(bottom=me.BorderSide(color=theme['divider'], width=1)) if row_idx < len(rows) - 1 else None,
                        ),
                        key=f"{key}_row_{row_idx}"
                    ):
                        # Calculate dynamic column flex values
                        column_flex_values = calculate_column_flex(headers, rows)
                        
                        for col_idx, cell in enumerate(row):
                            # Use calculated flex values
                            flex_value = column_flex_values[col_idx] if col_idx < len(column_flex_values) else 1
                            
                            with me.box(style=me.Style(flex=flex_value, min_width='60px')):
                                me.text(
                                    cell or '-',
                                    style=me.Style(
                                        color=theme['text_primary'] if cell else theme['text_secondary'],
                                        font_size=CSC_TYPOGRAPHY['font_size_base'],
                                        line_height='1.4',
                                        word_wrap='break-word',
                                        white_space='normal',
                                )
                            )
                
                # Pagination controls - compact design
                if pagination_info:
                    with me.box(
                        style=me.Style(
                            display='flex',
                            justify_content='space-between',
                            align_items='center',
                            padding=me.Padding.all(12),
                            background=theme['header_bg'],
                            border=me.Border(top=me.BorderSide(color=theme['divider'], width=1)),
                        ),
                        key=f"{key}_pagination"
                    ):
                        is_loading = bool(me.state(AppState).background_tasks)
                        # Pagination info text (show loading state)
                        me.text(
                            pagination_info,
                            style=me.Style(
                                font_family=CSC_TYPOGRAPHY['font_family_primary'],
                                font_size=CSC_TYPOGRAPHY['font_size_xs'],
                                color=theme['text_secondary'],
                                flex='1',
                            )
                        )
                        
                        # Pagination buttons - smaller and more compact
                        with me.box(
                            style=me.Style(
                                display='flex',
                                gap=6,
                                align_items='center',
                            )
                        ):
                            # Previous button
                            with me.content_button(
                                type='raised',
                                on_click=previous_page_handler,
                                style=me.Style(
                                    padding=me.Padding.symmetric(vertical=6, horizontal=10),
                                    border_radius=CSC_RADIUS['md'],
                                    font_size=CSC_TYPOGRAPHY['font_size_xs'],
                                    background=CSC_COLORS['primary_blue'],
                                    color=CSC_COLORS['white'],
                                ),
                                key=f"{key}_prev_btn"
                            ):
                             me.text('Previous', style=me.Style(color=CSC_COLORS['white']))                            
                            # Next button (highlighted)
                            with me.content_button(
                                type='raised',
                                on_click=next_page_handler,
                                style=me.Style(
                                    padding=me.Padding.symmetric(vertical=6, horizontal=10),
                                    border_radius=CSC_RADIUS['md'],
                                    font_size=CSC_TYPOGRAPHY['font_size_xs'],
                                    font_weight=CSC_TYPOGRAPHY['font_weight_semibold'],
                                    background=CSC_COLORS['primary_blue'],
                                    color=CSC_COLORS['white'],
                                ),
                                key=f"{key}_next_btn"
                            ):
                                me.text('Next', style=me.Style(color=CSC_COLORS['white']))

                # Outro text (anything below the table)
                if outro_text:
                    me.text(
                        outro_text,
                        style=me.Style(
                            font_family=CSC_TYPOGRAPHY['font_family_primary'],
                            font_size=CSC_TYPOGRAPHY['font_size_base'],
                            color=theme['text_primary'],
                            line_height=CSC_TYPOGRAPHY['line_height_normal'],
                            margin=me.Margin(top=16),
                            padding=me.Padding(left=0, right=0),
                            width='100%',
                        )
                    )


@me.component  
def render_table_content(content: str, key: str = "table_content"):
    """
    Render content that may contain mixed text and table data.
    
    This function intelligently separates text content from table data,
    rendering both appropriately while preserving all content visibility.
    """
    # Parse the content to separate text and table parts
    headers, rows, pagination_info, intro_text, _outro_text = parse_table_data(content)
    
    # Check if we actually found valid table data
    has_table_data = is_valid_table(headers, rows)
    
    with me.box(style=me.Style(
        # Use full width within bubble container
        width='100%',
        display='flex',
        flex_direction='column',
        gap=8,
    )):
        if has_table_data:
            # Render the table using data_table component
            data_table(content, key)
        else:
            # No table found - render everything as markdown with proper padding
            me.markdown(
                content,
                style=me.Style(
                    font_size=CSC_TYPOGRAPHY['font_size_base'],
                    font_family=CSC_TYPOGRAPHY['font_family_primary'],
                    line_height=CSC_TYPOGRAPHY['line_height_normal'],
                    padding=me.Padding(top=12, left=16, right=16, bottom=12),
                    margin=me.Margin(top=0, left=0, right=0, bottom=0),
                    background='transparent',
                    width='100%',
                ),
            )
