import os
from collections.abc import AsyncIterable
from typing import Any, Literal

from pydantic import BaseModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import AzureChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from app.database import get_plant_materials, get_material_endnumbers, execute
from app.logger.logger_config import setup_logger
logger= setup_logger("INFO")
logger.info("Creating Memory...")
memory = MemorySaver()
logger.info("Memory Created...")

@tool
def where_used_tool(material_number: str) -> dict[str, Any]:
    """
    Given a material number, return its module components,
    plants, and end numbers from the live Azure SQL tables.
    """
    plants = get_plant_materials(material_number)
    ends = get_material_endnumbers(material_number)

    # DEBUG: print actual rows from the database
    print("🔍 where_used_tool returned:", plants, ends)

    if not plants and not ends:
        return {"message": f"No usage records found for material {material_number}."}

    return {
        "material": material_number,
        "module_components": [r["module_component"] for r in plants],
        "plants": [r["plant_code"] for r in plants],
        "end_numbers": ends,
    }


@tool
def cost_of_part_tool(material_number: str) -> dict[str, Any]:
    """
    Given a material number, return the latest price & currency
    from the live Azure SQL tables.
    """
    rows = execute(
        """
        SELECT TOP 1 price, currency
          FROM CSC.dwd_tb_dim_md_plant_material pm
          JOIN CSC.dwd_tb_dim_md_material   m 
            ON m.material_number = pm.material_number
         WHERE pm.material_number = :mat
         ORDER BY m.costingDate DESC
        """,
        mat=material_number
    )

    # DEBUG: print actual rows from the database
    print("🔍 cost_of_part_tool returned:", rows)

    if not rows:
        return {"message": f"No cost data found for material {material_number}."}

    return {"material": material_number, **rows[0]}


class ResponseFormat(BaseModel):
    status: Literal["input_required", "completed", "error"] = "input_required"
    message: str


class CostingAgent:
    """
    An agent that answers two kinds of questions:
    - “Where is part X used?” → calls where_used_tool(...)
    - “What is the cost of part X?” → calls cost_of_part_tool(...)
    """
    logger.info("Creating system instructions...")
    SYSTEM_INSTRUCTION = (
        "You are a Costing Services agent.  "
        "When the user asks 'Where is part <M> used?', you MUST call the tool "
        "`where_used_tool(material_number)` and return its result.  "
        "When the user asks 'What is the cost of part <M>?', you MUST call the tool "
        "`cost_of_part_tool(material_number)` and return its result.  "
        "If they ask anything else, politely state you can only answer usage or cost queries."
    )

    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self):
        src = os.getenv("MODEL_SOURCE", "azure").lower()
        if src == "google":
            logger.info("Creating Gemini model...")
            self.model = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
        else:
            logger.info("Creating Azure Openai model...")
            self.model = AzureChatOpenAI(
                openai_api_key=os.environ["AZURE_OPENAI_API_KEY"],
                azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
                azure_deployment=os.environ["AZURE_OPENAI_LLM_DEPLOYMENT_NAME"],
                api_version=os.environ["AZURE_OPENAI_API_VERSION"],
                temperature=0,
            )

        # Register both tools
        self.tools = [where_used_tool, cost_of_part_tool]
        logger.info("Creating react agent...")
        # Build the React-style agent
        self.graph = create_react_agent(
            self.model,
            tools=self.tools,
            checkpointer=memory,
            prompt=self.SYSTEM_INSTRUCTION,
        )
        logger.info("React agent created...")

    async def stream(self, query: str, context_id: str) -> AsyncIterable[dict[str, Any]]:
        """
        Stream back status updates when the LLM invokes a tool,
        then yield the final response.
        """
        inputs = {"messages": [("user", query)]}
        config = {"configurable": {"thread_id": context_id}}
        logger.info(f"config: {config}")

        for item in self.graph.stream(inputs, config, stream_mode="values"):
            last = item["messages"][-1]
            if isinstance(last, AIMessage) and last.tool_calls:
                yield {
                    "is_task_complete": False,
                    "require_user_input": False,
                    "content": "Looking up data…",
                }

        # Final reply
        yield self.get_agent_response(config)

    def get_agent_response(self, config: dict) -> dict[str, Any]:
        """
        Inspect the agent’s message history:
        1) If there’s a ToolMessage, return its raw .content dict.
        2) Otherwise return the last AIMessage.text.
        """
        state = self.graph.get_state(config)
        messages = state.values.get("messages", [])
        logger.info(f"Agent Responses: {messages}")

        # 1) Check for any ToolMessage
        for msg in reversed(messages):
            if isinstance(msg, ToolMessage):
                payload = msg.content  # the dict your tool returned
                return {
                    "is_task_complete": True,
                    "require_user_input": False,
                    "content": payload,
                }
        
        logger.info(f"Falling back of messages")
        # 2) Fallback to the last AIMessage
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content:
                return {
                    "is_task_complete": True,
                    "require_user_input": False,
                    "content": msg.content,
                }
        logger.info(f"Error Messages")
        # 3) Final error fallback
        return {
            "is_task_complete": False,
            "require_user_input": True,
            "content": "Sorry, I couldn't process your request.",
        }
 