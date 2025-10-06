"""
Single LLM Text2SQL Tool for CSC Agent
This tool allows the agent to generate SQL queries using its own intelligence.
"""

from langchain_core.tools import tool
from typing import Dict, Optional
import sys
import os
import logging

# Assume the logger is configured in a central place, or configure it here.
from app.logger.logger_config import setup_logger
logger= setup_logger("INFO")

# Assuming these functions are in the path and available for import
from app.database.query_executor import execute_sql_query
from app.text2sql.shield import protect_db
from app.text2sql.domain_knowledge import TEXT2SQL_DOMAIN_KNOWLEDGE, CSC_SCHEMA_INFO


@tool
def generate_text2sql(
    natural_language_request: str,
    table_schema: str = "",
    search_context: Dict = None
) -> str:
    """
    This tool provides CSC database schema knowledge and patterns to help the agent
    generate appropriate SQL queries using its own intelligence. The agent uses this
    tool to understand the database structure and create queries dynamically.
    
    Args:
        natural_language_request: What the agent wants to query (e.g., "Find materials with material number X")
        table_schema: Specific schema info if needed
        search_context: Additional context like search type, terms, limits
        
    Returns:
        Database schema knowledge and query patterns for the agent to use
    """
    
    logger.info(f"Agent requesting SQL generation guidance for: {natural_language_request}")
    
    # Extract context if provided
    context_info = ""
    if search_context:
        search_type = search_context.get('search_type', 'description')
        search_term = search_context.get('search_term', '')

        # Pagination defaults (OFFSET/FETCH): page is 1-based
        page = int(search_context.get('page', 1))
        page_size = int(search_context.get('page_size', 50))
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 50
        offset = (page - 1) * page_size

        context_info = f"""
        Search Context:
        - Type: {search_type}
        - Term: '{search_term}'
        - Page: {page}
        - Page Size: {page_size}
        - Offset: {offset}
        """
        
        logger.info(f"Context: {search_type} search for '{search_term}'")
    schema_guidance = f"""
    Request: "{natural_language_request}"
    {context_info}
    
    **SYSTEM CONSTRAINT: READ-ONLY ACCESS**
    This system only supports data retrieval (SELECT operations).
    Data modification operations are not available.
    
    {CSC_SCHEMA_INFO}
    
    **IMPORTANT: This is SQL Server (T-SQL) - NOT MySQL!**
    
    Common Patterns:
    - Material Number Lookup: WHERE m.material_number = @material_number (find description OF this material)
    - Exact Description: WHERE m.material_desc = @description
    - Description Contains: WHERE m.material_desc LIKE '%' + @search + '%'
    - Ordering (deterministic): ORDER BY m.material_number, m.material_desc
    - Pagination for listings: OFFSET @offset ROWS FETCH NEXT @page_size ROWS ONLY
    - Quick probes only: SELECT TOP 15 ... (no ORDER BY)
    
    **CRITICAL DISTINCTION**:
    - Looking up a material number: WHERE m.material_number = @material_number
    - Searching by description text: WHERE m.material_desc = @description (or LIKE)
    
    Example Material Number Lookup:
    SELECT TOP 1 m.material_desc
    FROM [csc].[dwd_tb_dim_md_material] m
    WHERE m.material_number = @material_number
    
    Example Query Template (paginated listing):
    -- DECLARE @page INT = 1, @page_size INT = 50;
    -- DECLARE @offset INT = (@page - 1) * @page_size;

    SELECT DISTINCT
        ISNULL(pm.mkp_component, 'NULL') as mkp_component, 
        ISNULL(m.endnumber, 'NULL') as endnumber, 
        m.material_number, 
        m.material_desc, 
        ISNULL(pm.plant_code, 'NULL') as plant_code
    FROM [csc].[dwd_tb_dim_md_material] m
    LEFT JOIN [csc].[dwd_tb_dim_md_plant_material] pm ON m.material_number = pm.material_number
    WHERE [YOUR_CONDITIONS]
    ORDER BY m.material_number, m.material_desc
    OFFSET @offset ROWS FETCH NEXT @page_size ROWS ONLY;
    
    **CRITICAL: Always use T-SQL syntax (TOP), never MySQL syntax (LIMIT)!**
    - For pagination: use OFFSET/FETCH (NOT LIMIT).
    - Use TOP only for short, non-paginated probes (e.g., progressive matching without ORDER BY).
    
    Please generate a T-SQL SELECT query based on this schema and your request.
    """
    
    logger.info("Providing schema guidance to agent for SQL generation")
    return schema_guidance.strip()


@tool
def search_materials_comprehensive(
    search_query: str,
    search_type: str = "description",
    material_number: str = None
) -> dict:
    """
    Comprehensive material search coordinator that guides the agent through the business logic.
    This tool does NOT generate SQL - it provides guidance for the agent to generate SQL using its intelligence.
    
    Args:
        search_query: The search term (description or material number)
        search_type: Type of search - "description" or "similar_parts" 
        material_number: Material number for similar parts search (Case 2)
        
    Returns:
        Dictionary containing business logic guidance for the agent

    ----------------------------------------------------------------
    Business Logic Guidance:
    
    Case 1: Description Search (e.g., "TRIM SIDE PANEL CTR RR LWR RH AL4")
    - Agent should: 
      1) Generate SQL for exact matches 
      2) Generate SQL for substring/prefix matches (exclude exacts) 
      3) Display in two separate paginated tables.

    Case 2: Similar Parts Search (e.g., "Find similar parts for A1675407259")
    - Agent should: 
      1) Generate SQL to resolve description for the given material number
      2) Use that description as @exact_desc
      3) Run two paginated queries:
         a) Exact Matches → WHERE m.material_desc = @exact_desc
         b) Similar Parts → WHERE m.material_desc LIKE @first_token + '%' AND m.material_desc <> @exact_desc
      4) Display results in two separate tables with deterministic ordering

    ----------------------------------------------------------------

    Result Presentation:
    - Always display results in **markdown tables**
    - Show two distinct sections:
        1) ### Exact Matches  
           - Paginated table of materials with identical description
           - Hint text: "Page {exact_page}. Say 'next exact' or 'previous exact'."
        2) ### Similar Parts (Prefix Matches)  
           - Paginated table of materials starting with the first token of description
           - Hint text: "Page {similar_page}. Say 'next similar' or 'previous similar'."
    - If a bucket returns < @page_size rows, do not suggest "next" for that bucket.
    - Only use plain text if the result is a single scalar value.
    
    ----------------------------------------------------------------
    Critical Rules:
    - Never emit instructional placeholders (e.g., EXACT_DESCRIPTION_FROM_STEP1).
    - Always exclude exact matches from the similar list.
    - Always apply deterministic ORDER BY.
    - If plant scope is present, include AND pm.plant_code = @plant_code in both buckets.
    - Count queries (SELECT COUNT(*)) should only be executed if the user explicitly requests totals.
    """

    
    logger.info(f"Comprehensive Search Coordinator invoked for: '{search_query}' (Type: {search_type})")
    
    try:
        guidance = {
            "business_logic": "",
            "steps": [],
            "expected_output_fields": ["mkp_component", "endnumber", "material_number", "material_desc", "plant_code"],
            "search_query": search_query,
            "search_type": search_type
        }
        
        if search_type == "similar_parts":
            logger.info(f"Initiating similar parts search for material: {material_number}")
            if not material_number:
                material_number = search_query
            # Case 2: Similar parts search - Find materials with similar descriptions
            guidance["business_logic"] = f"""
                **CASE 2: SIMILAR PARTS SEARCH FOR MATERIAL {material_number} (Exact-first, Similar-on-demand, Pagination on both)**

                GOAL
                1) Resolve the **exact description** of material **{material_number}**.
                2) Return **only the Exact Matches** list first, with **deterministic ordering**.
                WHERE criteria for Exact:
                    - m.material_desc = @exact_desc
                    - AND (@plant_code IS NULL OR pm.plant_code = @plant_code)
                **Exact Pagination**:
                    - Default: page = 1, page_size = 50
                    - offset = (page - 1) * page_size
                    - Use SQL Server: OFFSET {{offset}} ROWS FETCH NEXT {{page_size}} ROWS ONLY
                    - **Do NOT declare SQL scalar variables** for paging (no DECLARE/SET). Substitute integers inline.
                3) Then **ask the user**: "Show similar parts (prefix matches) too?" and **wait**.
                If user confirms, return the **Similar Parts (Prefix)** list with deterministic ordering.
                WHERE criteria for Similar:
                    - m.material_desc LIKE @first_token + '%'
                    - AND m.material_desc <> @exact_desc
                    - AND (@plant_code IS NULL OR pm.plant_code = @plant_code)
                **Similar Pagination**:
                    - Default: page = 1, page_size = 50
                    - offset = (page - 1) * page_size
                    - Use SQL Server: OFFSET {{offset}} ROWS FETCH NEXT {{page_size}} ROWS ONLY
                    - **No SQL variable declarations**; substitute integers inline.

                RULES
                - Never emit instructional placeholders (e.g., EXACT_DESCRIPTION_FROM_STEP1).
                - Deterministic order **always**: ORDER BY m.material_number, m.material_desc.
                - If plant scope is provided, apply AND pm.plant_code = @plant_code to **both** lists.
                - Run COUNT(*) only if the user explicitly requests totals.
                - **Even if the user asks for “similar parts”, you MUST first run and show the Exact Matches list, then ask about Similar. Do not ask about Similar until after Exact is shown.**
                - When Similar has **NOT** been shown yet, bare commands "next", "previous", or "page N" apply to the **Exact** list.
                - After Similar **has** been shown, bare "next/previous/page N" are **ambiguous** — ask:
                "Do you mean the Exact list or the Similar list?"

                CRITICAL AGENT BEHAVIOR REQUIREMENT
                The agent MUST ALWAYS execute this sequence for similar-parts queries:
                1. Get description query → execute
                2. Exact Matches list (**paginated via OFFSET/FETCH, integers inline**) → execute
                3. Ask: "Show similar parts (prefix matches) too?" → **wait for user**
                4. If user **confirms**, Similar Parts list (**paginated via OFFSET/FETCH, integers inline**) → execute
                5. If totals explicitly requested → run COUNT queries for the lists that were shown

                FORBIDDEN
                - Combining Exact and Similar into a single query
                - Skipping deterministic ORDER BY
                - Including placeholder tokens (e.g., EXACT_DESCRIPTION_FROM_STEP1)
                - Mixing results into one table
                - Declaring SQL variables for paging (no DECLARE/SET for either list). Use **inline numerals** only.

                CONSISTENCY REQUIREMENT
                - ALWAYS show Exact Matches and Similar Parts in **separate tables** (when Similar is requested),
                both ordered by m.material_number, m.material_desc.
                - Do not run the Similar query unless the user agrees.

                USER INTENTS
                - Exact pagination:
                • Before Similar is shown: "next", "previous", "page N" (applies to Exact)
                • After Similar is shown: "next exact", "previous exact", "page N exact"
                - Similar pagination:
                • "next similar", "previous similar", "page N similar"
                - Show Similar:
                • Positive → "yes", "ok", "show similar", "similar please", "go ahead"
                • Negative → "no", "only exact"

                Plant scoping (include/exclude, multi):
                - Detect plant mentions from user text. Accept formats like:
                    • "plant 3010", "for 3010", "in 3010", "for plant 3010"
                    • Multi: "plants 3010,4010", "for 3010 4010", "3010; 4010"
                    • Exclude: "exclude 3010", "without 3010", "except 3010, 4010"
                - Sanitize: keep only tokens matching ^\d{3,5}$ (digits only), de-duplicate, limit to max 20 codes.
                - Inclusion logic (default when user says 'for', 'in', lists without 'exclude/without/except'):
                    → add predicate:   AND pm.plant_code IN ('P1','P2',...,'Pk')
                - Exclusion logic (when user says 'exclude', 'without', 'except'):
                    → add predicate:   AND pm.plant_code NOT IN ('P1','P2',...,'Pk')
                    (Optionally keep NULLs by using: AND (pm.plant_code IS NULL OR pm.plant_code NOT IN (...)))
                - IMPORTANT: Inline literals only. Do NOT declare or use SQL variables for plant filters.
                - If no valid plant tokens found, omit the plant predicate entirely.
                - Plant scoping:
                • Include: "plant 3010", "for 3010", "in 3010", "plants 3010,4010"
                • Exclude: "exclude 3010", "without 3010", "except 3010 4010"
            """


            guidance["steps"] = [
                {
                    "step": 1,
                    "action": "get_description",
                    "instruction": (
                        "Resolve the exact description for the given material number.\n"
                        "SQL pattern:\n"
                        "SELECT TOP 1 m.material_desc\n"
                        "FROM [csc].[dwd_tb_dim_md_material] m\n"
                        "WHERE m.material_number = @material_number\n"
                        "ORDER BY m.material_desc;"
                    ),
                    "required_fields": ["@exact_desc"],
                    "search_type": "material_number_lookup",
                    "critical_note": (
                        f"You are looking up the description OF material number {material_number}, "
                        "not searching for materials WITH that number as description."
                    ),
                    "completion_note": (
                        "After obtaining @exact_desc, compute @first_token (first token of @exact_desc). "
                        "**MANDATORY NEXT ACTIONS (no user-facing text yet):** "
                        "1) Call tool `generate_text2sql` to build the Step-2 (Exact) SQL. "
                        "2) Immediately call tool `execute_sql_for_materials` with that SQL. "
                        "Only after Step-2 rows are returned may you speak to the user."
                    )
                },
                {
                    "step": 2,
                    "action": "list_exact_matches_paginated",  # renamed to reflect pagination
                    "instruction": (
                        "**Execute now. Do not ask for confirmation.** "
                        "**Immediately execute this step after Step 1. Do not ask about Similar yet.** "
                        "Implement **pagination only for the Exact list**.\n"
                        "**Immediately execute this step after Step 1. Do not ask about Similar yet.**"
                            "Pagination commands:"
                            "- Default: page = 1, page_size = 50"
                            "- 'next' → page = last_page + 1"
                            "- 'previous' → page = max(1, last_page - 1)"
                            "- 'page N' → page = N"
                            "Compute offset = (page - 1) * page_size."
                            "**Do NOT declare SQL variables for paging — substitute integers inline.**"

                        "- Default: page = 1, page_size = 50. If user said 'next exact', page = last_page + 1; "
                        "'previous exact' → page = max(1, last_page - 1); 'page N exact' → page = N.\n"
                        "- Compute offset = (page - 1) * page_size.\n"
                        "- **Do NOT declare SQL variables for paging. Substitute integers inline.**\n\n"
                        "SQL pattern (Exact bucket with pagination via OFFSET/FETCH):\n"
                        "SELECT DISTINCT\n"
                        "  ISNULL(pm.mkp_component,'NULL') AS mkp_component,\n"
                        "  ISNULL(m.endnumber,'NULL')      AS endnumber,\n"
                        "  m.material_number,\n"
                        "  m.material_desc,\n"
                        "  ISNULL(pm.plant_code,'NULL')    AS plant_code\n"
                        "FROM [csc].[dwd_tb_dim_md_material] m\n"
                        "LEFT JOIN [csc].[dwd_tb_dim_md_plant_material] pm\n"
                        "  ON m.material_number = pm.material_number\n"
                        "WHERE m.material_desc = @exact_desc\n"
                        "WHERE m.material_desc = @exact_desc\n"
                        "-- Plant filter (choose exactly one block if plants were detected; otherwise omit):\n"
                        "-- Inclusion example:\n"
                        "--   AND pm.plant_code IN ('3010','4010','5010')\n"
                        "-- Exclusion example (simple):\n"
                        "--   AND pm.plant_code NOT IN ('3010','4010')\n"
                        "-- Exclusion example (keep NULLs):\n"
                        "--   AND (pm.plant_code IS NULL OR pm.plant_code NOT IN ('3010','4010'))\n"
                        "  AND (@plant_code IS NULL OR pm.plant_code = @plant_code)\n"
                        "ORDER BY m.material_number, m.material_desc\n"
                        "OFFSET {{offset}} ROWS FETCH NEXT {{page_size}} ROWS ONLY;"
                        "**Price per 1 population (MANDATORY):**\n"
                        "1) Collect the set of distinct plant_code values from the result rows.\n"
                        "2) For each distinct plant_code, call tool `get_price_for_plant(plant_code)` exactly once and cache the returned value for this conversation turn.\n"
                        "3) Set `price_per_1` for each row by looking up its plant_code in the cached map; format as €xx.xx (two decimals).\n"
                        "4) If the tool errors for any plant_code, fall back for those rows only to a random value in €10.00–€20.00 (two decimals). Do NOT seed randomness. Do NOT reuse a single random value across multiple rows.\n"
                        "5) Do NOT query price from SQL. All price values come from the tool or the fallback.\n"

                    ),
                    "result_bucket": "Exact Matches",
                    "presentation": (
                                                "STRICT OUTPUT FORMAT — TABLE ONLY\n"
                                                "Start your message **directly** with a GitHub-flavored Markdown table. "
                                                "No leading sentences, no bullet points, no numbered lists.\n\n"
                                                "| mkp_component | endnumber | material_number | material_desc | plant_code | price_per_1 |\n"
                                                "|---|---|---|---|---|---|\n"
                                                "<one row per result in this exact column order>\n\n"
                                                "**Price source rule:** `price_per_1` is populated via the `get_price_for_plant(plant_code)` tool (cached per distinct plant in this turn). If the tool fails for a plant, use a one-off random fallback in €10.00–€20.00 for only those rows (two decimals). Never source price from SQL.\n\n"
                                                "Below the table, add exactly one helper line: "
                                                "\"Page {page} • Size {page_size}. Say \\\"next\\\", \\\"previous\\\", or \\\"page N\\\". "
                                                "Then: **Show similar (prefix) too?**\""
                                            ),
                    "expected_output_fields": [
                        "mkp_component",
                        "endnumber",
                        "material_number",
                        "material_desc",
                        "plant_code",
                        "price_per_1"
                    ],
                    "post_step_behavior": "STOP_AND_WAIT_FOR_USER"
                },
                {
                    "step": 3,
                    "action": "list_similar_prefix_paginated",
                    "instruction": (
                        "Execute this step **only if** the user confirms they want similar parts.\n"
                        "Compute @first_token = the first space-delimited token of @exact_desc "
                        "(e.g., 'TRIM' from 'TRIM SIDE PANEL ...'). Implement **pagination for Similar**.\n"
                        "- Default: page = 1, page_size = 50. If user said 'next similar', page = last_page + 1; "
                        "'previous similar' → page = max(1, last_page - 1); 'page N similar' → page = N.\n"
                        "- Compute offset = (page - 1) * page_size.\n"
                        "- **Do NOT declare SQL variables for paging. Substitute integers inline.**\n\n"
                        "SQL pattern (Similar bucket with pagination via OFFSET/FETCH):\n"
                        "SELECT DISTINCT\n"
                        "  ISNULL(pm.mkp_component,'NULL') AS mkp_component,\n"
                        "  ISNULL(m.endnumber,'NULL')      AS endnumber,\n"
                        "  m.material_number,\n"
                        "  m.material_desc,\n"
                        "  ISNULL(pm.plant_code,'NULL')    AS plant_code\n"
                        "FROM [csc].[dwd_tb_dim_md_material] m\n"
                        "LEFT JOIN [csc].[dwd_tb_dim_md_plant_material] pm\n"
                        "  ON m.material_number = pm.material_number\n"
                        "WHERE m.material_desc LIKE @first_token + '%'\n"
                        "  AND m.material_desc <> @exact_desc\n"
                        "-- Plant filter (choose exactly one block if plants were detected; otherwise omit):\n"
                        "-- Inclusion example:\n"
                        "--   AND pm.plant_code IN ('3010','4010','5010')\n"
                        "-- Exclusion example (simple):\n"
                        "--   AND pm.plant_code NOT IN ('3010','4010')\n"
                        "-- Exclusion example (keep NULLs):\n"
                        "--   AND (pm.plant_code IS NULL OR pm.plant_code NOT IN ('3010','4010'))\n"
                        "  AND m.material_desc <> @exact_desc\n"
                        "  AND (@plant_code IS NULL OR pm.plant_code = @plant_code)\n"
                        "ORDER BY m.material_number, m.material_desc\n"
                        "OFFSET {{offset}} ROWS FETCH NEXT {{page_size}} ROWS ONLY;"
                            "**Price per 1 population (MANDATORY):**\n"
                            "1) Collect the set of distinct plant_code values from the result rows.\n"
                            "2) For each distinct plant_code, call tool `get_price_for_plant(plant_code)` exactly once and cache the returned value for this conversation turn (reuse any cache built in Step 2 if present).\n"
                            "3) Set `price_per_1` for each row by looking up its plant_code in the cached map; format as €xx.xx (two decimals).\n"
                            "4) If the tool errors for any plant_code, fall back for those rows only to a random value in €10.00–€20.00 (two decimals). Do NOT seed randomness. Do NOT reuse a single random value across multiple rows.\n"
                            "5) Do NOT query price from SQL. All price values come from the tool or the fallback.\n"
                    ),
                        "expected_output_fields": [
                            "mkp_component",
                            "endnumber",
                            "material_number",
                            "material_desc",
                            "plant_code",
                            "price_per_1"
                        ],

                    "result_bucket": "Similar Parts (Prefix)",
                    "presentation": (
                        "STRICT OUTPUT FORMAT — TABLE ONLY\n"
                        "Start your message **directly** with a GitHub-flavored Markdown table. "
                        "No leading sentences, no bullet points, no numbered lists, no 'here are some of them'.\n\n"
                        "| mkp_component | endnumber | material_number | material_desc | plant_code | price_per_1 |\n"
                        "|---|---|---|---|---|---|\n"
                        "<one row per result in this exact column order>\n\n"
                        "**Price source rule:** `price_per_1` is populated via the `get_price_for_plant(plant_code)` tool (cached per distinct plant in this turn and shared with Step 2 if already built). If the tool fails for a plant, use a one-off random fallback in €10.00–€20.00 for only those rows (two decimals). Never source price from SQL.\n\n"
                        "After the table, on a new line, add exactly one helper sentence: "
                        "\"You can say \\\"next similar\\\" or \\\"page N similar\\\" for more similar parts.\""
                    ),
                    "run_condition": "USER_CONFIRMED_SHOW_SIMILAR"
                },
                {
                    "step": 4,
                    "action": "optional_counts_when_requested",
                    "instruction": (
                        "Only when the user asks for totals, run COUNT(*) for both buckets using identical filters.\n\n"
                        "-- Exact count\n"
                        "SELECT COUNT(*) AS exact_count\n"
                        "FROM [csc].[dwd_tb_dim_md_material] m\n"
                        "LEFT JOIN [csc].[dwd_tb_dim_md_plant_material] pm\n"
                        "  ON m.material_number = pm.material_number\n"
                        "WHERE m.material_desc = @exact_desc\n"
                        "  AND (@plant_code IS NULL OR pm.plant_code = @plant_code);\n\n"
                        "-- Similar (prefix) count\n"
                        "SELECT COUNT(*) AS similar_count\n"
                        "FROM [csc].[dwd_tb_dim_md_material] m\n"
                        "LEFT JOIN [csc].[dwd_tb_dim_md_plant_material] pm\n"
                        "  ON m.material_number = pm.material_number\n"
                        "WHERE m.material_desc LIKE @first_token + '%'\n"
                        "  AND m.material_desc <> @exact_desc\n"
                        "  AND (@plant_code IS NULL OR pm.plant_code = @plant_code);"
                    ),
                    "notes": "Skip COUNTs unless explicitly requested to reduce latency."
                }
            ]
            
        # else:
        #     logger.info(f"Initiating progressive search for material: {material_number}")
        #     # Progressive substring matching with decreasing word combinations
        #     all_words = [word.strip() for word in search_query.split() if len(word.strip()) > 0]
            
        #     # Generate progressive word combinations
        #     # Example: "TRIM SIDE PANEL CTR RR LWR RH AL4" 
        #     # → ["TRIM SIDE PANEL CTR RR LWR RH AL4", "TRIM SIDE PANEL CTR", "TRIM SIDE PANEL", "TRIM SIDE", "TRIM"]
        #     progressive_combinations = []
            
        #     if len(all_words) >= 2:
        #         # First add the full original text as highest priority
        #         progressive_combinations.append({
        #             'phrase': search_query.strip(),
        #             'word_count': len(all_words),
        #             'priority': len(all_words) + 1  # Highest priority
        #         })
                
        #         # Then add progressive combinations starting from half the word count down to minimum
        #         start_count = max(1, len(all_words) // 2)
                
        #         # For queries with more than 4 words, don't include single-word matches (too broad)
        #         # For very long queries, be more restrictive to avoid context overflow
        #         if len(all_words) > 6:
        #             min_word_count = 4  # Very restrictive for long queries
        #         elif len(all_words) > 4:
        #             min_word_count = 3  # Moderately restrictive
        #         else:
        #             min_word_count = 2  # Standard restriction
                
        #         for word_count in range(start_count, min_word_count - 1, -1):
        #             # Take the first 'word_count' words
        #             combination = ' '.join(all_words[:word_count])
        #             progressive_combinations.append({
        #                 'phrase': combination,
        #                 'word_count': word_count,
        #                 'priority': word_count  # Lower priority than full text
        #             })
        #     else:
        #         # Single word case - just use the original query
        #         progressive_combinations.append({
        #             'phrase': search_query,
        #             'word_count': 1,
        #             'priority': 1
        #         })
            
        #     # Create search instruction with progressive matching
        #     search_phrases = [combo['phrase'] for combo in progressive_combinations]
        #     priority_info = ', '.join([f"'{combo['phrase']}' (priority {combo['priority']})" for combo in progressive_combinations])
            
        #     guidance["business_logic"] = f"""
        #     Case 1: Progressive Substring Search for '{search_query}'
        #     You must execute ALL THREE steps using YOUR intelligence - do not stop after exact matches:
            
        #     1. Exact Match: Find materials with exactly matching descriptions
        #     2. Progressive Substring Match: **REQUIRED** - Find additional materials using decreasing word combinations for better coverage
        #        - Progressive combinations: {search_phrases}
        #        - Priority order: {priority_info}
        #        - Search strategy: Longer phrases first, then shorter ones
        #        - This ensures comprehensive material discovery beyond exact matches
        #        - Exclude exact matches from substring results to avoid duplicates
        #     3. Count Total: Count all progressive substring matches for reporting
            
        #     **IMPORTANT**: Even if exact matches are found, you MUST continue with progressive substring matching.
        #     This provides users with comprehensive material options and similar alternatives.
            
        #     Progressive Search Logic:
        #     - Use UNION ALL to combine results from each phrase length
        #     - Each phrase should use LIKE '%phrase%' matching
        #     - Present results in TWO SEPARATE TABLES: 1) Exact Matches, 2) Similar Parts (Substring Matches)
        #     - NEVER combine exact and substring results in one table
        #     """
            
        #     guidance["steps"] = [
        #         {
        #             "step": 1,
        #             "action": "exact_match",
        #             "instruction": f"Generate SQL for exact description match: material_desc = '{search_query}'. This is STEP 1 of 3 - continue to step 2 regardless of results.",
        #             "required_fields": ["ISNULL(pm.mkp_component, 'NULL') as mkp_component", "ISNULL(m.endnumber, 'NULL') as endnumber", "m.material_number", "m.material_desc", "ISNULL(pm.plant_code, 'NULL') as plant_code"],
        #             "presentation_note": "Present these results under '### Exact Matches:' section in separate table",
        #             "completion_note": "After completing this step, CONTINUE to progressive substring matching even if exact matches are found."
        #         },
        #         {
        #             "step": 2,
        #             "action": "progressive_substring_match", 
        #             "instruction": f"MANDATORY STEP: Generate SQL for progressive substring matches using EXACTLY these phrases in this specific order: {search_phrases}. Create a UNION ALL query with exactly {len(progressive_combinations)} parts - one SELECT for each phrase. Each part must use SELECT DISTINCT TOP 5 with the same fields. Each WHERE clause must use LIKE '%phrase%' for the corresponding phrase. Exclude exact matches using AND m.material_desc != '{search_query}'. Do NOT skip any intermediate phrases - include all {len(progressive_combinations)} combinations. CRITICAL: Add ORDER BY m.material_number, m.material_desc at the very end (after all UNION ALL parts) for deterministic consistent results.",
        #             "required_fields": ["ISNULL(pm.mkp_component, 'NULL') as mkp_component", "ISNULL(m.endnumber, 'NULL') as endnumber", "m.material_number", "m.material_desc", "ISNULL(pm.plant_code, 'NULL') as plant_code"],
        #             "limit": 10,
        #             "progressive_phrases": progressive_combinations,
        #             "exact_phrase_count": len(progressive_combinations),
        #             "mandatory_phrases": [combo['phrase'] for combo in progressive_combinations],
        #             "substring_logic": f"Must generate exactly {len(progressive_combinations)} UNION ALL parts. No skipping intermediate phrases. All phrases are mandatory.",
        #             "deterministic_ordering": "ORDER BY m.material_number, m.material_desc at the end ensures consistent results across multiple calls",
        #             "sql_syntax_warning": "T-SQL Rule: ORDER BY items must appear in SELECT list when using SELECT DISTINCT. Place ORDER BY at the very end after all UNION ALL parts.",
        #             "presentation_note": "Present these results under '### Similar Parts (Substring Matches):' section in separate table from exact matches",
        #             "completion_note": "This step is required regardless of exact match results. Must generate all progressive combinations consistently - no variations allowed."
        #         },
        #         {
        #             "step": 3,
        #             "action": "count_total",
        #             "instruction": f"Generate SQL to count total progressive substring matches using all phrase combinations: {search_phrases}",
        #             "required_fields": ["total_count"],
        #             "progressive_phrases": progressive_combinations
        #         }
        #     ]
        # logger.info("Business Logic Guidance Provided - Agent must generate ALL SQL queries")
        # logger.info("Agent should use: generate_text2sql -> YOUR SQL -> execute_sql_for_materials")
        
        return guidance
        
    except Exception as e:
        error_msg = f"Search coordination failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"error": error_msg}


@tool   
def execute_sql_for_materials(sql_query: str) -> dict:
    """
    Execute a SQL query against the CSC material database and return results.
    This tool should be used after the agent generates a SQL query.
    
    Args:
        sql_query: The SQL query to execute (generated by the agent)
        
    Returns:
        Dictionary containing query results or error information
    """
    
    logger.info("Executing agent-generated SQL query against CSC database...")
    logger.info(f"Agent Generated Query: {sql_query}")
    logger.info(f"Query Analysis: {len(sql_query)} characters")
    
    try:
        # Security check before execution
        if protect_db(sql_query):
            error_msg = "SQL query contains forbidden operations and was blocked for security"
            logger.warning(f"Security Alert: {error_msg}")
            return {"error": error_msg, "results": []}
        
        # Execute the query
        logger.info(f"Query: {sql_query}")
        results = execute_sql_query(sql_query)
        
        # Check if results is None (indicates connection failure)
        if results is None:
            error_msg = "Database connection failed. This may be due to expired authentication tokens or network issues. Please check the connection and try again."
            logger.error(error_msg)
            return {"error": error_msg, "results": [], "connection_failed": True}
        
        if results:
            logger.info(f"Query executed successfully, found {len(results)} results")
            return {"results": results, "count": len(results)}
        else:
            logger.warning("Query executed but returned no results")
            return {"results": [], "count": 0, "message": "No materials found matching the criteria"}
            
    except Exception as e:
        error_msg = f"Database query execution failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # Check if it's a token/authentication error
        if "token" in str(e).lower() or "login failed" in str(e).lower() or "authentication" in str(e).lower():
            error_msg = "Database authentication failed. The access token may have expired. Please refresh your authentication and try again."
        
        return {"error": error_msg, "results": []}
