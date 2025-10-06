import mesop as me
from typing import Literal, Tuple, Any
from pydantic.dataclasses import dataclass
import dataclasses

from typing import Any, Literal

import mesop as me

from pydantic.dataclasses import dataclass


ContentPart = str | dict[str, Any]


@dataclass
class StateConversation:
    """StateConversation provides mesop state compliant view of a conversation"""

    conversation_id: str = ''
    conversation_name: str = ''
    is_active: bool = True
    message_ids: list[str] = dataclasses.field(default_factory=list)


@dataclass
class StateMessage:
    """StateMessage provides mesop state compliant view of a message"""

    message_id: str = ''
    task_id: str = ''
    context_id: str = ''
    role: str = ''
    # Each content entry is a content, media type pair.
    content: list[Tuple[ContentPart, str]] = dataclasses.field(
        default_factory=list
    )


@dataclass
class StateTask:
    """StateTask provides mesop state compliant view of task"""

    task_id: str = ''
    context_id: str | None = None
    state: str | None = None
    message: StateMessage = dataclasses.field(default_factory=StateMessage)
    artifacts: list[list[Tuple[ContentPart, str]]] = dataclasses.field(
        default_factory=list
    )


@dataclass
class SessionTask:
    """SessionTask organizes tasks based on conversation"""

    context_id: str = ''
    task: StateTask = dataclasses.field(default_factory=StateTask)


@dataclass
class StateEvent:
    """StateEvent provides mesop state compliant view of event"""

    context_id: str = ''
    actor: str = ''
    role: str = ''
    id: str = ''
    # Each entry is a pair of (content, media type)
    content: list[Tuple[ContentPart, str]] = dataclasses.field(
        default_factory=list
    )
    # Short, abstract-level summary of the interaction
    overview: str = ''


@me.stateclass
class AppState:
    """Mesop Application State"""

    sidenav_open: bool = True
    theme_mode: Literal['system', 'light', 'dark'] = 'light'  # Default to light theme
    # Track current route for active menu highlighting
    current_page: str = '/'

    current_conversation_id: str = ''
    conversations: list[StateConversation]
    messages: list[StateMessage]
    task_list: list[SessionTask] = dataclasses.field(default_factory=list)
    background_tasks: dict[str, str] = dataclasses.field(default_factory=dict)
    message_aliases: dict[str, str] = dataclasses.field(default_factory=dict)
    # This is used to track the data entered in a form
    completed_forms: dict[str, dict[str, Any] | None] = dataclasses.field(
        default_factory=dict
    )
    # This is used to track the message sent to agent with form data
    form_responses: dict[str, str] = dataclasses.field(default_factory=dict)
    polling_interval: int = 1

    # Added for API key management
    api_key: str = ''
    uses_vertex_ai: bool = False
    api_key_dialog_open: bool = False

    # deletion flow for conversations (frontend-only when server RPC not available)
    conversation_to_delete: str | None = None
    delete_dialog_open: bool = False
    conversation_to_delete_name: str | None = None

    # header profile menu visibility
    show_user_menu: bool = False
    # language switcher menu visibility
    show_language_menu: bool = False
    # selected UI language
    language: str = 'en'
    # trigger browser-side logout (clear cookies + redirect)
    trigger_logout: bool = False

    # user info from cookie
    user_first_name: str = ''
    user_last_name: str = ''
    user_email: str = ''
    user_id: str = ''

    # sidebar expand/collapse
    nav_expand_conversations: bool = True
    nav_expand_admin: bool = True

    # Hide footer on conversation pages for better UX
    show_footer: bool = True

    # Suggested starter questions to display for brand new chats (no messages yet)
    suggested_questions: list[str] = dataclasses.field(
        default_factory=lambda: [
            'Provide me the list of plants.',
            'Provide me the list of materials in plant 3010.',
            'Provide me the similar parts for material A0000150400.',
            'Compare the prices for material U0000000139020000 in plant MBC Untertürkheim'
            # 'Provide me the similar parts for material U0000000139020000.',
        ]
    )


@me.stateclass
class SettingsState:
    """Settings State"""

    output_mime_types: list[str] = dataclasses.field(
        default_factory=lambda: [
            'image/*',
            'text/plain',
        ]
    )
