import re
from app.logger.logger_config import setup_logger
logger= setup_logger("INFO")
def protect_db(query: str) -> bool:
    """Checks if a given SQL query contains forbidden commands that modify the database or tables.

    ALLOWS ONLY SELECT queries for data retrieval.
    BLOCKS all other operations: INSERT, UPDATE, DELETE, ALTER, DROP, CREATE, etc.

    Parameters
    ----------
    query : str
        The SQL query to check.

    Returns
    -------
    bool
        Returns False if the query is safe (SELECT only), 
        and True if the query contains forbidden commands (blocked).
    """
    # If the query is empty, consider it safe
    if not query:
        logger.info("Query is empty")
        return False
    
    # List of forbidden SQL commands - ALLOW ONLY SELECT
    forbidden_commands = [
        # Data modification (BLOCKED)
        r'\bINSERT\b', r'\bUPDATE\b', r'\bDELETE\b',
        # Schema operations (BLOCKED)
        r'\bALTER\b', r'\bDROP\b', r'\bCREATE\b', r'\bTRUNCATE\b', r'\bRENAME\b',
        # Security operations (BLOCKED)
        r'\bGRANT\b', r'\bREVOKE\b', r'\bLOCK\b',
        # Transaction operations (BLOCKED)
        r'\bSET\b', r'\bCOMMIT\b', r'\bROLLBACK\b', r'\bBEGIN\b',
        # Maintenance operations (BLOCKED)
        r'\bBACKUP\b', r'\bREPAIR\b', r'\bRESTORE\b',
        # Other operations (BLOCKED)
        r'\bEXEC\b', r'\bEXECUTE\b', r'\bCALL\b'
        # NOTE: SELECT is NOT in this list, so it's ALLOWED
    ]
    logger.info("Looking for Forbidden commands")
    # Check if the query contains any forbidden command
    for pattern in forbidden_commands:
        if re.search(pattern, query, re.IGNORECASE):
            logger.info("Forbidden command found")
            return True
    
    # If no forbidden commands are found, it's safe (SELECT is allowed)
    return False
