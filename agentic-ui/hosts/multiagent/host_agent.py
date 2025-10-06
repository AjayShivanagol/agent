import asyncio
import base64
import json
import logging
import os
import re
import uuid

from dataclasses import dataclass
from typing import Any

import httpx

from a2a.client import A2ACardResolver
from a2a.types import (
    AgentCard,
    DataPart,
    JSONRPCError,
    Message,
    MessageSendConfiguration,
    MessageSendParams,
    Part,
    Task,
    TaskState,
    TextPart,
)
from google.adk import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools.tool_context import ToolContext
from google.genai import types


from .remote_agent_connection import RemoteAgentConnections, TaskUpdateCallback


@dataclass
class ValidationResult:
    """Container for Agent Judge validation results."""

    passed: bool
    feedback: str = ""
    raw_text: str | None = None
    confidence: int | None = None


class HostAgent:
    """The host agent.

    This is the agent responsible for choosing which remote agents to send
    tasks to and coordinate their work.
    """

    def __init__(
        self,
        remote_agent_addresses: list[str],
        http_client: httpx.AsyncClient,
        task_callback: TaskUpdateCallback | None = None,
    ):
        self.logger = logging.getLogger(__name__)
        self.task_callback = task_callback
        self.httpx_client = http_client
        self.remote_agent_connections: dict[str, RemoteAgentConnections] = {}
        self.cards: dict[str, AgentCard] = {}
        self.agents: str = ''
        self.max_validation_attempts = int(
            os.environ.get('AGENT_VALIDATION_MAX_ATTEMPTS', '5')
        )
        loop = asyncio.get_running_loop()
        loop.create_task(self.init_remote_agent_addresses(remote_agent_addresses))

    async def init_remote_agent_addresses(self, remote_agent_addresses: list[str]):
        async with asyncio.TaskGroup() as task_group:
            for address in remote_agent_addresses:
                task_group.create_task(self.retrieve_card(address))
        # The task groups run in the background and complete.
        # Once completed the self.agents string is set and the remote
        # connections are established.

    async def retrieve_card(self, address: str):
        card_resolver = A2ACardResolver(self.httpx_client, address)
        card = await card_resolver.get_agent_card()
        self.register_agent_card(card)

    def register_agent_card(self, card: AgentCard):
        remote_connection = RemoteAgentConnections(self.httpx_client, card)
        self.remote_agent_connections[card.name] = remote_connection
        self.cards[card.name] = card
        agent_info = []
        for ra in self.list_remote_agents():
            agent_info.append(json.dumps(ra))
        self.agents = '\n'.join(agent_info)

    def create_agent(self) -> Agent:
        
        model_name = os.environ.get('GEMINI_MODEL', 'gemini-2.0-flash-001')

        return Agent(
            #model='gemini-2.0-flash-001',
            model=model_name,
            name='host_agent',
            instruction=self.root_instruction,
            before_model_callback=self.before_model_callback,
            description=(
                'This agent orchestrates the decomposition of the user request into'
                ' tasks that can be performed by the child agents.'
            ),
            tools=[
                self.list_remote_agents,
                self.send_message,
            ],
        )

    def root_instruction(self, context: ReadonlyContext) -> str:
        current_agent = self.check_state(context)
        return f"""You are an expert delegator that can delegate the user request to the
appropriate remote agents.

Discovery:
- You can use `list_remote_agents` to list the available remote agents you
can use to delegate the task.

Execution:
- For actionable requests, you can use `send_message` to interact with remote agents to take action.

Be sure to include the remote agent name when you respond to the user.

Please rely on tools to address the request, and don't make up the response. If you are not sure, please ask the user for more details.
Focus on the most recent parts of the conversation primarily.

Agents:
{self.agents}

Current agent: {current_agent['active_agent']}
"""

    def check_state(self, context: ReadonlyContext):
        state = context.state
        if (
            'context_id' in state
            and 'session_active' in state
            and state['session_active']
            and 'agent' in state
        ):
            return {'active_agent': f'{state["agent"]}'}
        return {'active_agent': 'None'}

    def before_model_callback(
        self, callback_context: CallbackContext, llm_request
    ):
        state = callback_context.state
        if 'session_active' not in state or not state['session_active']:
            state['session_active'] = True

    def list_remote_agents(self):
        """List the available remote agents you can use to delegate the task."""
        if not self.remote_agent_connections:
            return []

        remote_agent_info = []
        for card in self.cards.values():
            remote_agent_info.append(
                {'name': card.name, 'description': card.description}
            )
        return remote_agent_info

    async def send_message(
        self, agent_name: str, message: str, tool_context: ToolContext
    ):
        """Send a message to a remote agent with Agent Judge validation."""

        if agent_name not in self.remote_agent_connections:
            raise ValueError(f'Agent {agent_name} not found')

        state = tool_context.state
        state['agent'] = agent_name

        original_request = message
        message_to_send = message
        attempts = 0
        judge_name = self._find_agent_judge()

        while True:
            response_parts = await self._dispatch_to_remote_agent(
                agent_name,
                message_to_send,
                tool_context,
                update_state=True,
            )

            # Skip validation when Agent Judge isn't available or when the
            # target agent is the judge itself.
            if not judge_name or agent_name == judge_name:
                return response_parts

            response_text = self._extract_text_from_parts(response_parts)
            if not response_text:
                self.logger.debug(
                    'Received empty response content from %s; skipping validation.',
                    agent_name,
                )
                return response_parts

            validation = await self._validate_with_judge(
                original_request,
                response_text,
                tool_context,
                judge_name,
            )

            # If validation succeeded or the judge was unavailable, surface the
            # response to the user with a helpful status message.
            if validation.passed:
                if validation.feedback and validation.feedback.startswith(
                    'Agent Judge unavailable'
                ):
                    response_parts.append(
                        '⚠️ Agent Judge is currently unavailable. Providing the best effort response.'
                    )
                else:
                    note = '✅ Agent Judge validated this response.'
                    if validation.confidence is not None:
                        note = (
                            f'✅ Agent Judge validated this response '
                            f'(confidence {validation.confidence}/10).'
                        )
                    response_parts.append(note)
                return response_parts

            attempts += 1
            self.logger.warning(
                'Agent Judge rejected response on attempt %s: %s',
                attempts,
                validation.feedback,
            )

            if attempts >= self.max_validation_attempts:
                self.logger.error(
                    'Exceeded maximum validation attempts (%s) for agent %s',
                    self.max_validation_attempts,
                    agent_name,
                )
                return [
                    'I’m sorry, but I’m unable to provide a validated answer right now. '
                    'Please try again later.'
                ]

            message_to_send = self._build_retry_message(
                original_request,
                validation.feedback or validation.raw_text or '',
                response_text,
                attempts + 1,
            )


    async def _dispatch_to_remote_agent(
        self,
        agent_name: str,
        message: str,
        tool_context: ToolContext,
        *,
        update_state: bool,
        context_override: str | None = None,
    ) -> list[Any]:
        """Send a request to a remote agent and normalize the response."""

        client = self.remote_agent_connections.get(agent_name)
        if not client:
            raise ValueError(f'Client not available for {agent_name}')

        state = tool_context.state
        task_id = state.get('task_id') if update_state else None
        context_id = context_override or state.get('context_id')
        message_id = str(uuid.uuid4())

        if update_state:
            state['message_id'] = message_id

        request = MessageSendParams(
            id=str(uuid.uuid4()),
            message=Message(
                role='user',
                parts=[TextPart(text=message)],
                messageId=message_id,
                contextId=context_id,
                taskId=task_id,
            ),
            configuration=MessageSendConfiguration(
                acceptedOutputModes=['text', 'text/plain', 'image/png'],
            ),
        )

        response = await client.send_message(
            request, self.task_callback if update_state else None
        )

        if isinstance(response, JSONRPCError):
            error_message = response.message or 'Unknown error from remote agent'
            self.logger.error(
                'Agent %s returned JSON-RPC error: %s', agent_name, error_message
            )
            return [f'Agent {agent_name} returned an error: {error_message}']

        if isinstance(response, Message):
            return await convert_parts(response.parts, tool_context)

        if response is None:
            return []

        task: Task = response

        if update_state:
            state['session_active'] = task.status.state not in [
                TaskState.completed,
                TaskState.canceled,
                TaskState.failed,
                TaskState.unknown,
            ]
            if task.contextId:
                state['context_id'] = task.contextId
            state['task_id'] = task.id

        if task.status.state == TaskState.input_required and update_state:
            tool_context.actions.skip_summarization = True
            tool_context.actions.escalate = True
        elif task.status.state == TaskState.canceled:
            raise ValueError(f'Agent {agent_name} task {task.id} is cancelled')
        elif task.status.state == TaskState.failed:
            raise ValueError(f'Agent {agent_name} task {task.id} failed')

        response_parts: list[Any] = []
        if task.status.message:
            response_parts.extend(
                await convert_parts(task.status.message.parts, tool_context)
            )
        if task.artifacts:
            for artifact in task.artifacts:
                response_parts.extend(
                    await convert_parts(artifact.parts, tool_context)
                )
        return response_parts

    def _find_agent_judge(self) -> str | None:
        for name, card in self.cards.items():
            card_name = (card.name or '').lower()
            description = (card.description or '').lower()
            if 'judge' in card_name or 'judge' in description:
                return name
        return None

    def _extract_text_from_parts(self, parts: list[Any]) -> str:
        texts: list[str] = []
        for part in parts:
            if isinstance(part, str):
                texts.append(part)
            elif isinstance(part, DataPart):
                try:
                    texts.append(json.dumps(part.data))
                except Exception:
                    texts.append(str(part.data))
            elif isinstance(part, dict):
                try:
                    texts.append(json.dumps(part))
                except Exception:
                    texts.append(str(part))
            elif part is not None:
                texts.append(str(part))
        return '\n'.join(filter(None, (text.strip() for text in texts))).strip()

    async def _validate_with_judge(
        self,
        user_query: str,
        agent_response: str,
        tool_context: ToolContext,
        judge_name: str,
    ) -> ValidationResult:
        """Send the response to the Agent Judge for validation."""

        evaluation_input = f'{user_query}|||{agent_response}'
        context_id = tool_context.state.get('context_id', 'default')
        try:
            evaluation_parts = await self._dispatch_to_remote_agent(
                judge_name,
                evaluation_input,
                tool_context,
                update_state=False,
                context_override=f'{context_id}_judge',
            )
        except Exception as exc:
            self.logger.error('Agent Judge evaluation failed: %s', exc)
            return ValidationResult(
                True,
                feedback='Agent Judge unavailable. Response not validated.',
            )

        evaluation_text = self._extract_text_from_parts(evaluation_parts)
        if not evaluation_text:
            self.logger.warning('Agent Judge returned no evaluation content.')
            return ValidationResult(
                True,
                feedback='Agent Judge unavailable. Response not validated.',
            )

        return self._parse_validation_response(evaluation_text)

    @staticmethod
    def _parse_validation_response(evaluation_text: str) -> ValidationResult:
        normalized = evaluation_text.strip()
        if not normalized:
            return ValidationResult(False, 'Empty evaluation response.', evaluation_text)

        # Try JSON payloads first.
        try:
            parsed = json.loads(normalized)
            if isinstance(parsed, dict) and 'result' in parsed:
                result = str(parsed.get('result', '')).upper()
                passed = result == 'PASS'
                feedback = '' if passed else str(parsed.get('recommendations', ''))
                confidence = parsed.get('confidence')
                try:
                    confidence = int(confidence) if confidence is not None else None
                except (TypeError, ValueError):
                    confidence = None
                return ValidationResult(
                    passed,
                    feedback=feedback,
                    raw_text=evaluation_text,
                    confidence=confidence,
                )
        except json.JSONDecodeError:
            pass

        result_match = re.search(
            r'EVALUATION RESULT:\s*(PASS|FAIL)', normalized, re.IGNORECASE
        )
        if result_match:
            result = result_match.group(1).upper()
        else:
            upper_text = normalized.upper()
            result = 'PASS' if 'PASS' in upper_text and 'FAIL' not in upper_text else 'FAIL'

        confidence = None
        confidence_match = re.search(
            r'Confidence Level:\s*(\d+)', normalized, re.IGNORECASE
        )
        if confidence_match:
            try:
                confidence = int(confidence_match.group(1))
            except ValueError:
                confidence = None

        feedback = ''
        if result != 'PASS':
            recommendations_match = re.search(
                r'### Recommendations for Improvement:\s*(.+?)(?:\n###|\Z)',
                normalized,
                re.DOTALL,
            )
            if recommendations_match:
                feedback = recommendations_match.group(1).strip()
            else:
                feedback = normalized

        return ValidationResult(
            result == 'PASS', feedback=feedback, raw_text=evaluation_text, confidence=confidence
        )

    def _build_retry_message(
        self,
        original_query: str,
        feedback: str,
        previous_response: str,
        attempt_number: int,
    ) -> str:
        sanitized_feedback = feedback.strip() or (
            'Please address the issues highlighted by the Agent Judge.'
        )
        trimmed_response = previous_response.strip()
        max_length = 1500
        if len(trimmed_response) > max_length:
            trimmed_response = trimmed_response[:max_length] + '...'

        return (
            f"{original_query}\n\n"
            f"Agent Judge feedback (attempt {attempt_number}):\n{sanitized_feedback}\n\n"
            f"Previous response for reference:\n{trimmed_response}\n\n"
            "Please provide an improved, accurate, and complete answer that addresses the feedback above."
        )


async def convert_parts(parts: list[Part], tool_context: ToolContext):
    rval = []
    for p in parts:
        rval.append(await convert_part(p, tool_context))
    return rval


async def convert_part(part: Part, tool_context: ToolContext):
    if part.root.kind == 'text':
        return part.root.text
    elif part.root.kind == 'data':
        return part.root.data
    elif part.root.kind == 'file':
        # Repackage A2A FilePart to google.genai Blob
        # Currently not considering plain text as files
        file_id = part.root.file.name
        file_bytes = base64.b64decode(part.root.file.bytes)
        file_part = types.Part(
            inline_data=types.Blob(
                mime_type=part.root.file.mimeType, data=file_bytes
            )
        )
        await tool_context.save_artifact(file_id, file_part)
        tool_context.actions.skip_summarization = True
        tool_context.actions.escalate = True
        return DataPart(data={'artifact-file-id': file_id})
    return f'Unknown type: {part.kind}'
