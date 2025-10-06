import random
from langchain_core.tools import tool
from typing import Optional, List
from langchain_core.tools import tool
import httpx
import os
import difflib
import sys
import logging

# Assume the logger is configured in a central place, or configure it here.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Assuming these are available for import
import app.data_cache
from app.database.query_executor import execute_sql_query

@tool
def get_material_cost_details(
    material_list: List[str],
    plant_list: List[str],
    costing_variant_list: Optional[List[str]] = None,
    material_type_list: Optional[List[str]] = None,
    costing_status_list: Optional[List[str]] = None,
    costing_version: Optional[str] = "01",
    currency_type_code: Optional[str] = "10",
    compare_prices: Optional[bool] = False
) -> dict:
    """
    Routing rule: Do NOT call this tool until you have first called `get_instructions_for_task` in the current turn.
    Use this tool for precise lookups of material cost estimations.    It is the primary
    tool when you need to filter by specific material numbers, plants, costing variants,
    and validity dates. Depending on the `compare_prices` flag,
    it can either return the full detailed cost estimation JSON 
    (for LLM analysis) or a trimmed response with only essential fields for material 
    price comparison.


    Args:
        material_list: A list of alphanumeric keys uniquely identifying the materials.
        plant_list: A list of keys uniquely identifying the plants to search within.
        costing_variant_list: Optional list of costing variants. The variant key determines how a cost estimate is performed and valuated.
        material_type_list: Optional list of material types. The type key assigns the material to a group like raw materials or trading goods.
        costing_status_list: Optional list of costing statuses, indicating the current processing status of the cost estimate (e.g., 'KA').
        costing_version: The version number that differentiates between cost estimates for the same material.
        currency_type_code: Specifies the currency, either from the Company Code ('10') or Controlling Area Currency.
        valid_on: A specific date (e.g., 'YYYY-MM-DD') to find cost estimates valid on that day.
        costing_date_from: The start date (e.g., 'YYYY-MM-DD') from which the cost estimate is valid.
        costing_date_to: The end date (e.g., 'YYYY-MM-DD') to which the cost estimate is valid.
        compare_prices: If True, limits the API response to only the essential fields needed for material price comparison. 
                        If False, retrieves the full detailed cost estimation JSON, leaving the analysis to the LLM.


    """
    # Construct the API payload from the function arguments
    payload = {
        "materialList": material_list,
        "plantList": plant_list,
        "costingVersion": costing_version,
        "currencyTypeCode": currency_type_code,
    }
    # Add optional list parameters to the payload only if they are provided
    if costing_variant_list:
        payload["costingVariantList"] = costing_variant_list
    if material_type_list:
        payload["materialTypeList"] = material_type_list
    if costing_status_list:
        payload["costingStatusList"] = costing_status_list

    logger.info(f"--- Calling Material Details API with payload: {payload} ---")

    try:
        # Get the mock API URL from environment variables, similar to your other tools
        mock_api_url = os.getenv("MOCK_CSC_API_URL", "http://localhost:8000")
        logger.info(f"mock API Url: {mock_api_url}")
        # You would replace 'materialDetails' with the actual endpoint path
        api_endpoint = f'{mock_api_url}'
        header= {"x-api-key": os.getenv("XAPI_KEY")}
        response = httpx.post(api_endpoint, json=payload, timeout=30.0,headers=header, verify=False)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

        response_data = response.json()

        # Check for a successful response code from the API's own message
        if response_data.get("code") == 200 and response_data.get("data", {}).get("data"):
            if compare_prices:
                return _get_material_price_comparison(response_data["data"]["data"])
            else:
                return {"items": response_data["data"]["data"]}
        else:
            return {"error": f"API returned non-200 status or no data. Message: {response_data.get('message', 'Unknown error')}"}

    except httpx.HTTPStatusError as e:
        logger.error(f"API request failed with status {e.response.status_code}: {e.response.text}", exc_info=True)
        return {"error": f"API request failed with status {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        return {"error": f"An unexpected error occurred: {e}"}

def _get_material_price_comparison(material_cost_json: List) -> dict:
    """
    Sorts the material cost JSON by costingDate and returns the latest two costing records for comparison.
    Args:
        material_cost_json (List): The full material cost JSON response (as shown in the sample).
    Returns:
        dict: Contains the latest two costing records sorted by costingDate (descending).
    """
    try:

        # Sort by costingDate descending
        sorted_data = sorted(material_cost_json, key=lambda x: x.get("costingDate", ""), reverse=True)
        logger.info(f"Sorted material cost data")
        if not sorted_data:
            return {"error": "No costing records found."}

        # Get the latest two unique costingDate values
        unique_dates = []
        for row in sorted_data:
            date = row.get("costingDate")
            if date and date not in unique_dates:
                unique_dates.append(date)
            if len(unique_dates) == 2:
                break
        logger.info(f"Latest two unique costing dates: {unique_dates}")

        # Get all rows for the latest two costingDates
        latest_rows = [row for row in sorted_data if row.get("costingDate") in unique_dates]
        logger.info(f"Sorting latest rows Done")
        return {"items": latest_rows}
    except Exception as e:
        return {"error": f"Failed to extract costing comparison: {e}"}

@tool
def get_plant_id_from_name(plant_name: str) -> str:
    """
    Translates a plant's common name (e.g., 'MBC Untertürkheim') into its official Plant ID
    (e.g., '3010'). It automatically corrects for minor spelling errors by finding
    the closest match in the cache.
    """
    logger.info(f"--- Searching for Plant ID for '{plant_name}' with fuzzy matching... ---")
    
    # Get all valid plant names from the imported cache variable
    all_plant_names = list(app.data_cache.PLANT_NAME_TO_ID_CACHE.keys())
    # Find the best fuzzy match for the user's input
    close_matches = difflib.get_close_matches(plant_name.lower(), all_plant_names, n=1, cutoff=0.8)
    
    if close_matches:
        best_match_name = close_matches[0]
        # Look up the ID from the imported cache variable
        plant_id = app.data_cache.PLANT_NAME_TO_ID_CACHE[best_match_name]
        logger.info(f"Found a match for '{plant_name}' with '{best_match_name}'. The Plant ID is {plant_id}.")
        return f"Found a match for '{plant_name}' with '{best_match_name}'. The Plant ID is {plant_id}."
    else:
        logger.info(f"Error: Could not find a close match for plant name '{plant_name}'. Please check the spelling.") 
        return f"Error: Could not find a close match for plant name '{plant_name}'. Please check the spelling."
# Tool to fetch all plant details (plantCode and plantName only)
@tool
def get_plant_list() -> dict:
    """
    Retrieves all plant details with their official Plant Code and Plant Name.
    Returns:
        dict: A dictionary with a list of plants, each containing 'plantCode' and 'plantName'.
    """
    try:
        mock_api_url = os.getenv("PLANT_DETAILS_API_URL", "http://localhost:8000")
        api_endpoint = f'{mock_api_url}'
        header = {"x-api-key": os.getenv("XAPI_KEY")}
        logger.info(f"Fetching plant data from: {api_endpoint}")

        response = httpx.get(api_endpoint, timeout=30.0, headers=header, verify=False)
        response.raise_for_status()
        all_plants = response.json().get("data", [])
        logger.info(f"Received {len(all_plants)} plant records.")

        # Only include plantCode and plantName in the result
        plant_list = [
            {
                "plantCode": plant.get("plantCode"),
                "plantName": plant.get("plantName")
            }
            for plant in all_plants if plant.get("plantCode") and plant.get("plantName")
        ]
        return {"plants": plant_list}

    except httpx.HTTPStatusError as e:
        logger.error(f"API request failed with status {e.response.status_code}: {e.response.text}", exc_info=True)
        return {"error": f"API request failed with status {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        return {"error": f"An unexpected error occurred: {e}"}
    
@tool
def get_costing_status_id_from_description(status_description: str) -> str:
    """
    Translates a costing status description (e.g., 'Costing Without Errors')
    into its official ID/code (e.g., 'KA'). Automatically corrects for minor
    spelling errors.
    """
    logger.info(f"--- Searching for Costing Status ID for '{status_description}' in cache... ---")
    
    # Get all valid status descriptions from the imported cache variable
    all_status_descriptions = list(app.data_cache.COSTING_STATUS_CACHE.keys())
    
    # Find the best fuzzy match for the user's input
    close_matches = difflib.get_close_matches(status_description.lower(), all_status_descriptions, n=1, cutoff=0.8)
    
    if close_matches:
        best_match_desc = close_matches[0]
        # Look up the ID from the imported cache variable
        status_id = app.data_cache.COSTING_STATUS_CACHE[best_match_desc]
        return f"Found a match for '{status_description}' with '{best_match_desc}'. The ID is {status_id}."
    else:
        return f"Error: Could not find a close match for costing status '{status_description}'."

@tool
def get_currency_type_code_from_description(currency_description: str) -> str:
    """
    Translates a currency type description (e.g., 'Company Code Currency')
    into its official code (e.g., '10'). Automatically corrects for minor
    spelling errors.
    """
    logger.info(f"--- Searching for Currency Type Code for '{currency_description}' in cache... ---")
    
    # Get all valid currency descriptions from the imported cache variable
    all_currency_descriptions = list(app.data_cache.CURRENCY_TYPE_CODE.keys())
    
    # Find the best fuzzy match for the user's input
    close_matches = difflib.get_close_matches(currency_description.lower(), all_currency_descriptions, n=1, cutoff=0.8)
    
    if close_matches:
        best_match_desc = close_matches[0]
        # Look up the code from the imported cache variable
        currency_code = app.data_cache.CURRENCY_TYPE_CODE[best_match_desc]
        return f"Found a match for '{currency_description}' with '{best_match_desc}'. The Code is {currency_code}."
    else:
        return f"Error: Could not find a close match for currency type '{currency_description}'."

@tool
def get_instructions_for_task(task_name: str) -> str:
    """
    Retrieves the detailed system prompt or 'playbook' for a specific, complex task like
    'cost_comparison', 'parts_usage', or 'material_search'. Use this as the first step when a user asks a
    complex question that requires a multi-step plan.
    """
    if task_name == "material_search":
        instructions_playbook = """# Material Search Instructions - Comprehensive Guide

                        ## CRITICAL: SYSTEM LIMITATIONS 
                        **READ-ONLY SYSTEM**: This system is designed for data retrieval only.
                        
                        **INTELLIGENTLY BLOCK DATA MANIPULATION REQUESTS**:
                        If user asks to INSERT, UPDATE, DELETE, CREATE, DROP, ALTER any data:
                        - Respond: "I cannot perform data modification operations. This system is read-only and designed for searching and retrieving material information only."
                        - Offer alternative: "I can help you search for existing materials, find similar parts, or retrieve material details. What would you like to find?"
                        - Do NOT generate SQL queries for data manipulation
                        - Do NOT use any tools for data modification attempts

                        ## Tool Selection & Priority
                        **ALWAYS** use `search_materials_comprehensive` tool first for ANY material search request.
                        This is your PRIMARY tool for:
                        - Finding similar parts
                        - Material lookups
                        - Part searches
                        - Alternative part identification

                        ## Search Type Determination
                        Choose the correct search type based on user input:

                        ### Description Search (search_type="description")
                        Use when user provides descriptive text like:
                        - "brake pad", "TRIM SIDE PANEL", "EL.LTG.SATZ"
                        - "Show me materials like brake components"
                        - "Find PROTECTIVE STRIP parts"
                        - "Show me maximum matching material for TRIM SIDE PANEL CTR RR LWR RH AL4"

                        ### Similar Parts Search (search_type="similar_parts")
                        Use when user provides a specific material number like:
                        - "A1234567890", "F920990007514", "A1675407259"
                        - "Find similar parts for A9066900362"
                        - "What parts are like material A1234567"

                        Process:
                        1. Tool finds the material's description first
                        2. Then searches for all parts with similar descriptions (limited to TOP 25)
                        3. **MANDATORY**: Execute count query to get actual total count
                        4. Perfect for "find similar parts for [material_number]" queries

                        **CRITICAL**: Execute ALL 3 steps - do not stop after limited results!
                        
                        CONSISTENCY ENFORCEMENT
                        **FOR MATERIAL A9076920402**: ALWAYS execute the EXACT same 3-step sequence:
                        1. Get description → "TRIM SIDE PANEL CTR RR LWR RH AL4"
                        2. Progressive substring search → TOP 25 results + SEPARATE TABLES  
                        3. Count query → Actual total counts (NOT just "25")
                        
                        **FORBIDDEN**: Different search strategies each time
                        **REQUIRED**: Deterministic ORDER BY m.material_number, m.material_desc
                        **MANDATORY**: Progressive substring patterns: 'TRIM SIDE PANEL CTR', 'TRIM SIDE PANEL', 'TRIM SIDE'

                        ## Business Logic - Two Cases:
                        **Case 1**: Description searches (exact + substring matching)
                        **Case 2**: Similar parts (get description → apply Case 1)

                        ## Result Processing & Display
                        The tool returns comprehensive results with:
                        - **Exact Matches**: Materials with identical descriptions
                        - **Substring Matches**: Materials containing meaningful words (improved filtering)

                        ## MANDATORY Response Format
                        **ALWAYS** display results in TWO SEPARATE TABLES - exact matches and substring matches:

                        ### Exact Matches:
                        | Material Number | MKP Component | End Number | Description | Price Per 1 |
                        |----------------|---------------|------------|-------------|--------------|
                        | A1234567890    | ABC123        | E001       | BRAKE PAD   | $10.00       |
                        | A1234567891    | N/A           | N/A        | BRAKE DISC  | $15.00       |

                        ### Similar Parts (Substring Matches):
                        | Material Number | MKP Component | End Number | Description | Price Per 1 |
                        |----------------|---------------|------------|-------------|--------------|
                        | B9876543210    | XYZ789        | E002       | BRAKE PAD FRONT | $12.00       |
                        | C5555444333    | N/A           | N/A        | BRAKE PAD REAR  | $14.00       |
                        

                        **Required Columns (in exact order):**
                        1. **Material Number** (unique identifier)
                        2. **MKP Component** (module component code)
                        3. **End Number** (end number identifier)  
                        4. **Description** (full material description)
                        5. **Price Per 1** (price per unit)

                        **CRITICAL:** 
                        - Use "N/A" for any empty/None fields
                        - NEVER combine exact and substring results in one table
                        - ALWAYS create separate sections with clear headers
                        - NEVER use numbered lists - ONLY use table format

                        ## MANDATORY Result Counts
                        **ALWAYS** include these counts prominently BEFORE each table:
                        - "Found X exact matches" (actual count from exact match query)
                        - "Found Y total similar parts" (actual count from COUNT query, NOT the limited results)
                        - If showing limited results: "Found 157 total similar parts (showing first 25)"
                        - **CRITICAL**: Use actual total counts from Step 3 count query, not the TOP limit numbers
                        - **WARNING**: Never show "25 similar parts" - always get the real count with COUNT query

                        ## User Communication Guidelines
                        1. Explain what type of search was performed
                        2. Present results in TWO SEPARATE TABLES with clear headers
                        3. Show ACTUAL total counts, then display limited results for performance
                        4. Clarify the difference between exact and substring matches
                        5. If many results found, explain "showing first X of Y total" clearly
                        6. Provide helpful context about the materials found
                        7. For material number searches, mention the original material being searched

                        ## Advanced SQL Generation (when needed)
                        If comprehensive search doesn't work, use:
                        1. `generate_text2sql` for schema guidance
                        2. Generate custom SQL using your intelligence
                        3. `execute_sql_for_materials` to run your SQL

                        ## Error Handling
                        - Database connection errors: Inform user about authentication issues
                        - Empty results: "No materials found matching your criteria"
                        - Token errors: "Access token expired, contact administrator"
                        """
    
    elif task_name == "sql_generation":
        instructions_playbook = """# Single LLM SQL Generation Guide
        
                        ## Core Principle
                        YOU (the agent) generate ALL SQL using your own intelligence. No separate LLM needed.
                        
                        ## Process Flow
                        1. **Get Schema**: Call `generate_text2sql` for database structure guidance
                        2. **Generate SQL**: Use YOUR intelligence to create T-SQL queries
                        3. **Execute SQL**: Call `execute_sql_for_materials` with your generated query
                        4. **Format Results**: Present data in proper table format
                        
                        ## T-SQL Requirements
                        - Use `SELECT DISTINCT TOP N` (not LIMIT)
                        - **CRITICAL**: ORDER BY items must appear in SELECT list when using SELECT DISTINCT
                        - For progressive matching: Use TOP 15 without ORDER BY to avoid DISTINCT conflicts
                        - Schema: `[csc].[dwd_tb_dim_md_material]` and `[csc].[dwd_tb_dim_md_plant_material]`
                        - Required fields: `pm.mkp_component, m.endnumber, m.material_number, m.material_desc`
                        - Standard JOIN: `LEFT JOIN [csc].[dwd_tb_dim_md_plant_material] pm ON m.material_number = pm.material_number`
                        ### HARD CONSTRAINTS (MANDATORY)
                        - Never reference tables outside the `[csc]` schema for materials listing.
                        - The ONLY allowed objects for listing materials are:
                            1) `[csc].[dwd_tb_dim_md_material]` (alias `m`)
                            2) `[csc].[dwd_tb_dim_md_plant_material]` (alias `pm`)
                        - Do NOT invent or use a table named `materials` (or any unqualified table names).
                        - Always qualify table names with the schema.
                        - For plant filters, always filter on `pm.plant_code = '<resolved_plant_code>'`.
                        - If the user gives a plant **name**, FIRST resolve it to a code using `get_plant_id_from_name`, then use that code in SQL.

                        #  Pagination (Azure SQL)
                        - **Pagination (Azure SQL)**:
                        - Use `OFFSET/FETCH` (not `TOP`) for paginated listings.
                        - Parameters:
                            - `@page INT = 1`  (1-based)
                            - `@page_size INT = 50`
                            - `@offset INT = (@page - 1) * @page_size`
                        - **ORDER BY is required** with OFFSET/FETCH; choose a stable, indexed key (e.g., `m.material_number`), and add a tiebreaker if needed (e.g., `m.material_desc`).
                        - When using `DISTINCT` with `ORDER BY`, **every ORDER BY column must be in the SELECT list** (keep existing rule).
                        - Caller infers `has_more` as `rows_returned == @page_size`.

                        #  When to use TOP vs OFFSET/FETCH
                        - Keep `TOP 15` **only** for progressive/quick matching probes **without** pagination and **without** `ORDER BY` (as per existing rule).
                        - For user-visible lists (e.g., “show materials in plant …”), **do not** use `TOP`; use `OFFSET/FETCH` pagination.

                        #  Canonical Pagination Template
                        ```sql
                        -- Pagination template (listing)
                        -- DECLARE @page INT = 1, @page_size INT = 50;
                        -- DECLARE @offset INT = (@page - 1) * @page_size;

                        SELECT DISTINCT
                            ISNULL(pm.mkp_component,'NULL') AS mkp_component,
                            ISNULL(m.endnumber,'NULL')      AS endnumber,
                            m.material_number,
                            m.material_desc,
                            ISNULL(pm.plant_code,'NULL')    AS plant_code
                        FROM [csc].[dwd_tb_dim_md_material] AS m
                        LEFT JOIN [csc].[dwd_tb_dim_md_plant_material] AS pm
                        ON m.material_number = pm.material_number
                        WHERE 1=1
                        -- add predicates as needed, e.g. pm.plant_code = @plant_code
                        ORDER BY
                        m.material_number                 -- stable, indexed key
                        -- , m.material_desc              -- optional tiebreaker
                        OFFSET @offset ROWS FETCH NEXT @page_size ROWS ONLY;
                        
                        ## CRITICAL: Deterministic Ordering for Consistency
                        **ALWAYS** use deterministic ordering to ensure consistent results across multiple calls:
                        - **MAIN QUERIES**: Use `ORDER BY m.material_number, m.material_desc` for consistent results
                        - **UNION ALL QUERIES**: Place ORDER BY at the very end (after all UNION parts)
                        - **CONSISTENT RESULTS**: Same query should always return same results in same order
                        - **NO RANDOM ORDERING**: Never rely on database default ordering
                        
                        ## Search Patterns
                        - Exact material: `WHERE m.material_number = @material_number ORDER BY m.material_number, m.material_desc OFFSET @offset ROWS FETCH NEXT @page_size ROWS ONLY;`
                        - Exact description: `WHERE m.material_desc = 'EXACT TEXT' ORDER BY m.material_number, m.material_desc OFFSET @offset ROWS FETCH NEXT @page_size ROWS ONLY;`
                        - Substring (excluding exact): `WHERE m.material_desc LIKE '%SEARCH%' AND m.material_desc != 'EXACT_TEXT' ORDER BY m.material_number, m.material_desc OFFSET @offset ROWS FETCH NEXT @page_size ROWS ONLY;`
                        - Progressive patterns: `WHERE m.material_desc LIKE '%WORD1 WORD2%' AND m.material_desc != 'FULL_EXACT_TEXT' ORDER BY m.material_number, m.material_desc OFFSET @offset ROWS FETCH NEXT @page_size ROWS ONLY;`

                        ## CRITICAL: Similar Parts Exclusion Pattern
                        **ALWAYS** exclude exact matches from substring searches to find truly similar parts:
                        - CORRECT: `WHERE m.material_desc LIKE '%TRIM SIDE PANEL%' AND m.material_desc != 'TRIM SIDE PANEL CTR RR LWR RH AL4'`
                        - WRONG: `WHERE m.material_desc LIKE '%TRIM SIDE PANEL CTR RR LWR RH AL4%'` (includes exact duplicates)
                        
                        ## Deterministic UNION ALL Example for Similar Parts:
                        ```sql
                        -- Step 2: Get limited results for display
                        SELECT DISTINCT  pm.mkp_component, m.endnumber, m.material_number, m.material_desc
                        FROM [csc].[dwd_tb_dim_md_material] m
                        LEFT JOIN [csc].[dwd_tb_dim_md_plant_material] pm ON m.material_number = pm.material_number
                        WHERE m.material_desc = 'TRIM SIDE PANEL CTR RR LWR RH AL4'
                        UNION ALL
                        SELECT DISTINCT pm.mkp_component, m.endnumber, m.material_number, m.material_desc
                        FROM [csc].[dwd_tb_dim_md_material] m
                        LEFT JOIN [csc].[dwd_tb_dim_md_plant_material] pm ON m.material_number = pm.material_number
                        WHERE m.material_desc LIKE '%TRIM SIDE PANEL%' AND m.material_desc != 'TRIM SIDE PANEL CTR RR LWR RH AL4'
                        ORDER BY m.material_number, m.material_desc
                        OFFSET @offset ROWS FETCH NEXT @page_size ROWS ONLY;
                        ```
                        ## Guardrails for Instruction Placeholders
                        - Tokens like `EXACT_DESCRIPTION_FROM_STEP1`, `SUBSTRING_DESCRIPTION_FROM_STEP2`, or any pattern
                        matching `[A-Z_]+_FROM_STEP\d+` are **instructional placeholders**, not data.
                        - **Never** emit these tokens in SQL. If a description variable resolves to an instructional token, treat it as **missing**.
                        - If description is missing/invalid:
                        - Do **not** add description predicates.
                        - Prefer the **Plant Inventory Listing** path when the user asked “materials in/from/at <plant>”.

                        ## Pagination (OFFSET/FETCH)
                        - Use `@page` (1-based) and `@page_size` (default 50) with `@offset = (@page-1)*@page_size`.
                        - Always return only `@page_size` rows; tell the user: “Showing page {@page} (50 rows). Say ‘next’ or give a page number, or add filters.”

                        ## Count Query Example for Actual Totals:
                        ```sql
                        -- Step 3: Get actual total count (no TOP limit)
                        SELECT COUNT(*) as total_count
                        FROM [csc].[dwd_tb_dim_md_material] m
                        WHERE m.material_desc LIKE '%TRIM SIDE PANEL%' AND m.material_desc != 'TRIM SIDE PANEL CTR RR LWR RH AL4'
                        ```
                        
                        **Usage**: Step 2 shows "first 25", Step 3 shows "total 157" for accurate reporting.
                        """
                        
    elif task_name == "error_handling":
        instructions_playbook = """# Error Handling Guidelines
        
                        ## Database Connection Errors
                        If you see "Database connection failed" or "token" errors:
                        → "I'm unable to connect to the database right now. This is likely due to expired authentication. Please contact your administrator to refresh the database connection."
                        
                        ## Authentication Errors  
                        If you see "Login failed" or "authentication" errors:
                        → "There's an authentication issue with the database. Please ensure your access tokens are valid and try again."
                        
                        ## No Results vs Connection Issues
                        - Empty results ([]): "No materials found matching your criteria."
                        - Connection errors: Explain the technical issue clearly to the user.
                        
                        ## General Error Handling
                        - Always provide helpful context about what went wrong
                        - Suggest next steps when possible  
                        - Don't just say "No materials found" for technical errors
                        - Check for "connection_failed" flag in tool responses
                        """
    
    elif task_name=="get_material_cost_details":
        logger.info(f"instructions: {task_name}")
        instructions_playbook=  """# Steps to consider when handling get_material_cost_details tool:
                                    Key Instructions & Constraints

                                    1. Initial Check:
                                    - If the user's query does not specify a plant, check if it has been specified in the chat history. If not, immediately stop and ask the user for the plant location before proceeding.

                                    2. Costing Variant Filter:
                                    - For a given material ID, first identify the latest costing date across all entries and sort the costing dates in descending order.
                                    - Check if this latest costing date falls within one of the required costing variants: ZPA1, ZPA0, or YPA0. If it does not, inform the user that the material is not eligible for this analysis and terminate the process.

                                    3.  Latest Costing Status Check (Conditional Stop):
                                        *   Step 1 (New Costing): Retrieve the latest costing date for the material.
                                        *   Step 2 (Status Check): Check the costingStatus for this latest costing date.
                                        *   Step 3 (Conditional Stop):
                                            *   **If the costingStatus for the LATEST costing date is "FR" (Released) or "KF" (Costing with errors), IMMEDIATELY STOP the analysis and inform the user that the latest costing is either released or has errors.**
                                            *   **If the costingStatus for the LATEST costing date is "KA" (Costing without Errors), IMMEDIATELY STOP the analysis and inform the user that the latest costing is without errors.**
                                            *   **DO NOT proceed to any further steps if the analysis is stopped based on the costingStatus of the LATEST costing date.**
                                    4.  Data Extraction for Comparison  (ONLY if the analysis has NOT been stopped in Step 3):
                                        *   If, and ONLY if, the analysis was NOT stopped in Step 3 because the latest costing status was neither "FR" nor "KF" nor "KA", then proceed to retrieve the following data:
                                            *   New Costing: Find the Total Value and Currency for the latest costing date.
                                            *   Old Costing: Find the Total Value and Currency for the next former costing date that has a costingStatus of "FR".
                                            
                                    5. Comparison and Validation (ONLY if the analysis has NOT been stopped in Step 3):
                                    - Compare the Total Value of the new and old costing.
                                    - Verify that the Currency is the same for both. If they are different, explicitly state this in your output. If the currency is empty for both, proceed without mentioning it.

                                    6. Crucial Constraint (ONLY if the analysis has NOT been stopped in Step 3):
                                    - DO NOT invent or assume any data. If any required information (e.g., old costing data) is missing, state this clearly in the final result.

                                    7. Us chain of thought (ONLY if the analysis has NOT been stopped in Step 3): 
                                    - Use chain of thought to validate and answer accordingly as there are many logical steps involved.

                                    8. Output Format (ONLY if the analysis has NOT been stopped in Step 3):
                                    - Your final response must be a Markdown table. Do not include any conversational filler or preambles. The table must have the following columns in this exact order:
                                        - Material ID
                                        - New Costing Total Value
                                        - Old Costing Total Value
                                        - New costing date
                                        - Old costing date
                                        - Currency
                                        - Costing Per 1 (Calculated as New Costing Total Value / Costing Lot Size)"""
                                        # and Explain the steps that you have performed step by step, Also explain the calculations by showing the values as well
                                        # eg: Costing date is 2025-07-20 which is latest than 2025-06-25. Make sure you add values for the steps"""
    else:
        # General instructions for any other tasks with READ-ONLY constraint
        instructions_playbook = f"""No specific instructions found for task: {task_name}. 
        Available tasks: material_search, sql_generation, error_handling, get_material_cost_details
        
        **IMPORTANT: READ-ONLY SYSTEM CONSTRAINT**
        This system only supports data retrieval and search operations. 
        If users request data modification (INSERT, UPDATE, DELETE, CREATE, DROP, etc.):
        - Politely explain this is a read-only system
        - Offer alternative search/retrieval options
        - Do not attempt to generate modification queries"""
        
    logger.info(f"--- Fetching instructions for task: {task_name} ---")
    return instructions_playbook


@tool
def get_price_for_plant(plant_code: int) -> float:
    """
    Returns price for the given plant code.
    If not in the mapping, generates a random value (10-20), stores it, and returns it.
    """
    # ✅ Predefined mapping (fixed values)
    plant_price_mapping = {
    2821: 12.11, 2827: 13.34, 3010: 17.22, 3050: 9.32, 3051: 8.74,
    3059: 11.34, 3075: 9.07, 3838: 11.63, 6185: 9.25,
    2800: 16.2, 2801: 13.4, 2802: 17.1, 2803: 10.8, 2806: 18.5,
    2807: 15.2, 2809: 11.6, 2810: 19.3, 2811: 14.7, 2812: 16.8,
    2813: 11.4, 2816: 13.7, 2817: 18.2, 2818: 17.4, 2822: 15.1,
    2824: 11.9, 2826: 17.8, 2828: 19.1, 2829: 12.3, 2830: 18.9,
    2831: 13.9, 2836: 14.6, 3000: 12.8, 3002: 16.5, 3008: 11.5,
    3015: 13.2, 3019: 19.5, 3020: 15.7, 3040: 12.6, 3042: 18.1,
    3054: 17.2, 3061: 15.8, 3065: 12.4, 3067: 16.9, 3068: 14.5,
    3088: 11.3, 3090: 19.2, 3091: 13.1, 3097: 12.9, 3117: 15.9,
    3167: 14.4, 3192: 10.7, 3371: 17.6, 3390: 12.1, 3429: 19.7,
    3516: 18.3, 3601: 14.2, 3616: 13.3, 3693: 17.7, 3788: 11.8,
    3944: 16.1, 4147: 12.7, 4380: 18.7, 4383: 19.6, 4831: 14.8,
    4840: 16.3, 5560: 13.6, 6038: 11.2, 7920: 17.5
    }
    if plant_code not in plant_price_mapping:
        random_price = round(random.uniform(10, 20), 1)
        plant_price_mapping[plant_code] = random_price
        print(f"⚠️ Plant {plant_code} not in mapping. Generated new price = {random_price}")
    return plant_price_mapping[plant_code]