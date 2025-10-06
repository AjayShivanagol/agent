import logging
import os
import sys
import click
import httpx
import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from dotenv import load_dotenv

from agent_judge.judge import AgentJudge
from agent_judge.agent_executor import JudgeAgentExecutor

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

class MissingAPIKeyError(Exception):
    """Exception for missing API key."""

@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=10001)  # Different port from CSC Agent
def main(host, port):
    """Starts the Agent Judge server."""
    try:
        # Check for required API keys based on model source
        if os.getenv('MODEL_SOURCE') == "google":
            logger.info("Using Google Gemini")
            if not os.getenv('GOOGLE_API_KEY'):
                raise MissingAPIKeyError(
                    'GOOGLE_API_KEY environment variable not set.'
                )
        else:
            logger.info("Using Azure OpenAI")
            if not os.getenv('AZURE_OPENAI_API_KEY'):
                raise MissingAPIKeyError(
                    'AZURE_OPENAI_API_KEY environment variable not set.'
                )

        # Define agent capabilities (no streaming needed for quick evaluations)
        capabilities = AgentCapabilities(
            text_generation=True,
            structured_output=True,
            function_calling=True,
        )
        logger.info(f"Agent capabilities: {capabilities}")

        # Define agent skills
        evaluation_skill = AgentSkill(
            id='evaluate_agent_response',
            name='Agent Response Evaluation',
            description='Evaluates the accuracy, completeness, and quality of AI agent responses against user queries. Provides detailed feedback and pass/fail decisions.',
            tags=[
                'evaluation',
                'accuracy',
                'quality assessment',
                'response validation',
                'fact checking',
                'completeness check'
            ],
            examples=[
                'What is the capital of France?|||The capital of France is Paris.',
                'How do I bake a cake?|||To bake a cake, you need flour, eggs, sugar, and butter. Mix them together and bake at 350°F.',
                'Explain quantum computing|||Quantum computing uses quantum mechanical phenomena to perform calculations.',
            ],
        )
        logger.info(f"Evaluation skill created: {evaluation_skill}")

        fact_checking_skill = AgentSkill(
            id='fact_check_claims',
            name='Fact Checking Tool',
            description='Verifies factual claims and statements for accuracy using available knowledge sources.',
            tags=[
                'fact checking',
                'verification',
                'accuracy',
                'claims validation',
                'truth assessment'
            ],
            examples=[
                'Verify that the Earth revolves around the Sun',
                'Check if water boils at 100°C at sea level',
                'Validate that Shakespeare wrote Romeo and Juliet',
            ],
        )
        logger.info(f"Fact checking skill created: {fact_checking_skill}")

        quality_assessment_skill = AgentSkill(
            id='assess_response_quality',
            name='Response Quality Assessment',
            description='Analyzes response quality including structure, specificity, relevance, and comprehensiveness.',
            tags=[
                'quality assessment',
                'response analysis',
                'structure evaluation',
                'relevance check',
                'completeness analysis'
            ],
            examples=[
                'Assess the quality of a technical explanation',
                'Evaluate response completeness and clarity',
                'Check if response addresses all aspects of the query',
            ],
        )
        logger.info(f"Quality assessment skill created: {quality_assessment_skill}")

        # Create agent card
        agent_card = AgentCard(
            name='Agent Judge',
            description='Agent Judge evaluates AI agent responses for accuracy, completeness, and quality. Provides comprehensive evaluation with pass/fail decisions and detailed feedback.',
            url=f'http://{host}:{port}/',
            version='1.0.0',
            defaultInputModes=AgentJudge.SUPPORTED_CONTENT_TYPES,
            defaultOutputModes=AgentJudge.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[evaluation_skill, fact_checking_skill, quality_assessment_skill]
        )
        logger.info(f"Agent Card created: {agent_card}")

        # Create request handler
        logger.info("Creating request handler")
        httpx_client = httpx.AsyncClient()
        request_handler = DefaultRequestHandler(
            agent_executor=JudgeAgentExecutor(),
            task_store=InMemoryTaskStore(),
        )

        # Create and start server
        logger.info("Creating server")
        server = A2AStarletteApplication(
            agent_card=agent_card, 
            http_handler=request_handler
        )
        
        logger.info(f"Agent Judge server starting on {host}:{port}")
        uvicorn.run(server.build(), host=host, port=port)

    except MissingAPIKeyError as e:
        logger.error(f'Error: {e}')
        sys.exit(1)
    except Exception as e:
        logger.error(f'An error occurred during server startup: {e}', exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()