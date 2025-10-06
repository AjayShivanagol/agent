import logging
import asyncio
from typing import Any
from uuid import uuid4

import httpx

from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    AgentCard,
    MessageSendParams,
    SendMessageRequest,
    SendStreamingMessageRequest,
)


PUBLIC_AGENT_CARD_PATH = '/.well-known/agent.json'
EXTENDED_AGENT_CARD_PATH = '/agent/authenticatedExtendedCard'


async def main() -> None:
    # Configure logging to show INFO level messages
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)  # Get a logger instance

    # base_url = 'https://cscagent-int.app.corpintra.net/' # Ensure this matches your __main__.py port
    base_url = 'http://localhost:10006'
    # Define the path to your certificate file
    cert_path = r"C:/Users/vilakka/Desktop/CSC Agent/Development/CSC-Agent/cert/xcorp_root_CA_G2.crt"

    async with httpx.AsyncClient(timeout=180.0, verify=cert_path) as httpx_client:
        # --- This section for getting the agent card remains the same ---
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=base_url
        )
        final_agent_card_to_use: AgentCard | None = None
        try:
            _public_card = (
                await resolver.get_agent_card()
            )  # Fetches from default public path
            final_agent_card_to_use = _public_card
            # Override the agent card URL to match where the service is actually running

            if final_agent_card_to_use:
                final_agent_card_to_use.url = base_url
            # (Optional) Add extended card logic here if needed
        except Exception as e:
            logger.error(f"Critical error fetching agent card: {e}", exc_info=True)
            return

        client = A2AClient(
            httpx_client=httpx_client, agent_card=final_agent_card_to_use
        )
        logger.info('A2AClient initialized. Type "quit" or "exit" to end the conversation.')

        # --- START: MODIFIED CONVERSATIONAL LOOP ---

        context_id: str | None = None  # This will store the history ID for the conversation

# --- START: CORRECTED CONVERSATIONAL LOOP ---

        context_id: str | None = None  # This will store the history ID for the conversation
        chat_history = [] ##added for chat history
        while True:
            try:
                ##added for chat history
                # Clear the screen for a cleaner chat interface
                import os
                os.system('cls' if os.name == 'nt' else 'clear')
                # Print the entire conversation history
                if chat_history:
                    print("\n--- Conversation History ---")
                    for message in chat_history:
                        print(message)
                    print("--------------------------\n")
                ##added for chat history
                # Get user input without blocking the async event loop
                user_input = await asyncio.to_thread(input, "You: ")

                if user_input.lower() in ["quit", "exit"]:
                    print("Exiting conversation.")
                    break
                
                if not user_input.strip():
                    continue
                chat_history.append(f"You: {user_input}") ##added for chat history

                # Construct the message payload
                send_message_payload: dict[str, Any] = {
                    'message': {
                        'role': 'user',
                        'parts': [{'kind': 'text', 'text': user_input}],
                        'messageId': uuid4().hex,
                    },
                    'history': chat_history,
                }
                
                # After the first turn, add the contextId to maintain history
                if context_id:
                    send_message_payload['contextId'] = context_id

                request = SendMessageRequest(
                    id=str(uuid4()), params=MessageSendParams(**send_message_payload)
                )

                print("Agent is thinking...")
                response = await client.send_message(request)

                # Get the task object from the response
                # print(f"Response: {response}")
                
                # Handle JSONRPCErrorResponse
                if hasattr(response.root, 'error'):
                    error_msg = response.root.error
                    print(f"Agent Error: {error_msg}")
                    continue
                
                task = response.root.result
                # print(f"Task {task}")

                # Capture the contextId from the task to use in subsequent requests
                if task and task.context_id and not context_id:
                    context_id = task.context_id
                    logger.info(f"Started new conversation with contextId: {context_id}")

                # Find the agent's response message
                agent_response_text = "No message received."
                if task and task.status and task.status.message:
                    agent_response_text = task.status.message.text
                
                # Check for final artifacts (the final answer is often here)
                # print(f"Final Task: {task}")
                if task and hasattr(task, 'artifacts') and task.artifacts:
                    try:
                        # The text is nested inside parts -> root -> text
                        final_answer = task.artifacts[0].parts[0].root.text
                        agent_response_text = f"{final_answer}"
                    except (IndexError, AttributeError):
                        # Handle cases where artifact structure might be different
                        agent_response_text = "Could not parse the final artifact."
                
                chat_history.append(f"Agent: {agent_response_text}") ##added for chat history

                print(f"Agent: {agent_response_text}")

            except KeyboardInterrupt:
                print("\nExiting conversation.")
                break
            except Exception as e:
                logger.error(f"An error occurred during the conversation: {e}", exc_info=True)
                break
        
        # --- END: CORRECTED CONVERSATIONAL LOOP ---

if __name__ == '__main__':
    asyncio.run(main())