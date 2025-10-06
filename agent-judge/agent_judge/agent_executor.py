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

from agent_judge.judge import AgentJudge

class JudgeAgentExecutor(AgentExecutor):
    """Agent Judge Executor - Handles evaluation requests."""

    def __init__(self):
        self.agent = AgentJudge()

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        logging.info(f"Agent Judge execute called with context: {context}")
        logging.info(f"Message: {context.message}")
        
        error = self._validate_request(context)
        if error:
            logging.error(f"Validation failed: {error}")
            raise ServerError(error=InvalidParamsError())

        query = context.get_user_input()
        logging.info(f"User input extracted: {query}")
        
        task = context.current_task
        if not task:
            task = new_task(context.message)

        # Update task to working state
        updater = TaskUpdater(event_queue, task.id, task.contextId)
        
        await updater.update_status(
            TaskState.working,
            new_agent_text_message(
                "Processing evaluation request...",
                context.message.context_id,
                task.id,
            ),
        )

        try:
            logging.info(f"Calling agent with user_input: {query}")
            # Get agent evaluation (synchronous - typically 1-3 seconds)
            agent_response = self.agent.get_agent_response(
                user_input=query,
                conversation_id=task.id
            )
            logging.info(f"Agent response received: {agent_response}")

            # Create response message
            response_message = new_agent_text_message(
                agent_response['content'],
                context.message.context_id,
                task.id,
            )

            # Complete the task
            if agent_response['is_task_complete']:
                await updater.update_status(
                    TaskState.working,
                    response_message
                )
                await updater.complete()
                logging.info("Task completed successfully")
            else:
                await updater.update_status(
                    TaskState.input_required,
                    response_message,
                    final=True
                )
                logging.info("Task requires user input")

        except Exception as e:
            logging.error(f"Error during agent execution: {e}", exc_info=True)
            error_message = new_agent_text_message(
                f"An error occurred during evaluation: {str(e)}",
                context.message.context_id,
                task.id,
            )
            
            await updater.update_status(
                TaskState.working,
                error_message
            )
            # Don't complete on error - let the framework handle it

    async def cancel(self, task_id: str) -> None:
        """Cancel a running task."""
        # For Agent Judge, we don't have long-running tasks to cancel
        # This is a simple implementation that does nothing
        pass

    def _validate_request(self, context: RequestContext) -> ServerError | None:
        """Validate the incoming request."""
        logging.info(f"Validating request. Message: {context.message}")
        logging.info(f"Message parts: {context.message.parts}")
        
        if not context.message.parts:
            logging.error("No message parts found")
            return ServerError(error=InvalidParamsError())

        # Check for TextPart either directly or nested within Part objects
        text_parts = []
        for part in context.message.parts:
            if isinstance(part, TextPart):
                text_parts.append(part)
            elif hasattr(part, 'root') and isinstance(part.root, TextPart):
                text_parts.append(part.root)
        
        logging.info(f"Text parts found: {len(text_parts)}")
        logging.info(f"Text parts content: {[tp.text for tp in text_parts]}")
        
        if not text_parts:
            logging.error("No text parts found")
            return ServerError(error=UnsupportedOperationError())

        logging.info("Request validation passed")
        return None