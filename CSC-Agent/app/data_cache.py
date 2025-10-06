import httpx
import os
import logging

# This dictionary will hold our cached data: {'stuttgart': '3010', ...}
PLANT_NAME_TO_ID_CACHE = {}
COSTING_STATUS_CACHE = {}
CURRENCY_TYPE_CODE = {}

# Assume logger is configured elsewhere, or configure it here
from app.logger.logger_config import setup_logger
logger= setup_logger("INFO")

def load_data_cache():
    """
    Calls the API to get all plant details and loads them into the
    in-memory cache. This should be called once on application startup.
    """
    global PLANT_NAME_TO_ID_CACHE, COSTING_STATUS_CACHE, CURRENCY_TYPE_CODE
    print("--- Loading all plant data into cache... ---")
    logger.info("--- Loading all plant data into cache... ---")
    
    try:
        # NOTE: Replace with your actual API endpoint that gets all plants
        mock_api_url = os.getenv("PLANT_DETAILS_API_URL", "http://localhost:8000")
        api_endpoint = f'{mock_api_url}'
        header= {"x-api-key": os.getenv("XAPI_KEY")}
        logger.info(f"Fetching plant data from: {api_endpoint}")

        response = httpx.get(api_endpoint, timeout=30.0,headers= header, verify=False)
        response.raise_for_status()
        
        all_plants = response.json().get("data", []) # Assuming data is in a 'data' key
        logger.info(f"Received {len(all_plants)} plant records.")

        # Create a simple name -> id mapping.
        # This assumes the plant name is in a 'plantName' field and id is in 'plantCode'.
        # Adjust these keys to match your actual API response.
        temp_cache = {
            plant['plantName'].lower(): plant['plantCode'] 
            for plant in all_plants if 'plantName' in plant and 'plantCode' in plant
        }
        
        PLANT_NAME_TO_ID_CACHE = temp_cache
        print(f"--- Successfully loaded {len(PLANT_NAME_TO_ID_CACHE)} plants into cache. ---")
        logger.info(f"--- Successfully loaded {len(PLANT_NAME_TO_ID_CACHE)} plants into cache. ---")

        ### Creating Costing status Cache
        print("--- Loading all Costing Status into cache... ---")
        logger.info("--- Loading all Costing Status into cache... ---")
        # NOTE: Replace with your actual API endpoint that gets all plants
        mock_api_url = os.getenv("COSTING_STATUS_API_URL", "http://localhost:8000")
        api_endpoint = f'{mock_api_url}'
        logger.info(f"Fetching costing status data from: {api_endpoint}")

        response = httpx.get(api_endpoint, timeout=30.0,headers= header, verify=False)
        response.raise_for_status()
        all_costing_status= response.json().get("data", []) # Assuming data is in a 'data' key
        logger.info(f"Received {len(all_costing_status)} costing status records.")
        
        # Create a simple name -> id mapping.
        # This assumes the Costing status value is in a 'value' field and description is in 'description'.
        # Adjust these keys to match your actual API response.
        temp_cache = {
            costing_status['value'].lower(): costing_status['description'] 
            for costing_status in all_costing_status if 'value' in costing_status and 'description' in costing_status
        }
        COSTING_STATUS_CACHE= temp_cache
        logger.info(f"--- Successfully loaded {len(COSTING_STATUS_CACHE)} costing statuses into cache. ---")


        ### Creating Costing TYPE Cache
        print("--- Loading all Costing TYPE into cache... ---")
        logger.info("--- Loading all Costing TYPE into cache... ---")
        mock_api_url = os.getenv("COSTING_STATUS_API_URL", "http://localhost:8000")
        api_endpoint = f'{mock_api_url}'
        logger.info(f"Fetching costing type data from: {api_endpoint}")

        response = httpx.get(api_endpoint, timeout=30.0,headers= header, verify=False)
        response.raise_for_status()
        all_costing_type= response.json().get("data", []) # Assuming data is in a 'data' key
        logger.info(f"Received {len(all_costing_type)} costing type records.")

        # Create a simple name -> id mapping.
        # This assumes the Costing status value is in a 'value' field and description is in 'description'.
        # Adjust these keys to match your actual API response.
        temp_cache = {
            costing_type['currencyTypeCode'].lower(): costing_type['currencyTypeDesc'] 
            for costing_type in all_costing_type if 'currencyTypeCode' in costing_type and 'currencyTypeDesc' in costing_type
        }
        CURRENCY_TYPE_CODE= temp_cache
        logger.info(f"--- Successfully loaded {len(CURRENCY_TYPE_CODE)} currency types into cache. ---")

    except Exception as e:
        print(f"!!! FAILED to load data into cache: {e} !!!")
        logger.error(f"!!! FAILED to load data into cache: {e} !!!", exc_info=True)
