import os
import requests
import pandas as pd
from neo4j import GraphDatabase
import uuid
from dotenv import load_dotenv
load_dotenv()
class ApiToGraphLoader:
    """
    A class to fetch data from an API and load it as nodes into a Neo4j database.
    """
    def __init__(self, url, user_name, password, database):
        """
        Initializes the connection to the Neo4j database.
        
        Args:
            url (str): The URI for the Neo4j database (e.g., "neo4j://localhost:7687").
            user_name (str): The username for database authentication.
            password (str): The password for database authentication.
            database (str): The name of the database to connect to.
        """
        try:
            self.driver = GraphDatabase.driver(url, auth=(user_name, password))
            self.database = database
            print("✅ Successfully connected to Neo4j database.")
        except Exception as e:
            print(f"🔥 Failed to connect to Neo4j. Error: {e}")
            self.driver = None

    def close(self):
        """Closes the Neo4j driver connection."""
        if self.driver:
            self.driver.close()
            print("🔌 Neo4j connection closed.")

    def fetch_data_from_api(self, api_url):
        """
        Fetches data from the specified API endpoint.
        
        Args:
            api_url (str): The URL of the API to fetch data from.
            
        Returns:
            list: A list of dictionaries containing the data, or None if the request fails.
        """
        print(f"Attempting to fetch data from {api_url}...")
        try:
            payload= {
                    "materialList": [
                        "U0000000139020000"
                    ]
                            }
            response = requests.post(api_url, json=payload, verify=False)
            # Raise an exception for bad status codes (4xx or 5xx)
            response.raise_for_status()
            print("✅ Data fetched successfully from API.")
            ## Get the material description
            data= response.json()
            # print(response)
            # print("----"*10)
            # print(response["data"])
            material_details= data["data"]["data"]
            return material_details
        except requests.exceptions.RequestException as e:
            print(f"🔥 Failed to fetch data from API. Error: {e}")
            return None

    def _create_node_query(self, session, node_label, properties):
        """
        Helper function to create a single node in Neo4j using a parameterized query
        to prevent Cypher injection and handle data types correctly.
        
        Args:
            session: The Neo4j session object.
            node_label (str): The label for the node (e.g., "Material").
            properties (dict): A dictionary of properties for the node.
        """
        # Using MERGE to avoid creating duplicate nodes. 
        # It's best to merge on a unique property, like an 'id'.
        # The query is parameterized for security and correctness.
        query = f"MERGE (n:{node_label} {{id: $id}}) SET n += $props"
        
        # We pass the unique ID separately from the rest of the properties
        params = {
            'id': str(uuid.uuid4()), # Assumes your data has a unique 'id' field
            'props': properties
        }
        session.run(query, params)

    def load_data_as_nodes(self, api_data, node_label):
        """
        Processes a list of data from the API and creates a node for each item.
        
        Args:
            api_data (list): The list of dictionaries fetched from the API.
            node_label (str): The label to assign to the created nodes.
        """
        if not self.driver or not api_data:
            print("Driver not initialized or no data to load. Aborting.")
            return

        print(f"Starting to load data as nodes with label '{node_label}'...")
        with self.driver.session(database=self.database) as session:
            for item in api_data:
                # The 'item' is a dictionary from the API response.
                # All keys in the dictionary will be added as properties to the node.
                self._create_node_query(session, node_label, item)
        
        print(f"✅ Finished creating nodes.")


# ==============================================================================
# MAIN EXECUTION BLOCK
# ==============================================================================
if __name__ == "__main__":
    # --- 1. SET YOUR CONFIGURATION VARIABLES HERE ---
    
    # Neo4j Database Credentials
    NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
    NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "invalid") # <-- IMPORTANT: SET YOUR PASSWORD
    NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

    # API Configuration
    # <-- IMPORTANT: REPLACE WITH YOUR ACTUAL API ENDPOINT
    API_ENDPOINT = "https://code-spaces.dna-prod.app.corpintra.net/il-csc-backend-maven-aws/prod/api/integration_layer/resultview/componentView/report" 
    
    # Node Configuration
    # <-- IMPORTANT: SET THE LABEL FOR THE NODES YOU ARE CREATING
    NODE_LABEL = "new_material_details" 
    
    # --- 2. INITIALIZE THE LOADER ---
    loader = ApiToGraphLoader(
        url=NEO4J_URI,
        user_name=NEO4J_USERNAME,
        password=NEO4J_PASSWORD,
        database=NEO4J_DATABASE
    )

    try:
        # --- 3. FETCH DATA FROM THE API ---
        data = loader.fetch_data_from_api(API_ENDPOINT)

        # --- 4. LOAD DATA INTO NEO4J ---
        if data:
            # Check if the fetched data is a list
            if isinstance(data, list):
                loader.load_data_as_nodes(data, NODE_LABEL)
            else:
                print("🔥 API data is not in the expected format (a list of objects).")
    
    finally:
        # --- 5. CLOSE THE CONNECTION ---
        loader.close()