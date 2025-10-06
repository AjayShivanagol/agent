from app.logger.logger_config import setup_logger
logger= setup_logger("INFO")
"""
CSC Agent Text2SQL Domain Knowledge
This module contains the domain knowledge and usage patterns for the text2sql tools.
"""
logger.info("Adding Domain knowledge")
TEXT2SQL_DOMAIN_KNOWLEDGE = """
## Text2SQL Tool Usage for Material Search

The agent now has access to specialized tools that eliminate the need for a separate LLM:

### 1. generate_text2sql Tool
- Provides CSC database schema knowledge and patterns
- Contains built-in understanding of table structures and relationships
- Supports different search types: material_number, description, exact_description
- Includes T-SQL syntax guidance and security considerations
- No separate LLM needed - uses agent's existing intelligence

### 2. search_materials_comprehensive Tool  
- Comprehensive search coordinator with business logic guidance
- Handles both Case 1 (description search) and Case 2 (similar parts)
- Provides step-by-step instructions for the agent
- Includes meaningful word extraction for better substring matching
- Guides agent through exact and substring search patterns

### 3. execute_sql_for_materials Tool
- Executes the generated SQL against CSC database
- Returns structured results with counts and error handling
- Includes security validation before execution
- Provides detailed feedback on query execution

### Usage Pattern:
1. Agent receives user request for material search
2. Agent calls search_materials_comprehensive for business logic guidance
3. Agent calls generate_text2sql for schema guidance
4. Agent generates SQL using its own intelligence
5. Agent calls execute_sql_for_materials with the generated query
6. Agent processes and formats results for user

### Search Types:
- **description**: Direct description search (e.g., "TRIM SIDE PANEL")
- **similar_parts**: Material number lookup then description search (e.g., "Find similar parts for A1675407259")

### Business Logic Cases:
- **Case 1**: Description Search - exact and substring matching
- **Case 2**: Similar Parts Search - get description first, then apply Case 1

### Key Features:
- **Single LLM Architecture**: Uses only the main agent LLM
- **Security First**: Built-in SQL injection protection
- **T-SQL Optimized**: Proper SQL Server syntax (TOP vs LIMIT)
- **Intelligent Filtering**: Meaningful word extraction for better substring matches
- **Automotive Focus**: Domain-aware filtering for relevant results

This approach achieves true single LLM architecture where the agent's intelligence drives the entire SQL generation process.
"""
logger.info("Adding Schema information")
# CSC Database Schema Reference
CSC_SCHEMA_INFO = """
## CSC Database Schema

### Main Tables:
1. [csc].[dwd_tb_dim_md_material] (alias: m)
   - material_number (VARCHAR): Unique material identifier
   - material_desc (VARCHAR): Material description text
   - endnumber (VARCHAR): End number identifier

2. [csc].[dwd_tb_dim_md_plant_material] (alias: pm)
   - material_number (VARCHAR): Links to main table
   - mkp_component (VARCHAR): Module component code
   - plant_code (VARCHAR): Plant code

### Standard Join Pattern:
LEFT JOIN [csc].[dwd_tb_dim_md_plant_material] pm ON m.material_number = pm.material_number

### Required Output Fields:
- ISNULL(pm.mkp_component, 'NULL') as mkp_component: module component from plant_material table
- ISNULL(m.endnumber, 'NULL') as endnumber: end number from material table  
- m.material_number: material number (primary key)
- m.material_desc: material description
- ISNULL(pm.plant_code, 'NULL') as plant_code: plant code from plant_material table
- Always include pm.plant_code when user requests plant information
- Use ISNULL function to display 'NULL' instead of empty values for null database fields

### T-SQL Syntax Rules:
- Use TOP N, NOT LIMIT N
- Correct: SELECT DISTINCT TOP 15 ...
- WRONG: SELECT ... LIMIT 15 (MySQL syntax)
- WRONG: SELECT TOP 15 DISTINCT ... (wrong order)

**Entity patterns & disambiguation (HARD RULES)**
- Plant code: tokens matching ^\\d{3,5}$  → ALWAYS treat as pm.plant_code. Never as a material number.
- Material number: must start with a letter (A/B/F/U) followed by digits (e.g., A9076920402, U0000000139020000).
  Pure digits are NOT material numbers.
- If the user says 'plant <code>' or 'in/for <code>', you MUST filter with: AND pm.plant_code IN ('<code>', ...).
"""
logger.info("Adding Business Logic")
# Business Logic Templates
BUSINESS_LOGIC_TEMPLATES = {
    "description_search": """
    Case 1: Description Search for '{search_query}'
    You must execute these steps using YOUR intelligence:
    
    1. Exact Match: Find materials with exactly matching descriptions
    2. Substring Match: Find materials containing meaningful words from the search term
       - Meaningful words extracted: {words}
       - Search for materials containing ANY of these meaningful words
       - Focus on automotive-relevant matches
       - Exclude exact matches from substring results
    3. Count Total: Count all substring matches for reporting
    """,
    
    "similar_parts": """
    Case 2: Similar Parts Search for {material_number}
    You must execute these steps using YOUR intelligence:
    
    1. Get Description: Use generate_text2sql to get schema guidance for finding material description
    2. Generate SQL: Create SQL to get description for material {material_number}
    3. Execute SQL: Use execute_sql_for_materials with your generated SQL
    4. Apply Case 1: Use the found description for exact and substring matching
    """
}
