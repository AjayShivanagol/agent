import logging
import asyncio
from typing import Any, List, Dict
from uuid import uuid4
import os
import json

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
# Add a constant to limit the history size for robustness
MAX_HISTORY_MESSAGES = 10  # 5 turns (user + model)


async def main() -> None:
    # Configure logging to show INFO level messages
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)  # Get a logger instance

    base_url = 'http://localhost:10006' # Ensure this matches your __main__.py port

    async with httpx.AsyncClient(timeout=60.0) as httpx_client:
        # --- This section for getting the agent card remains the same ---
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=base_url,
        )
        final_agent_card_to_use: AgentCard | None = None
        try:
            _public_card = (
                await resolver.get_agent_card()
            )  # Fetches from default public path
            final_agent_card_to_use = _public_card
        except Exception as e:
            logger.error(f"Critical error fetching agent card: {e}", exc_info=True)
            return

        client = A2AClient(
            httpx_client=httpx_client, agent_card=final_agent_card_to_use
        )
        logger.info('A2AClient initialized. Type "quit" or "exit" to end the conversation.')

        # --- START: CORRECTED CONVERSATIONAL LOOP ---

        context_id: str | None = None
        chat_history: List[Dict[str, Any]] = []

        while True:
            try:
                # Clear the screen and print the conversation history
                # os.system('cls' if os.name == 'nt' else 'clear')
                if chat_history:
                    print("\n--- Conversation History ---")
                    # Display the most recent messages from history
                    for message in chat_history[-MAX_HISTORY_MESSAGES:]:
                        role = message.get('role', 'unknown').capitalize()
                        text = message.get('parts', [{}])[0].get('text', '')
                        print(f"{role}: {text}")
                    print("--------------------------\n")

                # Get user input
                user_input = await asyncio.to_thread(input, "You: ")

                if user_input.lower() in ["quit", "exit"]:
                    print("Exiting conversation.")
                    break
                
                if not user_input.strip():
                    continue

                # The user_message object already has the correct structure
                user_message = {
                    'role': 'user',
                    'parts': [{'kind': 'text', 'text': user_input}],
                    'messageId': uuid4().hex,
                }

                # Add the context_id TO THE MESSAGE OBJECT after the first turn
                if context_id:
                    user_message['context_id'] = context_id

                # The payload now correctly matches the MessageSendParams schema
                send_message_payload: dict[str, Any] = {
                    'message': user_message,
                    # There is no 'history' field, so we remove it.
                }

                # This part remains the same
                request = SendMessageRequest(
                    id=str(uuid4()), params=MessageSendParams(**send_message_payload)
                )

                # MODIFICATION 2: Log the exact payload to debug what's being sent
                logger.info(f"Sending request payload:\n{json.dumps(send_message_payload, indent=2)}")
                # print(f"Sending request payload:\n{json.dumps(send_message_payload, indent=2)}")

                print("\nAgent is thinking...")
                response = await client.send_message(request)
                task = response.root.result

                if task and task.context_id and not context_id:
                    context_id = task.context_id
                    logger.info(f"Started new conversation with contextId: {context_id}")

                agent_response_text = "No message received."
                if task and hasattr(task, 'artifacts') and task.artifacts:
                    try:
                        final_answer = task.artifacts[0].parts[0].root.text
                        agent_response_text = final_answer
                    except (IndexError, AttributeError):
                        agent_response_text = "Could not parse the final artifact."
                
                agent_message = {
                    'role': 'model',
                    'parts': [{'kind': 'text', 'text': agent_response_text}]
                }
                print(f"Agent response: {agent_response_text}")
                chat_history.append(user_message)
                chat_history.append(agent_message)

            except KeyboardInterrupt:
                print("\nExiting conversation.")
                break
            except Exception as e:
                logger.error(f"An error occurred during the conversation: {e}", exc_info=True)
                break
        
        # --- END: CORRECTED CONVERSATIONAL LOOP ---

if __name__ == '__main__':
    asyncio.run(main())
