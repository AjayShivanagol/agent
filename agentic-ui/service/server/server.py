import asyncio
import base64
import logging
import os
import threading
import uuid
from typing import cast, Optional

import httpx

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from a2a.types import FilePart, FileWithUri, Message, Part
from fastapi import APIRouter, FastAPI, Request, Response, Header

from utils.user_info import get_user_id

from service.types import (
    CreateConversationResponse,
    GetEventResponse,
    ListAgentResponse,
    ListConversationResponse,
    ListMessageResponse,
    ListTaskResponse,
    MessageInfo,
    PendingMessageResponse,
    RegisterAgentResponse,
    DeleteAgentResponse,
    DeleteConversationResponse,
    SendMessageResponse,
)

from .adk_host_manager import ADKHostManager, get_message_id
from .application_manager import ApplicationManager
from .in_memory_manager import InMemoryFakeAgentManager


class ConversationServer:
    """ConversationServer is the backend to serve the agent interactions in the UI

    This defines the interface that is used by the Mesop system to interact with
    agents and provide details about the executions.
    """

    def __init__(self, app: FastAPI, http_client: httpx.AsyncClient):
        agent_manager = os.environ.get('A2A_HOST', 'ADK')
        self.logger = logging.getLogger('ConversationServer')
        # Maintain a manager per user_id to avoid cross-user interference
        self.managers: dict[str, ApplicationManager] = {}
        
        # Get API key from environment
        api_key = os.environ.get('GOOGLE_API_KEY', '')
        uses_vertex_ai = (
            os.environ.get('GOOGLE_GENAI_USE_VERTEXAI', '').upper() == 'TRUE'
        )

        self._agent_backend = agent_manager.upper()
        self._http_client = http_client
        self._api_key = api_key
        self._uses_vertex_ai = uses_vertex_ai
        self._file_cache = {}  # dict[str, FilePart] maps file id to message data
        self._message_to_cache = {}  # dict[str, str] maps message id to cache id

        app.add_api_route(
            '/conversation/create', self._create_conversation, methods=['POST']
        )
        app.add_api_route(
            '/conversation/list', self._list_conversation, methods=['POST']
        )
        app.add_api_route('/conversation/delete', self._delete_conversation, methods=['POST'])
        app.add_api_route('/message/send', self._send_message, methods=['POST'])
        app.add_api_route('/events/get', self._get_events, methods=['POST'])
        app.add_api_route(
            '/message/list', self._list_messages, methods=['POST']
        )
        app.add_api_route(
            '/message/pending', self._pending_messages, methods=['POST']
        )
        app.add_api_route('/task/list', self._list_tasks, methods=['POST'])
        app.add_api_route(
            '/agent/register', self._register_agent, methods=['POST']
        )
        app.add_api_route('/agent/list', self._list_agents, methods=['POST'])
        app.add_api_route('/agent/delete', self._delete_agent, methods=['POST'])
        app.add_api_route(
            '/message/file/{file_id}', self._files, methods=['GET']
        )
        app.add_api_route(
            '/api_key/update', self._update_api_key, methods=['POST']
        )

    def _extract_userinfo(self, request: Request) -> str:
        """Get x-userinfo from header or cookies.
        Priority: header -> cookies dict -> raw Cookie header.
        """
        # 1) Check headers: prefer 'x-userinfo', but accept 'userinfo' for compatibility
        header_val = request.headers.get('x-userinfo') or request.headers.get('userinfo')
        if header_val:
            return header_val
        # FastAPI parses cookies into request.cookies
        if hasattr(request, 'cookies'):
            cookie_val = request.cookies.get('x-userinfo') or request.cookies.get('userinfo')
            if cookie_val:
                return cookie_val
        # Fallback: parse raw Cookie header
        raw_cookie = request.headers.get('cookie')
        if raw_cookie:
            for part in raw_cookie.split(';'):
                name, _, value = part.strip().partition('=')
                lname = name.lower()
                if lname == 'x-userinfo' or lname == 'userinfo':
                    return value
        return ''

    def _get_user_id_from_request(self, request: Request) -> str:
        # Extract without logging sensitive headers/cookies or token contents
        userinfo_header = self._extract_userinfo(request)
        user_id = get_user_id(userinfo_header)
        return user_id

    # Update API key in manager
    def update_api_key(self, api_key: str):
        # Update all managers for consistency
        for m in self.managers.values():
            if isinstance(m, ADKHostManager):
                m.update_api_key(api_key)

    def _get_manager_for_user(self, user_id: str) -> ApplicationManager:
        uid = user_id or 'test_user'
        if uid in self.managers:
            return self.managers[uid]
        # Create a new manager for this user
        if self._agent_backend == 'ADK':
            manager = ADKHostManager(
                self._http_client,
                api_key=self._api_key,
                uses_vertex_ai=self._uses_vertex_ai,
                user_id=uid,
            )
        else:
            manager = InMemoryFakeAgentManager()
        self.managers[uid] = manager
        return manager

    async def _create_conversation(self, request: Request):
        # Extract user info from header or cookie
        user_id = self._get_user_id_from_request(request)
        self.logger.info(f"[_create_conversation] user_id: {user_id}")
        
        manager = self._get_manager_for_user(user_id)
        c = await manager.create_conversation()
        return CreateConversationResponse(result=c)

    async def _send_message(self, request: Request):
        # Extract user info from header or cookie
        user_id = self._get_user_id_from_request(request)
        self.logger.info(f"[_send_message] user_id: {user_id}")
        
        manager = self._get_manager_for_user(user_id)
        message_data = await request.json()
        message = Message(**message_data['params'])
        message = manager.sanitize_message(message)
        loop = asyncio.get_event_loop()
        if isinstance(manager, ADKHostManager):
            t = threading.Thread(
                target=lambda: cast(ADKHostManager, manager).process_message_threadsafe(message, loop)
            )
        else:
            t = threading.Thread(
                target=lambda: asyncio.run(manager.process_message(message))
            )
        t.start()
        return SendMessageResponse(
            result=MessageInfo(
                message_id=message.messageId,
                context_id=message.contextId if message.contextId else '',
            )
        )

    async def _list_messages(self, request: Request):
        # Extract user info from header or cookie
        user_id = self._get_user_id_from_request(request)
        self.logger.info(f"[_list_messages] user_id: {user_id}")
        
        manager = self._get_manager_for_user(user_id)
        message_data = await request.json()
        conversation_id = message_data['params']
        conversation = manager.get_conversation(conversation_id)
        if conversation:
            return ListMessageResponse(
                result=self.cache_content(conversation.messages)
            )
        return ListMessageResponse(result=[])

    def cache_content(self, messages: list[Message]):
        rval = []
        for m in messages:
            message_id = get_message_id(m)
            if not message_id:
                rval.append(m)
                continue
            new_parts: list[Part] = []
            for i, p in enumerate(m.parts):
                part = p.root
                if part.kind != 'file':
                    new_parts.append(p)
                    continue
                message_part_id = f'{message_id}:{i}'
                if message_part_id in self._message_to_cache:
                    cache_id = self._message_to_cache[message_part_id]
                else:
                    cache_id = str(uuid.uuid4())
                    self._message_to_cache[message_part_id] = cache_id
                # Replace the part data with a url reference
                new_parts.append(
                    Part(
                        root=FilePart(
                            file=FileWithUri(
                                mimeType=part.file.mimeType,
                                uri=f'/message/file/{cache_id}',
                            )
                        )
                    )
                )
                if cache_id not in self._file_cache:
                    self._file_cache[cache_id] = part
            m.parts = new_parts
            rval.append(m)
        return rval

    async def _pending_messages(self, request: Request):
        # Extract user and return only that user's pending messages
        user_id = self._get_user_id_from_request(request)
        manager = self._get_manager_for_user(user_id)
        return PendingMessageResponse(
            result=manager.get_pending_messages()
        )

    async def _list_conversation(self, request: Request):
        # Extract user info from header or cookie
        user_id = self._get_user_id_from_request(request)
        self.logger.info(f"[_list_conversation] user_id: {user_id}")
        
        manager = self._get_manager_for_user(user_id)
        return ListConversationResponse(result=manager.conversations)

    async def _delete_conversation(self, request: Request):
        # Extract user info from header or cookie
        user_id = self._get_user_id_from_request(request)
        self.logger.info(f"[_delete_conversation] user_id: {user_id}")
        
        manager = self._get_manager_for_user(user_id)
        message_data = await request.json()
        conv_id = message_data.get('params')
        try:
            # manager should implement deletion and persistence
            manager.delete_conversation(conv_id)
            return DeleteConversationResponse(result='ok')
        except Exception as e:
            return DeleteConversationResponse(error={'code': 1, 'message': str(e)})

    async def _get_events(self, request: Request):
        # Extract user info from header or cookie
        user_id = self._get_user_id_from_request(request)
        
        manager = self._get_manager_for_user(user_id)
        return GetEventResponse(result=manager.events)

    async def _list_tasks(self, request: Request):
        # Extract user info from header or cookie
        user_id = self._get_user_id_from_request(request)
        
        manager = self._get_manager_for_user(user_id)
        return ListTaskResponse(result=manager.tasks)

    async def _register_agent(self, request: Request):
        message_data = await request.json()
        url = message_data['params']
        # Register agent in a default manager (admin action); use 'test_user'
        self._get_manager_for_user('test_user').register_agent(url)
        return RegisterAgentResponse()

    async def _delete_agent(self, request: Request):
        message_data = await request.json()
        name_or_url = message_data.get('params')
        # manager should implement delete behavior
        try:
            self._get_manager_for_user('test_user').delete_agent(name_or_url)
            return DeleteAgentResponse(result='ok')
        except Exception as e:
            return DeleteAgentResponse(error={'code': 1, 'message': str(e)})

    async def _list_agents(self, request: Request):
        # Extract user info from header or cookie
        user_id = self._get_user_id_from_request(request)
        
        manager = self._get_manager_for_user(user_id)
        return ListAgentResponse(result=manager.agents)

    async def _files(self, file_id, request: Request):
        # Extract user info from header or cookie
        user_id = self._get_user_id_from_request(request)
        manager = self._get_manager_for_user(user_id)
        if file_id not in self._file_cache:
            raise Exception('file not found')
        part = self._file_cache[file_id]
        if 'image' in part.file.mimeType:
            return Response(
                content=base64.b64decode(part.file.bytes),
                media_type=part.file.mimeType,
            )
        return Response(content=part.file.bytes, media_type=part.file.mimeType)

    async def _update_api_key(self, request: Request):
        """Update the API key"""
        try:
            data = await request.json()
            api_key = data.get('api_key', '')

            if api_key:
                # Update in the manager
                self.update_api_key(api_key)
                return {'status': 'success'}
            return {'status': 'error', 'message': 'No API key provided'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
