# ask_the_graph_openai.py
import os
from neo4j import GraphDatabase
from langchain_openai import ChatOpenAI         # CHANGED
from langchain.chains import GraphCypherQAChain
from langchain_community.graphs import Neo4jGraph
from langchain_openai import AzureChatOpenAI
from dotenv import load_dotenv
load_dotenv()
# --- CONFIGURATION ---
# Load credentials from environment variables
    # Neo4j Database Credentials
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "invalid") # <-- IMPORTANT: SET YOUR PASSWORD
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")


def query_the_graph(question):
    """
    Uses an LLM to translate a natural language question into a Cypher query,
    executes it against the Neo4j database, and returns the answer.
    """
    try:
        # 1. Connect to the Neo4j Graph
        graph = Neo4jGraph(
            url=NEO4J_URI, 
            username=NEO4J_USERNAME, 
            password=NEO4J_PASSWORD,
            database=NEO4J_DATABASE
        )
        print("✅ Connected to Neo4j and fetched schema.")
        graph.refresh_schema()

        # 2. Set up the Language Model using OpenAI
        llm = AzureChatOpenAI(
                openai_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
                temperature=0
            )
        print("✅ Initialized OpenAI language model (gpt-4).")

        # 3. Create the Question-Answering Chain
        chain = GraphCypherQAChain.from_llm(
            graph=graph,
            cypher_llm=llm,
            qa_llm=llm,
            verbose=True,
            allow_dangerous_requests=True
        )
        print("🤖 Created Graph QA chain. Asking the question...")
        
        # 4. Ask the question
        result = chain.invoke({"query": question})
        return result['result']

    except Exception as e:
        return f"🔥 An error occurred: {e}"

if __name__ == "__main__":
    # Define the question you want to ask
    user_question = "What are available costingdates for material U0000000139020000 in plant 'MBC Untertürkheim'?"
    
    # Get the answer
    answer = query_the_graph(user_question)
    
    # Print the final result
    print("\n" + "="*50)
    print(f"❓ Question: {user_question}")
    print(f"💡 Answer: {answer}")
    print("="*50)