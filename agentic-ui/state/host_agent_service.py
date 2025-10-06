import json
import os
import sys
import traceback
import uuid

from typing import Any

from a2a.types import FileWithBytes, Message, Part, Role, Task, TaskState
from service.client.client import ConversationClient
from service.types import (
    Conversation,
    CreateConversationRequest,
    Event,
    GetEventRequest,
    ListAgentRequest,
    ListConversationRequest,
    ListMessageRequest,
    ListTaskRequest,
    MessageInfo,
    PendingMessageRequest,
    RegisterAgentRequest,
    SendMessageRequest,
)
from service.types import DeleteConversationRequest, DeleteConversationResponse
from service.types import DeleteAgentRequest

from .state import (
    AppState,
    SessionTask,
    StateConversation,
    StateEvent,
    StateMessage,
    StateTask,
)


server_url = 'http://localhost:12000'


async def ListConversations() -> list[Conversation]:
    client = ConversationClient(server_url)
    try:
        response = await client.list_conversation(ListConversationRequest())
        return response.result if response.result else []
    except Exception as e:
        print('Failed to list conversations: ', e)
    return []


async def SendMessage(message: Message) -> Message | MessageInfo | None:
    client = ConversationClient(server_url)
    try:
        response = await client.send_message(SendMessageRequest(params=message))
        return response.result
    except Exception as e:
        traceback.print_exc()
        print('Failed to send message: ', e)
    return None


async def CreateConversation() -> Conversation:
    client = ConversationClient(server_url)
    try:
        response = await client.create_conversation(CreateConversationRequest())
        return (
            response.result
            if response.result
            else Conversation(conversation_id='', is_active=False)
        )
    except Exception as e:
        print('Failed to create conversation', e)
    return Conversation(conversation_id='', is_active=False)


async def ListRemoteAgents():
    client = ConversationClient(server_url)
    try:
        response = await client.list_agents(ListAgentRequest())
        return response.result
    except Exception as e:
        print('Failed to read agents', e)


async def AddRemoteAgent(path: str):
    client = ConversationClient(server_url)
    try:
        await client.register_agent(RegisterAgentRequest(params=path))
    except Exception as e:
        print('Failed to register the agent', e)


async def DeleteRemoteAgent(name_or_url: str):
    client = ConversationClient(server_url)
    try:
        await client.delete_agent(DeleteAgentRequest(params=name_or_url))
    except Exception as e:
        print('Failed to delete the agent', e)


async def GetEvents() -> list[Event]:
    client = ConversationClient(server_url)
    try:
        response = await client.get_events(GetEventRequest())
        return response.result if response.result else []
    except Exception as e:
        print('Failed to get events', e)
    return []


async def GetProcessingMessages():
    client = ConversationClient(server_url)
    try:
        response = await client.get_pending_messages(PendingMessageRequest())
        return dict(response.result)
    except Exception as e:
        print('Error getting pending messages', e)
        # Always return a dict to avoid state corruption and ensure
        # callers can safely assume a mapping.
        return {}


def GetMessageAliases():
    return {}


async def GetTasks():
    client = ConversationClient(server_url)
    try:
        response = await client.list_tasks(ListTaskRequest())
        return response.result
    except Exception as e:
        print('Failed to list tasks ', e)


async def ListMessages(conversation_id: str) -> list[Message]:
    client = ConversationClient(server_url)
    try:
        response = await client.list_messages(
            ListMessageRequest(params=conversation_id)
        )
        return response.result if response.result else []
    except Exception as e:
        print('Failed to list messages ', e)
    return []


async def DeleteConversation(conversation_id: str):
    client = ConversationClient(server_url)
    try:
        await client.delete_conversation(DeleteConversationRequest(params=conversation_id))
    except Exception as e:
        print('Failed to delete conversation', e)


async def UpdateAppState(state: AppState, conversation_id: str):
    """Update the app state."""
    try:
        if conversation_id:
            state.current_conversation_id = conversation_id
            messages = await ListMessages(conversation_id)
            if messages is None:
                # Do not alter current messages if fetch failed
                pass
            elif len(messages) == 0:
                # Preserve optimistic messages for this conversation to avoid flicker
                if not state.messages or any(
                    getattr(m, 'context_id', '') != conversation_id for m in state.messages
                ):
                    state.messages = []
            else:
                state.messages = [convert_message_to_state(x) for x in messages]
        conversations = await ListConversations()
        if not conversations:
            state.conversations = []
        else:
            state.conversations = [
                convert_conversation_to_state(x) for x in conversations
            ]

        state.task_list = []
        for task in await GetTasks():
            state.task_list.append(
                SessionTask(
                    context_id=extract_conversation_id(task),
                    task=convert_task_to_state(task),
                )
            )
        # Pending messages from backend (message_id -> placeholder/progress)
        state.background_tasks = await GetProcessingMessages()
        state.message_aliases = GetMessageAliases()

        # Enrich background task texts with latest event content for the same conversation
        # so the UI can show meaningful, live progress in chat bubbles.
        try:
            if state.background_tasks:
                # Build a quick index: message_id -> context_id for fast lookup
                msg_context: dict[str, str] = {}
                try:
                    for m in state.messages or []:
                        if getattr(m, 'message_id', None):
                            msg_context[m.message_id] = getattr(m, 'context_id', '')
                except Exception:
                    pass

                # Collect latest event text per context_id
                events = await GetEvents()
                latest_event_text: dict[str, tuple[str, str]] = {}

                def _flatten_content(parts: list[tuple[Any, str]]) -> str:
                    texts: list[str] = []
                    for p in parts or []:
                        content, mime = p
                        if mime in ('text/plain', 'application/json'):
                            try:
                                texts.append(str(content))
                            except Exception:
                                pass
                        else:
                            # For non-text parts, show the mime type as a hint
                            if mime:
                                texts.append(str(mime))
                    return '\n'.join([t for t in texts if t])

                # Convert events to StateEvent-like tuples and keep the latest by simple overwrite
                for ev in events or []:
                    try:
                        sev = convert_event_to_state(ev)
                        ctx = getattr(sev, 'context_id', '')
                        if not ctx:
                            continue
                        # Use overview instead of content for better readability
                        overview_text = getattr(sev, 'overview', '') or _flatten_content(getattr(sev, 'content', []))
                        latest_event_text[ctx] = ('', overview_text)
                    except Exception:
                        continue

                # Apply event-derived text to each pending message where available
                for msg_id in list(state.background_tasks.keys()):
                    ctx_id = msg_context.get(msg_id, '')
                    if not ctx_id:
                        continue
                    actor_content = latest_event_text.get(ctx_id)
                    if not actor_content:
                        continue
                    actor, text = actor_content
                    if not text:
                        continue
                    # Compose a concise progress line with loading indicator
                    composed = f"{actor} - {text}" if actor else text
                    # Add loading indicator prefix for better UX
                    composed = f"Working... {composed}" if not composed.startswith('Working') else composed
                    # Trim very long messages to keep the UI tidy
                    if len(composed) > 200:
                        composed = composed[:197] + '...'
                    state.background_tasks[msg_id] = composed
        except Exception:
            # Never let progress enrichment break the polling loop
            pass
    except Exception as e:
        print('Failed to update state: ', e)
        traceback.print_exc(file=sys.stdout)


async def UpdateApiKey(api_key: str):
    """Update the API key"""
    import httpx

    try:
        # Set the environment variable
        os.environ['GOOGLE_API_KEY'] = api_key

        # Call the update API endpoint
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f'{server_url}/api_key/update', json={'api_key': api_key}
            )
            response.raise_for_status()
        return True
    except Exception as e:
        print('Failed to update API key: ', e)
        return False


def convert_message_to_state(message: Message) -> StateMessage:
    if not message:
        return StateMessage()

    return StateMessage(
        message_id=message.messageId,
        context_id=message.contextId if message.contextId else '',
        task_id=message.taskId if message.taskId else '',
        role=message.role.name,
        content=extract_content(message.parts),
    )


def convert_conversation_to_state(
    conversation: Conversation,
) -> StateConversation:
    # Derive a human-friendly name if backend did not provide one
    derived_name = (conversation.name or '').strip()
    if not derived_name:
        try:
            # Try to use the first available text content from messages
            for m in conversation.messages or []:
                for part in m.parts or []:
                    p = part.root
                    if getattr(p, 'kind', None) == 'text' and getattr(p, 'text', ''):
                        derived_name = p.text.strip()[:40]
                        break
                if derived_name:
                    break
        except Exception:
            # Fall back silently if structure is different
            derived_name = ''

    if not derived_name:
        # Final fallback to a short ID-based label
        short_id = conversation.conversation_id[:8] if conversation.conversation_id else 'unknown'
        derived_name = f'Conversation {short_id}'

    return StateConversation(
        conversation_id=conversation.conversation_id,
        conversation_name=derived_name,
        is_active=conversation.is_active,
        message_ids=[extract_message_id(x) for x in conversation.messages],
    )


def convert_task_to_state(task: Task) -> StateTask:
    # Get the first message as the description
    output = (
        [extract_content(a.parts) for a in task.artifacts]
        if task.artifacts
        else []
    )
    if not task.history:
        return StateTask(
            task_id=task.id,
            context_id=task.contextId,
            state=TaskState.failed.name,
            message=StateMessage(
                message_id=str(uuid.uuid4()),
                context_id=task.contextId,
                task_id=task.id,
                role=Role.agent.name,
                content=[('No history', 'text')],
            ),
            artifacts=output,
        )
    else:
        message = task.history[0]
        last_message = task.history[-1]
        if last_message != message:
            output = [extract_content(last_message.parts)] + output
    return StateTask(
        task_id=task.id,
        context_id=task.contextId,
        state=str(task.status.state),
        message=convert_message_to_state(message),
        artifacts=output,
    )


def convert_event_to_state(event: Event) -> StateEvent:
    return StateEvent(
        context_id=extract_message_conversation(event.content),
        actor=event.actor,
        role=event.content.role.name,
        id=event.id,
        content=extract_content(event.content.parts),
        overview=event.overview,
    )


def extract_content(
    message_parts: list[Part],
) -> list[tuple[str | dict[str, Any], str]]:
    parts: list[tuple[str | dict[str, Any], str]] = []
    if not message_parts:
        return []
    for part in message_parts:
        p = part.root
        if p.kind == 'text':
            parts.append((p.text, 'text/plain'))
        elif p.kind == 'file':
            if isinstance(p.file, FileWithBytes):
                parts.append((p.file.bytes, p.file.mimeType or ''))
            else:
                parts.append((p.file.uri, p.file.mimeType or ''))
        elif p.kind == 'data':
            try:
                jsonData = json.dumps(p.data)
                if 'type' in p.data and p.data['type'] == 'form':
                    parts.append((p.data, 'form'))
                else:
                    parts.append((jsonData, 'application/json'))
            except Exception as e:
                print('Failed to dump data', e)
                parts.append(('<data>', 'text/plain'))
    return parts


def extract_message_id(message: Message) -> str:
    return message.messageId


def extract_message_conversation(message: Message) -> str:
    return message.contextId if message.contextId else ''


def extract_conversation_id(task: Task) -> str:
    if task.contextId:
        return task.contextId
    # Tries to find the first conversation id for the message in the task.
    if task.status.message:
        return task.status.message.contextId or ''
    return ''

