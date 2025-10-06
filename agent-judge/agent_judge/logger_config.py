import logging
import os

def setup_logger(level: str = "INFO") -> logging.Logger:
    """Set up and configure logger for Agent Judge."""
    
    # Convert string level to logging level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create logger
    logger = logging.getLogger("agent_judge")
    logger.setLevel(numeric_level)
    
    # Create console handler
    handler = logging.StreamHandler()
    handler.setLevel(numeric_level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    
    # Add handler to logger
    if not logger.handlers:
        logger.addHandler(handler)
    
    return logger