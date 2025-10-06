import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
load_dotenv()
class RelationshipCreator:
    """A class to create relationships directly within the Neo4j database."""
    def __init__(self, url, user_name, password, database):
        try:
            self.driver = GraphDatabase.driver(url, auth=(user_name, password))
            self.database = database
            print("✅ Successfully connected to Neo4j database.")
        except Exception as e:
            print(f"🔥 Failed to connect to Neo4j. Error: {e}")
            self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()
            print("🔌 Neo4j connection closed.")

    def run_cypher_query(self, query):
        """Runs a given Cypher query to perform an operation in the database."""
        if not self.driver:
            print("Aborting: Driver not initialized.")
            return

        print("🚀 Executing Cypher query in the database...")
        with self.driver.session(database=self.database) as session:
            try:
                session.run(query)
                print("✅ Query executed successfully.")
            except Exception as e:
                print(f"🔥 An error occurred: {e}")

if __name__ == "__main__":
    # Neo4j Database Credentials
    NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
    NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "invalid")
    NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

    # The powerful, all-in-one query
    create_relationships_query = """
    MATCH (a:new_material_details)
    MATCH (b:plant_details)
    WHERE a.plant = b.plantCode
    MERGE (a)-[:PRODUCED_IN]->(b)
    """
    
    # --- Execution ---
    creator = RelationshipCreator(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, NEO4J_DATABASE)
    try:
        print("Run Cypher")
        creator.run_cypher_query(create_relationships_query)
    finally:
        creator.close()