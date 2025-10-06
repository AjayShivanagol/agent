import logging
import os
import asyncio

def setup_logger(name):
    """
    Sets up a logger with a specified name and returns it.
    """
    log_level = 'DEBUG'

    logger = logging.getLogger(name)

    if log_level == 'DEBUG':
        logger.setLevel(logging.DEBUG)
    elif log_level == 'INFO':
        logger.setLevel(logging.INFO)
    elif log_level == 'WARNING':
        logger.setLevel(logging.WARNING)
    elif log_level == 'ERROR':
        logger.setLevel(logging.ERROR)
    elif log_level == 'CRITICAL':
        logger.setLevel(logging.CRITICAL)
    else:
        logger.setLevel(logging.INFO)

    handler = logging.StreamHandler()

    if log_level == 'DEBUG':
        handler.setLevel(logging.DEBUG)
    elif log_level == 'INFO':
        handler.setLevel(logging.INFO)
    elif log_level == 'WARNING':
        handler.setLevel(logging.WARNING)
    elif log_level == 'ERROR':
        handler.setLevel(logging.ERROR)
    elif log_level == 'CRITICAL':
        handler.setLevel(logging.CRITICAL)
    else:
        handler.setLevel(logging.INFO)

    formatter = logging.Formatter('%(name)s - %(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    if not logger.hasHandlers():
        logger.addHandler(handler)

    return logger

def get_current_filename():
    """
    Returns the name of the current file.
    """
    return os.path.basename(__file__)

# Async wrappers if needed in an async context

async def async_setup_logger(name):
    return await asyncio.to_thread(setup_logger, name)

async def async_get_current_filename():
    return await asyncio.to_thread(get_current_filename)