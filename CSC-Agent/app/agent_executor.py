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

logger = setup_logger("INFO")


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

    