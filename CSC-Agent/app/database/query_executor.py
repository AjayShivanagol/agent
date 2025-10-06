from .database_config import get_db_connection
from app.logger.logger_config import setup_logger
logger= setup_logger("CONFIG")

def execute_sql_query(query: str):
    """Execute a SQL query and return results."""
    connection = get_db_connection()
    if not connection:
        logger.error("❌ Failed to connect to the database.")
        return None  # Return None to indicate connection failure
    
    try:
        logger.info("Creating Cursor")
        cursor = connection.cursor()
        logger.info("Cursor created successfully")
        # Set a query timeout of 30 seconds
        logger.info("Executing query")
        cursor.execute(query)
        columns = [column[0] for column in cursor.description]
        rows = cursor.fetchall()
        results = [dict(zip(columns, row)) for row in rows]
        return results
    except Exception as e:
        logger.error(f"❌ Error executing query: {e}")
        return None  # Return None for query execution errors too
    finally:
        if connection:
            connection.close()
