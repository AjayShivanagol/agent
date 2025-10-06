import logging
import asyncio
from typing import Any
from uuid import uuid4
 
import streamlit as st
import httpx
 
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import AgentCard, MessageSendParams, SendMessageRequest
 
# ---------- Custom CSS ----------
CUSTOM_CSS = """
<style>
    .main {
        background-color: #f8f9fa;
        font-family: 'Segoe UI', sans-serif;
    }
    .stTextInput > div > div > input {
        border-radius: 8px;
        border: 1px solid #ccc;
        padding: 0.5rem;
        font-size: 1rem;
    }
    .stButton>button {
        background-color: gray;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 0.6rem 1.2rem;
        font-size: 1rem;
        transition: background-color 0.3s;
    }
    .stButton>button:hover {
        background-color: #C0C0C0;
    }
    .chat-bubble-user {
        background-color: #ceede0;
        padding: 0.8rem;
        margin-bottom: 0.5rem;
        text-align: right;
    }
    .chat-bubble-agent {
        background-color: #cedded;
        padding: 0.8rem;
        margin-bottom: 0.5rem;
        border: 0.5px solid #ddd;
    }
    .chat-icon {
        width: 28px;
        height: 28px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 14px;
        margin-right: 0.5rem;
    }
    .agent-icon {
        width: 40;
        height: 40;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 14px;
        margin-right: 0.5rem;
    }
 
</style>
"""
 
# ---------- Async function to send message ----------
async def send_message(client: A2AClient, message: str, context_id: str | None):
    send_message_payload: dict[str, Any] = {
        'message': {
            'role': 'user',
            'parts': [{'kind': 'text', 'text': message}],
            'messageId': uuid4().hex,
        },
    }
    if context_id:
        send_message_payload['contextId'] = context_id
 
    request = SendMessageRequest(
        id=str(uuid4()), params=MessageSendParams(**send_message_payload)
    )
    response = await client.send_message(request)
 
    task = response.root.result
    if task and task.context_id and not context_id:
        context_id = task.context_id
 
    agent_response_text = "No message received."
    if task and hasattr(task, 'artifacts') and task.artifacts:
        try:
            final_answer = task.artifacts[0].parts[0].root.text
            agent_response_text = final_answer
        except (IndexError, AttributeError):
            agent_response_text = "Could not parse the final artifact."
    elif task and task.status and task.status.message:
        agent_response_text = task.status.message.text
 
    return agent_response_text, context_id
 
# ---------- Streamlit UI ----------
def main():
    logging.basicConfig(level=logging.INFO)
    st.set_page_config(page_title="CSC Agent", page_icon="🤖", layout="centered")
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
 
    st.title("🤖 CSC Agent")
    st.write("Ask your question below and receive responses instantly.")
 
    # Session state initialization
    if "client" not in st.session_state:
        base_url = 'http://localhost:10006'  # Match your backend port
        st.session_state.httpx_client = httpx.AsyncClient(timeout=180.0)
 
        resolver = A2ACardResolver(httpx_client=st.session_state.httpx_client, base_url=base_url)
        try:
            public_card: AgentCard = asyncio.get_event_loop().run_until_complete(resolver.get_agent_card())
        except RuntimeError:  # For fresh loop in Streamlit
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            public_card: AgentCard = loop.run_until_complete(resolver.get_agent_card())
 
        st.session_state.client = A2AClient(httpx_client=st.session_state.httpx_client, agent_card=public_card)
        st.session_state.context_id = None
        st.session_state.chat_history = []
 
    # Show chat history above input
    # Add each message inside the same container
    for sender, message in st.session_state.chat_history:
        if sender == "user":
            st.markdown(
                f"<div class='chat-bubble-user'>"
                f"<span class='chat-icon user-icon'>👤</span>{message}</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"<div class='chat-bubble-agent'>"
                f"<span class='chat-icon agent-icon'>🤖</span>{message}</div>",
                unsafe_allow_html=True
            )
 
    # Initialize session state for input
    if "user_input" not in st.session_state:
        st.session_state.user_input = ""
 
    # Text input with watermark/placeholder
    user_input = st.text_input(
        label="",
        value=st.session_state.user_input,  # keeps the state
        placeholder="Type your question here..."
    )
 
    if st.button("Send") and user_input.strip():
       
        st.session_state.user_input = ""
        st.session_state.chat_history.append(("user", user_input))
 
        with st.spinner("💡 Thinking..."):
            try:
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
 
                response_text, new_context_id = loop.run_until_complete(
                    send_message(st.session_state.client, user_input, st.session_state.context_id)
                )
 
                st.session_state.chat_history.append(("agent", response_text))
                st.session_state.context_id = new_context_id
 
                st.rerun()  # Refresh UI so new message appears above
            except Exception as e:
                st.error(f"Error during request: {e}")
 
if __name__ == "__main__":
    main()