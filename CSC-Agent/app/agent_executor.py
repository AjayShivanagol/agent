import logging

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    InternalError,
    InvalidParamsError,
    Part,
    Task,
    TaskState,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils import (
    new_agent_text_message,
    new_task,
)
from a2a.utils.errors import ServerError

# FIX: Changed import from CurrencyAgent to CostingAgent
from app.agent import CostingAgent


from app.logger.logger_config import setup_logger
logger= setup_logger("INFO")


# FIX: Renamed the class from CurrencyAgentExecutor to CostingAgentExecutor
class CostingAgentExecutor(AgentExecutor):
    """Costing Data AgentExecutor Example."""

    def __init__(self):
        # FIX: Updated to initialize CostingAgent
        self.agent = CostingAgent()

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        error = self._validate_request(context)
        if error:
            raise ServerError(error=InvalidParamsError())

        query = context.get_user_input()
        logger.info(f'User query:{query}')
        task = context.current_task
        if not task:
            task = new_task(context.message)
            logger.info(f'Task:{task}')
            await event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue, task.id, task.contextId)
        logger.info(f"Task captured")
        try:
            logger.info(f"Entered try catch")
            async for item in self.agent.stream(query, task.contextId):
                logger.info(f"Entered streaming")
                is_task_complete = item['is_task_complete']
                require_user_input = item['require_user_input']
                logger.info(f" is task complete: {is_task_complete}")
                logger.info(f"require user input: {require_user_input}")
                

                if not is_task_complete and not require_user_input:
                    logger.info('inside working')
                    await updater.update_status(
                        TaskState.working,
                        new_agent_text_message(
                            item['content'],
                            task.contextId,
                            task.id,
                        ),
                    )
                elif require_user_input:
                    logger.info('inside input required')
                    await updater.update_status(
                        TaskState.input_required,
                        new_agent_text_message(
                            item['content'],
                            task.contextId,
                            task.id,
                        ),
                        final=True,
                    )
                    break
                else:
                    logger.info('inside complete')
                    
                    # Add Agent Judge evaluation before completing the task
                    try:
                        logger.info('Sending response to Agent Judge for evaluation')
                        await self._evaluate_with_agent_judge(
                            query, item['content'], updater, task.contextId, task.id
                        )
                    except Exception as eval_error:
                        logger.warning(f'Agent Judge evaluation failed: {eval_error}')
                    
                    await updater.add_artifact(
                        [Part(root=TextPart(text=item['content']))],
                        name='costing_result',
                    )
                    await updater.complete()
                    break

        except Exception as e:
            logger.error(f'An error occurred while streaming the response: {e}')
            raise ServerError(error=InternalError()) from e

    def _validate_request(self, context: RequestContext) -> bool:
        return False

    async def cancel(
        self, request: RequestContext, event_queue: EventQueue
    ) -> Task | None:
        raise ServerError(error=UnsupportedOperationError())
    
    async def _evaluate_with_agent_judge(
        self, 
        user_query: str, 
        agent_response: str, 
        updater: TaskUpdater, 
        context_id: str, 
        task_id: str
    ):
        """Send the agent response to Agent Judge for evaluation using A2A client"""
        try:
            import httpx
            from a2a.client import A2AClient, A2ACardResolver
            from uuid import uuid4
            
            # Show evaluation starting
            await updater.update_status(
                TaskState.working,
                new_agent_text_message(
                    "🤖 Agent Judge is evaluating the response...",
                    context_id,
                    task_id,
                ),
            )
            
            # Prepare the evaluation input in the format Agent Judge expects
            evaluation_input = f"{user_query}|||{agent_response}"
            
            # Use A2A client
            async with httpx.AsyncClient() as httpx_client:
                # Get Agent Judge card and create client
                card_resolver = A2ACardResolver(httpx_client, "http://localhost:10001/")
                card = await card_resolver.get_agent_card()
                client = A2AClient(httpx_client, agent_card=card)
                
                # Create message using A2A types
                from a2a.types import (
                    Message, TextPart, MessageSendParams, 
                    MessageSendConfiguration, SendMessageRequest
                )
                
                message = Message(
                    role="user",
                    parts=[TextPart(text=evaluation_input)],
                    messageId=str(uuid4()),
                    taskId=None,
                    contextId=f"judge_eval_{context_id}",
                )
                
                # Create request payload
                payload = MessageSendParams(
                    id=str(uuid4()),
                    message=message,
                    configuration=MessageSendConfiguration(
                        acceptedOutputModes=["text"],
                    ),
                )
                
                # Send message to Agent Judge
                event = await client.send_message(
                    SendMessageRequest(
                        id=str(uuid4()),
                        params=payload,
                    )
                )
                
                # Check if we got an error response
                from a2a.types import JSONRPCErrorResponse
                if isinstance(event.root, JSONRPCErrorResponse):
                    logger.error(f"Agent Judge returned JSONRPC error: {event.root.error}")
                    await updater.update_status(
                        TaskState.working,
                        new_agent_text_message(
                            f"⚠️ Agent Judge evaluation failed: {event.root.error.message}",
                            context_id,
                            task_id,
                        ),
                    )
                    return
                
                # Parse successful response
                result = event.root.result
                evaluation_content = ""
                
                # Handle different response types
                if hasattr(result, 'message') and result.message:
                    # Extract evaluation content from message parts
                    if result.message.parts:
                        for part in result.message.parts:
                            if hasattr(part, 'text'):
                                evaluation_content += part.text
                            elif hasattr(part, 'root') and hasattr(part.root, 'text'):
                                evaluation_content += part.root.text
                elif hasattr(result, 'content'):
                    evaluation_content = result.content
                elif hasattr(result, 'text'):
                    evaluation_content = result.text
                elif isinstance(result, str):
                    evaluation_content = result
                
                if evaluation_content:
                    # Display the evaluation result
                    await updater.update_status(
                        TaskState.working,
                        new_agent_text_message(
                            f"📊 **Agent Judge Evaluation:**\n\n{evaluation_content}",
                            context_id,
                            task_id,
                        ),
                    )
                    logger.info(f"Agent Judge evaluation completed: {evaluation_content[:100]}...")
                else:
                    logger.warning(f"Agent Judge response contained no readable content: {result}")
                    # Log the full response structure for debugging
                    logger.debug(f"Full Agent Judge response: {event.root}")
                    
        except Exception as e:
            logger.error(f"Error calling Agent Judge: {e}")
            await updater.update_status(
                TaskState.working,
                new_agent_text_message(
                    f"⚠️ Agent Judge evaluation failed: {str(e)}",
                    context_id,
                    task_id,
                ),
            )