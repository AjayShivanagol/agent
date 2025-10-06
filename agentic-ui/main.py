"""A UI solution and host service to interact with the agent framework.
run:
  uv main.py
"""

import os
import base64
import json
import httpx
from contextlib import asynccontextmanager

import mesop as me
from fastapi import Request

from components.api_key_dialog import api_key_dialog
from components.mbui_page_scaffold import mbui_page_scaffold
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.wsgi import WSGIMiddleware
from pages.agent_list import agent_list_page
from pages.conversation import conversation_page
from pages.event_list import event_list_page
from pages.home import home_page_content
from pages.settings import settings_page_content
from pages.task_list import task_list_page
from service.server.server import ConversationServer
from state import host_agent_service
from state.state import AppState
from utils.request_context import current_userinfo


# load_dotenv()
load_dotenv("/vault/secrets/envvar")


def on_load(e: me.LoadEvent):  # pylint: disable=unused-argument
    """On load event"""
    state = me.state(AppState)
    me.set_theme_mode(state.theme_mode)
    
    # Show footer by default on all pages except conversation
    if me.query_params.get('conversation_id') or '/conversation' in e.path:
        state.show_footer = False
    else:
        state.show_footer = True
    
    if 'conversation_id' in me.query_params:
        state.current_conversation_id = me.query_params['conversation_id']
    else:
        state.current_conversation_id = ''

    # check if the API key is set in the environment
    # and if the user is using Vertex AI
    uses_vertex_ai = (
        os.getenv('GOOGLE_GENAI_USE_VERTEXAI', '').upper() == 'TRUE'
    )
    api_key = os.getenv('GOOGLE_API_KEY', '')

    if uses_vertex_ai:
        state.uses_vertex_ai = True
    elif api_key:
        state.api_key = api_key
    else:
        # Show the API key dialog if both are not set
        state.api_key_dialog_open = True


# Policy to allow the lit custom element to load
security_policy = me.SecurityPolicy(
    allowed_script_srcs=[
        'https://cdn.jsdelivr.net',
    ]
)


@me.page(
    path='/',
    title='Chat',
    on_load=on_load,
    security_policy=security_policy,
)
def home_page():
    """Home Page"""
    # Ensure footer is shown on home page
    state = me.state(AppState)
    state.show_footer = True
    
    api_key_dialog()
    with mbui_page_scaffold():  # pylint: disable=not-context-manager
        home_page_content(me.state(AppState))


@me.page(
    path='/agents',
    title='Agents',
    on_load=on_load,
    security_policy=security_policy,
)
def another_page():
    """Another Page"""
    # Ensure footer is shown on agents page
    state = me.state(AppState)
    state.show_footer = True
    
    api_key_dialog()
    with mbui_page_scaffold():  # pylint: disable=not-context-manager
        agent_list_page(me.state(AppState))


@me.page(
    path='/conversation',
    title='Conversation',
    on_load=on_load,
    security_policy=security_policy,
)
def chat_page():
    """Conversation Page."""
    # Ensure footer is hidden on conversation page
    state = me.state(AppState)
    state.show_footer = False
    
    api_key_dialog()
    with mbui_page_scaffold():  # pylint: disable=not-context-manager
        conversation_page(me.state(AppState))


@me.page(
    path='/event_list',
    title='Event List',
    on_load=on_load,
    security_policy=security_policy,
)
def event_page():
    """Event List Page."""
    # Ensure footer is shown on event list page
    state = me.state(AppState)
    state.show_footer = True
    
    api_key_dialog()
    with mbui_page_scaffold():  # pylint: disable=not-context-manager
        event_list_page(me.state(AppState))


@me.page(
    path='/settings',
    title='Settings',
    on_load=on_load,
    security_policy=security_policy,
)
def settings_page():
    """Settings Page."""
    # Ensure footer is shown on settings page
    state = me.state(AppState)
    state.show_footer = True
    
    api_key_dialog()
    with mbui_page_scaffold():  # pylint: disable=not-context-manager
        settings_page_content()


@me.page(
    path='/task_list',
    title='Task List',
    on_load=on_load,
    security_policy=security_policy,
)
def task_page():
    """Task List Page."""
    # Ensure footer is shown on task list page
    state = me.state(AppState)
    state.show_footer = True
    
    api_key_dialog()
    with mbui_page_scaffold():  # pylint: disable=not-context-manager
        task_list_page(me.state(AppState))


class HTTPXClientWrapper:
    """Wrapper to return the singleton client where needed."""

    async_client: httpx.AsyncClient = None

    def start(self):
        """ Instantiate the client. Call from the FastAPI startup hook."""
        self.async_client = httpx.AsyncClient(timeout=30)

    async def stop(self):
        """ Gracefully shutdown. Call from FastAPI shutdown hook."""
        await self.async_client.aclose()
        self.async_client = None

    def __call__(self):
        """ Calling the instantiated HTTPXClientWrapper returns the wrapped singleton."""
        # Ensure we don't use it if not started / running
        assert self.async_client is not None
        return self.async_client


# Setup the server global objects
httpx_client_wrapper = HTTPXClientWrapper()
agent_server = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    httpx_client_wrapper.start()
    agent_server = ConversationServer(app, httpx_client_wrapper())
    app.openapi_schema = None
    app.mount(
        '/',
        WSGIMiddleware(
            me.create_wsgi_app(
                debug_mode=os.environ.get('DEBUG_MODE', '') == 'true'
            )
        ),
    )
    app.setup()
    yield
    await httpx_client_wrapper.stop()

if __name__ == '__main__':
    import uvicorn

    app = FastAPI(lifespan=lifespan)

    # Middleware to capture x-userinfo/userinfo from every incoming request
    @app.middleware("http")
    async def capture_userinfo(request: Request, call_next):
        try:
            # Prefer headers, then cookies, then raw Cookie header
            hdr = request.headers.get('x-userinfo') or request.headers.get('userinfo')
            if not hdr and hasattr(request, 'cookies'):
                hdr = request.cookies.get('x-userinfo') or request.cookies.get('userinfo')
            if not hdr:
                raw_cookie = request.headers.get('cookie')
                if raw_cookie:
                    for part in raw_cookie.split(';'):
                        name, _, value = part.strip().partition('=')
                        lname = name.lower()
                        if lname in ('x-userinfo', 'userinfo'):
                            hdr = value
                            break
            # Set into context for downstream internal HTTP calls
            current_userinfo.set(hdr or '')
        except Exception:
            current_userinfo.set('')
        response = await call_next(request)
        return response

    # Setup the connection details, these should be set in the environment
    host = os.environ.get('A2A_UI_HOST', '0.0.0.0')
    port = int(os.environ.get('A2A_UI_PORT', '12000'))

    # Set the client to talk to the server
    host_agent_service.server_url = f'http://{host}:{port}'

    uvicorn.run(
        app,
        host=host,
        port=port,
        timeout_graceful_shutdown=0,
    )
