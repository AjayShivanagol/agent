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

# Updated imports to reflect new agent and executor names
from app.agent import CostingAgent
from app.agent_executor import CostingAgentExecutor
from app.data_cache import load_data_cache
from app.logger.logger_config import setup_logger
logger= setup_logger("INFO")
logger.info("Loading Env variables")
# load_dotenv()
load_dotenv("/vault/secrets/envvar")



class MissingAPIKeyError(Exception):
    """Exception for missing API key."""


@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=10000)
def main(host, port):
    """Starts the CSC Agent server."""
    try:
        if os.getenv('MODEL_SOURCE') == "google":
           logger.info("Considering Google Gemini")
           if not os.getenv('GOOGLE_API_KEY'):
               raise MissingAPIKeyError(
                   'GOOGLE_API_KEY environment variable not set.'
               )
        else:
            logger.info("Considering Nexus")
            if not os.getenv('TOOL_LLM_URL'):
                raise MissingAPIKeyError(
                    'TOOL_LLM_URL environment variable not set.'
                )
            if not os.getenv('TOOL_LLM_NAME'):
                raise MissingAPIKeyError(
                    'TOOL_LLM_NAME environment not variable not set.'
                )
            # 1. Run the cache refresh once immediately on startup
        print("Performing initial data cache load...")
        logger.info("Loading data cache at startup")
        load_data_cache()
        logger.info("Creating Agent Capabilities...")
        capabilities = AgentCapabilities(streaming=True, pushNotifications=True)
        logger.info("Capabilities created")
        logger.info("Creating Agent Skill...")
        # Define AgentSkill for keyword search
        keyword_search_skill = AgentSkill(
            id='get_keyword_search_data',
            name='Keyword Search Tool',
            description='Performs a broad keyword and substring search across costing data for general queries and comprehensive context.',
            tags=['keyword search', 'costing data', 'material search', 'item search', 'general query'],
            examples=[
                'What is the costing data for Brake Pad Set?',
                'Find information about Engine Block (M276).',
                'Show me data for Alternator.',
            ],
        )
        logger.info(f"Skill Created: {keyword_search_skill}")

        # Define AgentSkill for semantic search
        semantic_search_skill = AgentSkill(
            id='get_semantic_search_data',
            name='Semantic Search Tool',
            description='Performs a semantic similarity search across costing data to find similar parts or alternatives, useful when direct keyword matching is insufficient.',
            tags=['semantic search', 'similar parts', 'alternatives', 'part comparison', 'related items'],
            examples=[
                'Show me similar parts to Headlight Assembly (LED).',
                'Are there any alternatives to Fuel Pump (W204)?',
                'Find parts comparable to Battery (AGM).',
            ],
        )
        logger.info(f"Skill Created: {semantic_search_skill}")
        # Define AgentSkill for the new tool
        material_details_skill = AgentSkill(
            id='get_material_cost_details',
            name='Material Cost Details',
            description='Gets detailed costing data for one or more materials in specific plants.',
            tags=[
                'costing data',
                'material details',
                'cost estimation',
                'part lookup',
                'material ID',
                'plant ID',
                'procurement',
                'finance',
                'specific lookup'
            ],
            examples=[
                'Get the cost details for material U0000000139020000 in plant 3010.',
                'What is the total value for part U0000000139020000?',
                'Show me the costing data for material U0000000139020000 with costing variant ZPA1.',
            ],
        )
        logger.info(f"Skill Created: {material_details_skill}")
                # Define AgentSkill for listing all plants
        plant_list_skill = AgentSkill(
            id='get_plant_list',
            name='Plant List Tool',
            description='Retrieves the list of all available plants with their official Plant Code and Plant Name.',
            tags=['plant list', 'plant code', 'plant name', 'lookup', 'facility', 'locations'],
            examples=[
                'Show me all available plants.',
                'List all plant codes and names.',
                'What plants are available in the system?',
            ],
        )
        logger.info(f"Skill Created: {plant_list_skill}")

        plant_lookup_skill = AgentSkill(
            id='get_plant_id_from_name',
            name='Plant ID Lookup',
            description="Translates a plant's common name (e.g., 'Stuttgart') into its official Plant ID, correcting for minor misspellings.",
            tags=[
                'plant ID',
                'plant name',
                'lookup',
                'translation',
                'fuzzy match'
            ],
            examples=[
                'What is the plant ID for the Stuttgart plant?',
                'Find the plant code for Stutgartt.',
                'I need the costs for the Berlin plant.'
            ],
        )
        logger.info(f"Skill Created: {plant_lookup_skill}")
        costing_status_lookup_skill = AgentSkill(
            id='get_costing_status_id_from_description',
            name='Costing Status ID Lookup',
            description="Translates a costing status description (e.g., 'Costing Without Errors') into its official ID/code (e.g., 'KA'), correcting for misspellings.",
            tags=[
                'costing status',
                'status code',
                'lookup',
                'translation',
                'fuzzy match'
            ],
            examples=[
                'Find all parts with a costing status of Costing Without Errors.',
                'What is the code for the status "costing with errros"?',
                'Filter by the KA costing status.'
            ],
        )
        logger.info(f"Skill Created: {costing_status_lookup_skill}")
        currency_type_lookup_skill = AgentSkill(
            id='get_currency_type_code_from_description',
            name='Currency Type Code Lookup',
            description="Translates a currency type description (e.g., 'Company Code Currency') into its official code (e.g., '10'), correcting for misspellings.",
            tags=[
                'currency type',
                'currency code',
                'lookup',
                'translation',
                'fuzzy match'
            ],
            examples=[
                'Show me the results in Company Code Currency.',
                'What is the type code for controlling area curency?',
                'Use currency type 10.'
            ],
        )
        logger.info(f"Skill Created: {currency_type_lookup_skill}")

        price_lookup_skill = AgentSkill(
            id="get_price_for_plant",
            name="Plant Price Lookup",
            description=(
                "Returns the synthetic price per 1 value for a given plant code. "
                "If the plant code exists in the predefined mapping, the fixed price is returned. "
                "If not, a random price in the range €10.0–€20.0 is generated, stored, and reused."
            ),
            tags=[
                "plant",
                "price",
                "lookup",
                "costing",
                "valuation"
            ],
            examples=[
                "Get the price per 1 for plant 3010.",
                "What is the price value for plant 3059?",
                "Lookup the unit price for plant code 2821."
            ],
        )

        # AgentSkill for comprehensive material search
        material_search_skill = AgentSkill(
            id='search_materials_comprehensive',
            name='Comprehensive Material Search',
            description='Advanced material search with exact and substring matching for finding similar automotive parts. Handles both description searches and material number lookups with improved relevance filtering.',
            tags=[
                'material search',
                'part search',
                'similar parts',
                'material lookup',
                'part number',
                'description search',
                'automotive parts',
                'exact matching',
                'substring matching'
            ],
            examples=[
                'Find similar parts for A9076920402.',
                'Search for brake pad materials.',
                'Find parts similar to TRIM SIDE PANEL.',
                'Look up material number A9066840817.',
                'Show me maximum matching materials for TRIM SIDE PANEL CTR RR LWR RH AL4.',
                'Find similar parts for A1675407259.'
            ],
        )
        logger.info(f"Skill Created: {material_search_skill}")

        instruction_fetcher_skill = AgentSkill(
            id='get_instructions_for_task',
            name='Task Instruction Fetcher',
            description="Retrieves a detailed instruction playbook for complex, multi-step tasks like 'cost_comparison' or 'parts_usage'.",
            tags=[
                'dynamic prompt',
                'instructions',
                'workflow',
                'planning',
                'strategy',
                'multi-step'
            ],
            examples=[
                'Perform a cost comparison for alternators.',
                'Can you show me where this part is used?',
                'I need a detailed analysis of parts usage for material X.'
            ],
        )
        logger.info(f"Skill Created: {instruction_fetcher_skill}")
        agent_card = AgentCard(
            name='CSC Agent',
            description='CSC Reporting Agent: Provides comprehensive costing data, finding similar parts and getting plant details in the system available using both keyword and semantic search capabilities.', # Updated overall description
            url=f'http://{host}:{port}/',
            version='1.0.0',
            defaultInputModes=CostingAgent.SUPPORTED_CONTENT_TYPES,
            defaultOutputModes=CostingAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            # skills=[keyword_search_skill, semantic_search_skill, material_details_skill, plant_lookup_skill, costing_status_lookup_skill, currency_type_lookup_skill]
            skills=[material_details_skill, plant_lookup_skill, costing_status_lookup_skill, currency_type_lookup_skill, instruction_fetcher_skill, material_search_skill, plant_list_skill, price_lookup_skill]
        )
        logger.info(f"Skill Agent Card: {agent_card}")
        # --8<-- [start:DefaultRequestHandler]
        logger.info(f"Creating request handler")
        httpx_client = httpx.AsyncClient()
        request_handler = DefaultRequestHandler(
            agent_executor=CostingAgentExecutor(),
            task_store=InMemoryTaskStore(),
            # push_notifier=PushNotificationSender(httpx_client),
        )
        logger.info(f"Creating Server")
        server = A2AStarletteApplication(
            agent_card=agent_card, http_handler=request_handler
        )
        logger.info(f"Server started running...")
        uvicorn.run(server.build(), host=host, port=port)
        # --8<-- [end:DefaultRequestHandler]

    except MissingAPIKeyError as e:
        logger.error(f'Error: {e}')
        sys.exit(1)
    except Exception as e:
        logger.error(f'An error occurred during server startup: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
