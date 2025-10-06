from __future__ import annotations

import base64
import datetime
import errno
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Optional, Tuple

import httpx
import asyncio

from a2a.types import (
    AgentCard,
    Artifact,
    DataPart,
    FilePart,
    FileWithBytes,
    FileWithUri,
    Message,
    Part,
    Role,
    Task,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
    TextPart,
)
from google.adk import Runner
from google.adk.artifacts import InMemoryArtifactService
from google.adk.events.event import Event as ADKEvent
from google.adk.events.event_actions import EventActions as ADKEventActions
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types
from hosts.multiagent.host_agent import HostAgent
from hosts.multiagent.remote_agent_connection import (
    TaskCallbackArg,
)
from utils.agent_card import get_agent_card

from service.server.application_manager import ApplicationManager
from service.types import Conversation, Event


class ADKHostManager(ApplicationManager):
    """An implementation of memory based management with fake agent actions

    This implements the interface of the ApplicationManager to plug into
    the AgentServer. This acts as the service contract that the Mesop app
    uses to send messages to the agent and provide information for the frontend.
    """

    async def generate_overview(self, message: Message, actor: str) -> str:
        """Generate a short overview/summary of an interaction using LLM.
        
        Args:
            message: The message containing the interaction content
            actor: The actor (user, agent name, host_agent, etc.)
            
        Returns:
            A short, human-readable summary of the interaction
        """
        if not message.parts:
            return f"{actor.capitalize()} sent an empty message"
            
        # Extract text content from message parts
        text_content = ""
        has_files = False
        has_data = False
        
        for part in message.parts:
            if part.root.kind == 'text':
                text_content += part.root.text + " "
            elif part.root.kind == 'file':
                has_files = True
            elif part.root.kind == 'data':
                has_data = True
        
        text_content = text_content.strip()
        
        # Always try LLM first, no hardcoded fallbacks
        try:
            return await self._generate_llm_overview(text_content, actor, has_files, has_data)
        except Exception as e:
            self.logger.warning(f"LLM overview generation failed: {e}")
            # Provide a more informative fallback with processing indicator
            if actor.lower() in ['host_agent', 'host agent']:
                return f"System processing {actor.lower()} request (analyzing...)"
            else:
                return f"{actor} working on request (processing...)"
    
    async def _generate_llm_overview(self, text_content: str, actor: str, has_files: bool, has_data: bool) -> str:
        """Generate overview using LLM for complete contextual understanding."""
        
        # Prepare additional context
        context_info = []
        if has_files:
            context_info.append("includes file attachments")
        if has_data:
            context_info.append("includes structured data/JSON")
        
        context_str = f" ({', '.join(context_info)})" if context_info else ""
        
        # Keep more content for better LLM understanding, especially for JSON data
        if has_data:
            # For structured data, keep more content to capture key details
            display_content = text_content[:800] + "..." if len(text_content) > 800 else text_content
        else:
            # For regular text, keep moderate length
            display_content = text_content[:500] + "..." if len(text_content) > 500 else text_content
        
        # Debug: Log what we're sending to the LLM
        self.logger.info(f"Sending to LLM - Actor: {actor}, Content length: {len(text_content)}, Display length: {len(display_content)}")
        self.logger.info(f"Content preview: {display_content[:200]}...")
        
        # Create a more detailed prompt for the LLM with better context
        # Format actor name properly for display
        formatted_actor = actor.replace('_', ' ').title() if actor else "Agent"
        
        prompt = f"""You are analyzing an interaction to create a short, specific overview (80-120 characters).

                CONTENT TO ANALYZE:
                Actor: {actor}
                Content: {display_content}{context_str}

                TASK: Create a brief, specific summary of what is happening.

                LOOK FOR:
                - Material codes, part numbers, plant IDs, agent names
                - Actions: find, search, compare, analyze, process, execute, request
                - Task states: working, processing, analyzing, waiting, completed
                - JSON data fields, API calls, system operations

                EXAMPLES:
                - "User requesting similar parts search for material A0000150400"
                - "CSC Agent processing price comparison for plant MBC materials"
                - "Host Agent coordinating multi-agent task execution"
                - "System executing background data processing request"
                - "Agent initializing task workflow"

                FALLBACK: If unclear, use "{formatted_actor} executing system operation"

                OVERVIEW:"""

        # Use the LLM directly through the existing infrastructure
        try:
            # Create content for LLM
            llm_parts = [types.Part.from_text(text=prompt)]
            llm_content = types.Content(parts=llm_parts, role='user')
            
            # Create a minimal temporary session for overview generation
            temp_session_id = f"overview_{uuid.uuid4().hex[:8]}"
            temp_session = await self._session_service.create_session(
                app_name=self.app_name,
                user_id=f"{self.user_id}_overview",
                session_id=temp_session_id
            )
            
            # Generate using the host runner
            overview_response = None
            async for event in self._host_runner.run_async(
                user_id=f"{self.user_id}_overview",
                session_id=temp_session_id,
                new_message=llm_content,
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            overview_response = part.text.strip()
                            break
                    if overview_response:
                        break
            
            if overview_response:
                # Clean up the response
                overview = overview_response.replace("Overview:", "").strip()
                overview = overview.strip('"').strip("'").strip()
                
                # Ensure it's informative but not too long
                if len(overview) > 150:
                    overview = overview[:147] + "..."
                
                # Add processing indicator if it seems like an ongoing task
                if any(word in overview.lower() for word in ['processing', 'analyzing', 'generating', 'calculating', 'searching']):
                    if not overview.endswith('...') and not any(indicator in overview for indicator in ['(processing', '(analyzing', '(in progress']):
                        overview += " (in progress...)"
                
                return overview
            
            raise Exception("No LLM response received")
            
        except Exception as e:
            self.logger.error(f"LLM overview generation failed: {e}")
            raise
    
    async def _generate_llm_overview_sync(self, message: Message, actor: str) -> str:
        """Generate LLM overview for synchronous contexts like emit_event."""
        
        # Extract content quickly
        text_parts = []
        data_parts = []
        has_files = False
        has_data = False
        
        for part in message.parts:
            if part.root.kind == 'text':
                text_parts.append(part.root.text)
            elif part.root.kind == 'file':
                has_files = True
            elif part.root.kind == 'data':
                has_data = True
                # Extract data content - this is structured data like JSON
                data_parts.append(str(part.root.data))
        
        # Combine text and data parts for comprehensive content
        all_content = text_parts + data_parts
        text_content = " ".join(all_content).strip()
        
        # Add debug logging to see what we're working with
        self.logger.info(f"Extracted content for overview ({actor}): text_parts={len(text_parts)}, data_parts={len(data_parts)}, total_length={len(text_content)}")
        if text_content:
            self.logger.info(f"First 200 chars: {text_content[:200]}")
        
        # Use the existing LLM method
        return await self._generate_llm_overview(text_content, actor, has_files, has_data)
    
    def __init__(
        self,
        http_client: httpx.AsyncClient,
        api_key: str = '',
        uses_vertex_ai: bool = False,
        user_id: str = 'test_user',
    ):
        # Initialize logger first before any operations
        self.logger = logging.getLogger('ADKHostManager')
        self._conversations: list[Conversation] = []
        self._messages: list[Message] = []
        self._tasks: list[Task] = []
        self._events: dict[str, Event] = {}
        self._pending_message_ids: list[str] = []
        self._agents: list[AgentCard] = []
        self._artifact_chunks: dict[str, list[Artifact]] = {}
        self._session_service = InMemorySessionService()
        self._artifact_service = InMemoryArtifactService()
        self._memory_service = InMemoryMemoryService()
        self._host_agent = HostAgent([], http_client, self.task_callback)
        # NOTE: persisted agents and conversations are loaded below

        self._context_to_conversation: dict[str, str] = {}
        self.user_id = user_id
        self._current_user_id = user_id  # Keep track of the current user
        self.app_name = 'A2A'
        self.api_key = api_key or os.environ.get('GOOGLE_API_KEY', '')
        self.uses_vertex_ai = (
            uses_vertex_ai
            or os.environ.get('GOOGLE_GENAI_USE_VERTEXAI', '').upper() == 'TRUE'
        )
        endpoint = os.environ.get('GEMINI_ENDPOINT')
        # Set environment variables based on auth method
        if self.uses_vertex_ai:
            os.environ['GOOGLE_GENAI_USE_VERTEXAI'] = 'TRUE'

        elif self.api_key:
            # Use API key authentication
            os.environ['GOOGLE_GENAI_USE_VERTEXAI'] = 'FALSE'
            os.environ['GOOGLE_API_KEY'] = self.api_key
            os.environ['GEMINI_ENDPOINT'] = endpoint # added for nexus
        
       
        if endpoint:
            # Set SDK base URL using the public environment variable the SDK
            # reads. Avoid importing internal modules from the installed
            # google-genai package.
            os.environ['GOOGLE_GEMINI_BASE_URL'] = endpoint

        # Load persisted agents and conversations from disk so they survive restarts
        try:
            self._load_agents_from_disk()
        except Exception:
            pass
        try:
            self._load_conversations_from_disk()
        except Exception as e:
            # Only show errors for actual failures, not for missing files which is normal
            if not isinstance(e, FileNotFoundError):
                self.logger.error(f"Error loading conversations: {e}")
            else:
                # For a new user, initialize with empty conversations list
                self._conversations = []

        self.logger.info(f"Initialized ADKHostManager with user_id: {user_id}")

        self._initialize_host()

        # Map of message id to task id
        self._task_map: dict[str, str] = {}
        # Map to manage 'lost' message ids until protocol level id is introduced
        self._next_id: dict[
            str, str
        ] = {}  # dict[str, str]: previous message to next message

    def _initialize_host(self):
        agent = self._host_agent.create_agent()
        self._host_runner = Runner(
            app_name=self.app_name,
            agent=agent,
            artifact_service=self._artifact_service,
            session_service=self._session_service,
            memory_service=self._memory_service,
        )

    async def create_conversation(self) -> Conversation:
        session = await self._session_service.create_session(
            app_name=self.app_name, user_id=self.user_id
        )
        conversation_id = session.id
        c = Conversation(conversation_id=conversation_id, is_active=True)
        self._conversations.append(c)
        # persist conversations to disk
        try:
            self._save_conversations_to_disk()
        except Exception:
            pass
        return c

    def update_api_key(self, api_key: str):
        """Update the API key and reinitialize the host if needed"""
        if api_key and api_key != self.api_key:
            self.api_key = api_key
            
    def update_user_id(self, new_user_id: str):
        """Update the user ID and reload user-specific conversations.
        
        This ensures each user only sees their own conversations by:
        1. Saving current user's conversations to disk
        2. Updating the user ID
        3. Clearing the conversations list
        4. Loading the conversations for the new user
        
        Args:
            new_user_id: The ID of the user to switch to
        """
        if new_user_id == self.user_id:
            # No change needed if it's the same user
            self.logger.info(f"User ID unchanged: {new_user_id}")
            return
        
        self.logger.info(f"Switching user ID from {self.user_id} to {new_user_id}")
            
        # Save current user's conversations before switching
        if self._conversations:
            try:
                self.logger.info(f"Saving conversations for user {self.user_id}")
                self._save_conversations_to_disk()
            except Exception as e:
                self.logger.error(f"Error saving conversations for user {self.user_id}: {e}")
        
        # Update the user ID
        self.user_id = new_user_id
        self.logger.info(f"Updated user_id to: {new_user_id}")
        
        # Clear existing conversations
        self._conversations = []
        self.logger.info("Cleared existing conversations")
        
        # Load conversations for the new user
        try:
            self.logger.info(f"Loading conversations for user {new_user_id}")
            self._load_conversations_from_disk()
            self.logger.info(f"Loaded {len(self._conversations)} conversations for user {new_user_id}")
        except FileNotFoundError:
            # This is normal for new users
            self.logger.info(f"No conversation file found for user {new_user_id}, starting fresh")
        except Exception as e:
            self.logger.error(f"Error loading conversations for user {new_user_id}: {e}")

    def sanitize_message(self, message: Message) -> Message:
        if message.contextId:
            conversation = self.get_conversation(message.contextId)
            if not conversation:
                return message
            # Check if the last event in the conversation was tied to a task.
            if conversation.messages:
                task_id = conversation.messages[-1].taskId
                if task_id and task_still_open(
                    next(
                        filter(lambda x: x and x.id == task_id, self._tasks),
                        None,
                    )
                ):
                    message.taskId = task_id
        return message

    async def process_message(self, message: Message):
        message_id = message.messageId
        if message_id:
            self._pending_message_ids.append(message_id)
        context_id = message.contextId
        conversation = self.get_conversation(context_id)
        self._messages.append(message)
        if conversation:
            conversation.messages.append(message)
            # persist after adding user message
            try:
                self._save_conversations_to_disk()
            except Exception:
                pass
        self.add_event(
            Event(
                id=str(uuid.uuid4()),
                actor='user',
                content=message,
                timestamp=datetime.datetime.utcnow().timestamp(),
                overview=await self.generate_overview(message, 'user'),
            )
        )
        final_event = None
        # Determine if a task is to be resumed.
        session = await self._session_service.get_session(
            app_name=self.app_name, user_id=self.user_id, session_id=context_id
        )
        task_id = message.taskId
        # Update state must happen in an event
        state_update = {
            'task_id': task_id,
            'context_id': context_id,
            'message_id': message.messageId,
        }
        # Need to upsert session state now, only way is to append an event.
        await self._session_service.append_event(
            session,
            ADKEvent(
                id=ADKEvent.new_id(),
                author='host_agent',
                invocation_id=ADKEvent.new_id(),
                actions=ADKEventActions(state_delta=state_update),
            ),
        )
        self.logger.info(f"[process_message] Processing message for user {self.user_id}, conversation {message.contextId}")
        # Log headers that would be sent in API calls
        self.logger.info(f"[process_message] Headers that would be sent: {{'x-userinfo': '<user_info_for_{self.user_id}>'}}")
        async for event in self._host_runner.run_async(
            user_id=self.user_id,
            session_id=context_id,
            new_message=self.adk_content_from_message(message),
        ):
            if (
                event.actions.state_delta
                and 'task_id' in event.actions.state_delta
            ):
                task_id = event.actions.state_delta['task_id']
            content_message = await self.adk_content_to_message(
                event.content, context_id, task_id
            )
            self.add_event(
                Event(
                    id=event.id,
                    actor=event.author,
                    content=content_message,
                    timestamp=event.timestamp,
                    overview=await self.generate_overview(content_message, event.author),
                )
            )
            final_event = event
        response: Message | None = None
        if final_event:
            if (
                final_event.actions.state_delta
                and 'task_id' in final_event.actions.state_delta
            ):
                task_id = event.actions.state_delta['task_id']
            final_event.content.role = 'model'
            response = await self.adk_content_to_message(
                final_event.content, context_id, task_id
            )
            self._messages.append(response)

        if conversation and response:
            conversation.messages.append(response)
            # persist after adding model response
            try:
                self._save_conversations_to_disk()
            except Exception:
                pass
        self._pending_message_ids.remove(message_id)

    def add_task(self, task: Task):
        self._tasks.append(task)

    def update_task(self, task: Task):
        for i, t in enumerate(self._tasks):
            if t.id == task.id:
                self._tasks[i] = task
                return

    def task_callback(self, task: TaskCallbackArg, agent_card: AgentCard):
        # Schedule async emit_event in background
        asyncio.create_task(self.emit_event(task, agent_card))
        
        if isinstance(task, TaskStatusUpdateEvent):
            current_task = self.add_or_get_task(task)
            current_task.status = task.status
            self.attach_message_to_task(task.status.message, current_task.id)
            self.insert_message_history(current_task, task.status.message)
            self.update_task(current_task)
            return current_task
        elif isinstance(task, TaskArtifactUpdateEvent):
            current_task = self.add_or_get_task(task)
            self.process_artifact_event(current_task, task)
            self.update_task(current_task)
            return current_task
        # Otherwise this is a Task, either new or updated
        elif not any(filter(lambda x: x and x.id == task.id, self._tasks)):
            self.attach_message_to_task(task.status.message, task.id)
            self.add_task(task)
            return task
        else:
            self.attach_message_to_task(task.status.message, task.id)
            self.update_task(task)
            return task

    async def emit_event(self, task: TaskCallbackArg, agent_card: AgentCard):
        content = None
        context_id = task.contextId
        if isinstance(task, TaskStatusUpdateEvent):
            if task.status.message:
                content = task.status.message
            else:
                content = Message(
                    parts=[Part(root=TextPart(text=str(task.status.state)))],
                    role=Role.agent,
                    messageId=str(uuid.uuid4()),
                    contextId=context_id,
                    taskId=task.taskId,
                )
        elif isinstance(task, TaskArtifactUpdateEvent):
            content = Message(
                parts=task.artifact.parts,
                role=Role.agent,
                messageId=str(uuid.uuid4()),
                contextId=context_id,
                taskId=task.taskId,
            )
        elif task.status and task.status.message:
            content = task.status.message
        elif task.artifacts:
            parts = []
            for a in task.artifacts:
                parts.extend(a.parts)
            content = Message(
                parts=parts,
                role=Role.agent,
                messageId=str(uuid.uuid4()),
                taskId=task.id,
                contextId=context_id,
            )
        else:
            content = Message(
                parts=[Part(root=TextPart(text=str(task.status.state)))],
                role=Role.agent,
                messageId=str(uuid.uuid4()),
                taskId=task.id,
                contextId=context_id,
            )
        if content:
            # Create event with LLM-generated overview
            event_id = str(uuid.uuid4())
            
            # Debug: Log the task and content details
            self.logger.info(f"Generating overview for {agent_card.name}, task type: {type(task).__name__}")
            self.logger.info(f"Task status state: {getattr(task.status, 'state', 'No state') if hasattr(task, 'status') and task.status else 'No status'}")
            
            # Try to generate LLM overview, but don't block event creation
            try:
                overview = await self._generate_llm_overview_sync(content, agent_card.name)
                self.logger.warning(f"overview {agent_card.name}: {overview}")
            except Exception as e:
                self.logger.warning(f"Failed to generate overview for {agent_card.name}: {e}")
                # More informative fallback with processing indicator
                overview = f"{agent_card.name} processing task (working...)"
            
            event = Event(
                id=event_id,
                actor=agent_card.name,
                content=content,
                timestamp=datetime.datetime.utcnow().timestamp(),
                overview=overview,
            )
            self.add_event(event)

    def attach_message_to_task(self, message: Message | None, task_id: str):
        if message:
            self._task_map[message.messageId] = task_id

    def insert_message_history(self, task: Task, message: Message | None):
        if not message:
            return
        if task.history is None:
            task.history = []
        message_id = message.messageId
        if not message_id:
            return
        if task.history and (
            task.status.message
            and task.status.message.messageId
            not in [x.messageId for x in task.history]
        ):
            task.history.append(task.status.message)
        elif not task.history and task.status.message:
            task.history = [task.status.message]
        else:
            print(
                'Message id already in history',
                task.status.message.messageId if task.status.message else '',
                task.history,
            )

    def add_or_get_task(self, event: TaskCallbackArg):
        task_id = None
        if isinstance(event, Message):
            task_id = event.taskId
        elif isinstance(event, Task):
            task_id = event.id
        else:
            task_id = event.taskId
        if not task_id:
            task_id = str(uuid.uuid4())
        current_task = next(
            filter(lambda x: x.id == task_id, self._tasks), None
        )
        if not current_task:
            context_id = event.contextId
            current_task = Task(
                id=task_id,
                # initialize with submitted
                status=TaskStatus(state=TaskState.submitted),
                artifacts=[],
                contextId=context_id,
            )
            self.add_task(current_task)
            return current_task

        return current_task

    def process_artifact_event(
        self, current_task: Task, task_update_event: TaskArtifactUpdateEvent
    ):
        artifact = task_update_event.artifact
        if not task_update_event.append:
            # received the first chunk or entire payload for an artifact
            if (
                task_update_event.lastChunk is None
                or task_update_event.lastChunk
            ):
                # lastChunk bit is missing or is set to true, so this is the entire payload
                # add this to artifacts
                if not current_task.artifacts:
                    current_task.artifacts = []
                current_task.artifacts.append(artifact)
            else:
                # this is a chunk of an artifact, stash it in temp store for assembling
                if artifact.artifactId not in self._artifact_chunks:
                    self._artifact_chunks[artifact.artifactId] = []
                self._artifact_chunks[artifact.artifactId].append(artifact)
        else:
            # we received an append chunk, add to the existing temp artifact
            current_temp_artifact = self._artifact_chunks[artifact.artifactId][
                -1
            ]
            # TODO handle if current_temp_artifact is missing
            current_temp_artifact.parts.extend(artifact.parts)
            if task_update_event.lastChunk:
                if current_task.artifacts:
                    current_task.artifacts.append(current_temp_artifact)
                else:
                    current_task.artifacts = [current_temp_artifact]
                del self._artifact_chunks[artifact.artifactId][-1]

    def add_event(self, event: Event):
        self._events[event.id] = event

    def get_conversation(
        self, conversation_id: Optional[str]
    ) -> Optional[Conversation]:
        if not conversation_id:
            return None
        return next(
            filter(
                lambda c: c and c.conversation_id == conversation_id,
                self._conversations,
            ),
            None,
        )

    def get_pending_messages(self) -> list[tuple[str, str]]:
        rval = []
        for message_id in self._pending_message_ids:
            if message_id in self._task_map:
                task_id = self._task_map[message_id]
                task = next(
                    filter(lambda x: x.id == task_id, self._tasks), None
                )
                if not task:
                    rval.append((message_id, ''))
                elif task.history and task.history[-1].parts:
                    if len(task.history) == 1:
                        rval.append((message_id, 'Working...'))
                    else:
                        part = task.history[-1].parts[0]
                        rval.append(
                            (
                                message_id,
                                part.root.text
                                if part.root.kind == 'text'
                                else 'Working...',
                            )
                        )
            else:
                rval.append((message_id, ''))
        return rval

    def register_agent(self, url):
        agent_data = get_agent_card(url)
        # Prefer the user-supplied URL. Some agents advertise their own
        # address (often "http://localhost:...") which is not reachable
        # from inside Docker containers. Store the provided URL so the
        # host uses the network-reachable address (for example
        # host.docker.internal) when making outbound calls.
        agent_data.url = url
        self._agents.append(agent_data)
        self._host_agent.register_agent_card(agent_data)
        # persist list so it survives restarts
        self._save_agents_to_disk()
        # Now update the host agent definition
        self._initialize_host()

    def delete_agent(self, name_or_url: str):
        # remove by name or url
        to_remove = None
        for a in self._agents:
            if a.name == name_or_url or a.url == name_or_url:
                to_remove = a
                break
        if not to_remove:
            # try matching by substring
            for a in self._agents:
                if name_or_url in (a.name or '') or name_or_url in (a.url or ''):
                    to_remove = a
                    break
        if not to_remove:
            raise ValueError('Agent not found')
        try:
            self._agents.remove(to_remove)
        except ValueError:
            pass
        # update host agent connections if present
        try:
            if to_remove.name in self._host_agent.remote_agent_connections:
                del self._host_agent.remote_agent_connections[to_remove.name]
            if to_remove.name in self._host_agent.cards:
                del self._host_agent.cards[to_remove.name]
        except Exception:
            pass
        # persist and reinitialize host
        self._save_agents_to_disk()
        self._initialize_host()

    @property
    def agents(self) -> list[AgentCard]:
        return self._agents

    @property
    def conversations(self) -> list[Conversation]:
        return self._conversations

    @property
    def tasks(self) -> list[Task]:
        return self._tasks

    @property
    def events(self) -> list[Event]:
        return sorted(self._events.values(), key=lambda x: x.timestamp)

    def adk_content_from_message(self, message: Message) -> types.Content:
        parts: list[types.Part] = []
        for p in message.parts:
            part = p.root
            if part.kind == 'text':
                parts.append(types.Part.from_text(text=part.text))
            elif part.kind == 'data':
                json_string = json.dumps(part.data)
                parts.append(types.Part.from_text(text=json_string))
            elif part.kind == 'file':
                if isinstance(part.file, FileWithUri):
                    parts.append(
                        types.Part.from_uri(
                            file_uri=part.file.uri,
                            mime_type=part.file.mimeType,
                        )
                    )
                else:
                    parts.append(
                        types.Part.from_bytes(
                            data=part.file.bytes.encode('utf-8'),
                            mime_type=part.file.mimeType,
                        )
                    )
        return types.Content(parts=parts, role=message.role)

    async def adk_content_to_message(
        self,
        content: types.Content,
        context_id: str | None,
        task_id: str | None,
    ) -> Message:
        parts: list[Part] = []
        if not content.parts:
            return Message(
                parts=[],
                role=content.role if content.role == Role.user else Role.agent,
                contextId=context_id,
                taskId=task_id,
                messageId=str(uuid.uuid4()),
            )
        for part in content.parts:
            if part.text:
                # try parse as data
                try:
                    data = json.loads(part.text)
                    parts.append(Part(root=DataPart(data=data)))
                except:
                    parts.append(Part(root=TextPart(text=part.text)))
            elif part.inline_data:
                parts.append(
                    Part(
                        root=FilePart(
                            file=FileWithBytes(
                                bytes=part.inline_data.decode('utf-8'),
                                mimeType=part.file_data.mime_type,
                            ),
                        )
                    )
                )
            elif part.file_data:
                parts.append(
                    Part(
                        root=FilePart(
                            file=FileWithUri(
                                uri=part.file_data.file_uri,
                                mimeType=part.file_data.mime_type,
                            )
                        )
                    )
                )
            # These aren't managed by the A2A message structure, these are internal
            # details of ADK, we will simply flatten these to json representations.
            elif part.video_metadata:
                parts.append(
                    Part(root=DataPart(data=part.video_metadata.model_dump()))
                )
            elif part.thought:
                parts.append(Part(root=TextPart(text='thought')))
            elif part.executable_code:
                parts.append(
                    Part(root=DataPart(data=part.executable_code.model_dump()))
                )
            elif part.function_call:
                parts.append(
                    Part(root=DataPart(data=part.function_call.model_dump()))
                )
            elif part.function_response:
                parts.extend(
                    await self._handle_function_response(
                        part, context_id, task_id
                    )
                )
            else:
                raise ValueError('Unexpected content, unknown type')
        return Message(
            role=content.role if content.role == Role.user else Role.agent,
            parts=parts,
            contextId=context_id,
            taskId=task_id,
            messageId=str(uuid.uuid4()),
        )

    async def _handle_function_response(
        self, part: types.Part, context_id: str | None, task_id: str | None
    ) -> list[Part]:
        parts = []
        try:
            for p in part.function_response.response['result']:
                if isinstance(p, str):
                    parts.append(Part(root=TextPart(text=p)))
                elif isinstance(p, dict):
                    if 'kind' in p and p['kind'] == 'file':
                        parts.append(Part(root=FilePart(**p)))
                    else:
                        parts.append(Part(root=DataPart(data=p)))
                elif isinstance(p, DataPart):
                    if 'artifact-file-id' in p.data:
                        file_part = await self._artifact_service.load_artifact(
                            user_id=self.user_id,
                            session_id=context_id,
                            app_name=self.app_name,
                            filename=p.data['artifact-file-id'],
                        )
                        file_data = file_part.inline_data
                        base64_data = base64.b64encode(file_data.data).decode(
                            'utf-8'
                        )
                        parts.append(
                            Part(
                                root=FilePart(
                                    file=FileWithBytes(
                                        bytes=base64_data,
                                        mimeType=file_data.mime_type,
                                        name='artifact_file',
                                    )
                                )
                            )
                        )
                    else:
                        parts.append(Part(root=DataPart(data=p.data)))
                else:
                    content = Message(
                        parts=[Part(root=TextPart(text='Unknown content'))],
                        role=Role.agent,
                        messageId=str(uuid.uuid4()),
                        taskId=task_id,
                        contextId=context_id,
                    )
        except Exception as e:
            print("Couldn't convert to messages:", e)
            parts.append(
                Part(root=DataPart(data=part.function_response.model_dump()))
            )
        return parts

    def process_message_threadsafe(self, message: Message, loop: asyncio.AbstractEventLoop):
        """Safely run process_message from a thread using the given event loop."""
        self.logger.info(f"Processing message for user {self.user_id}, conversation {message.contextId}")
        future = asyncio.run_coroutine_threadsafe(self.process_message(message), loop)
        return future  # You can call future.result() to get the result if needed

    def _agents_file_path(self) -> str:
        # store under ui/data/agents.json (create data dir if missing)
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data'))
        os.makedirs(base, exist_ok=True)
        return os.path.join(base, 'agents.json')

    def _conversations_file_path(self) -> str:
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data'))
        os.makedirs(base, exist_ok=True)
        return os.path.join(base, f'conversation-{self.user_id}.json')

    def _save_agents_to_disk(self) -> None:
        try:
            payload = [a.model_dump() for a in self._agents]
        except Exception:
            # fallback for older pydantic
            payload = [a.dict() for a in self._agents]
        path = self._agents_file_path()
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)

    def _load_agents_from_disk(self) -> None:
        path = self._agents_file_path()
        if not os.path.exists(path):
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            return
        for d in data:
            try:
                # Recreate AgentCard (pydantic v2)
                agent = AgentCard.model_validate(d)
            except Exception:
                agent = AgentCard(**d)
            # avoid duplicates
            if not any(a.name == agent.name for a in self._agents):
                self._agents.append(agent)
                # register into host runtime so it's available immediately
                try:
                    self._host_agent.register_agent_card(agent)
                except Exception:
                    pass

    def _save_conversations_to_disk(self) -> None:
        """Save conversations to disk."""
        path = self._conversations_file_path()
        self.logger.info(f"Saving conversations to {path}")
        conversation_data = []
        for c in self._conversations:
            try:
                conversation_data.append(c.model_dump())
            except Exception:
                conversation_data.append(c.dict())
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(conversation_data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)

    def _load_conversations_from_disk(self) -> None:
        path = self._conversations_file_path()
        self.logger.info(f"Loading conversations from {path}")
        if not os.path.exists(path):
            self.logger.warning(f"Conversation file not found: {path}")
            raise FileNotFoundError(f"Conversation file not found: {path}")
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.logger.info(f"Successfully loaded {len(data)} conversations from disk")
        except Exception as e:
            raise Exception(f"Error reading conversation file: {e}")
        for d in data:
            try:
                conv = Conversation.model_validate(d)
            except Exception:
                conv = Conversation(**d)
            # avoid duplicates
            if not any(c.conversation_id == conv.conversation_id for c in self._conversations):
                self._conversations.append(conv)
                # ensure a session exists in the session service for this conversation id
                try:
                    # create a session with the same id so ADK session state aligns
                    # create_session will return existing or new session with given id
                    # use sync helper by calling create_session sync through asyncio
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # schedule background creation
                        asyncio.create_task(self._session_service.create_session(app_name=self.app_name, user_id=self.user_id, session_id=conv.conversation_id))
                    else:
                        loop.run_until_complete(self._session_service.create_session(app_name=self.app_name, user_id=self.user_id, session_id=conv.conversation_id))
                except Exception:
                    pass

    def delete_conversation(self, conversation_id: str | None):
        if not conversation_id:
            raise ValueError('No conversation id provided')
        to_remove = None
        for c in self._conversations:
            if c.conversation_id == conversation_id:
                to_remove = c
                break
        if not to_remove:
            raise ValueError('Conversation not found')
        try:
            self._conversations.remove(to_remove)
        except ValueError:
            pass
        try:
            self._save_conversations_to_disk()
        except Exception:
            pass

def get_message_id(m: Message | None) -> str | None:
    if not m or not m.metadata or 'message_id' not in m.metadata:
        return None
    return m.metadata['message_id']


def task_still_open(task: Task | None) -> bool:
    if not task:
        return False
    return task.status.state in [
        TaskState.submitted,
        TaskState.working,
        TaskState.input_required,
    ]
