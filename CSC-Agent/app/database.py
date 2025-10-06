# app/database.py

import os
import urllib
from sqlalchemy import create_engine, text
import logging

# Assume logger is configured elsewhere, or configure it here
from app.logger.logger_config import setup_logger
logger= setup_logger("INFO")

# 1) Environment variables for your server + database
SERVER   = os.getenv("AZURE_SQL_SERVER",   "sqlserverfcos.database.windows.net")
DATABASE = os.getenv("AZURE_SQL_DATABASE", "fcosdb1")
DRIVER   = os.getenv("AZURE_SQL_DRIVER",   "ODBC Driver 18 for SQL Server")
logger.info(f"Database settings loaded: SERVER={SERVER}, DATABASE={DATABASE}")

# 2) Build an ODBC connection string (no username/pw)
odbc_str = (
    f"Driver={{{DRIVER}}};"
    f"Server={SERVER},1433;"
    f"Database={DATABASE};"
    "Encrypt=yes;TrustServerCertificate=no;"
)
# URL‐encode for SQLAlchemy
params = urllib.parse.quote_plus(odbc_str)
logger.info("ODBC connection string created.")

# 3) Create a SQLAlchemy engine
engine = create_engine(
    f"mssql+pyodbc:///?odbc_connect={params}"
)
logger.info("SQLAlchemy engine created successfully.")

def _get_token_bytes() -> bytes:
    """
    Read the Azure AD access token from the environment and
    encode it as UTF-16LE for ODBC.
    """
    token = os.getenv("AZURE_SQL_ACCESS_TOKEN")
    if not token:
        logger.error("Missing AZURE_SQL_ACCESS_TOKEN in environment")
        raise RuntimeError("Missing AZURE_SQL_ACCESS_TOKEN in environment")
    return token.encode("utf-16-le")

def execute(query: str, **binds) -> list[dict]:
    """
    Execute a parametrized SQL query against Azure SQL using
    the latest bearer token for authentication.
    """
    try:
        # Inject the latest token for this connection
        token_bytes = _get_token_bytes()
        engine.dialect.connect_args = {"attrs_before": {1256: token_bytes}}

        # Debug output
        logger.info(f"Executing SQL: {query.strip()} Binds: {binds}")

        # Run the query
        with engine.connect() as conn:
            result = conn.execute(text(query), binds).mappings().all()
        
        logger.info(f"Query executed successfully, {len(result)} rows returned.")
        # Return rows as list of dicts
        return [dict(row) for row in result]
    except Exception as e:
        logger.error(f"Error executing SQL query: {e}", exc_info=True)
        raise

def get_plant_materials(material_number: str) -> list[dict]:
    """
    Return all (module_component, plant_code) rows for the given material.
    """
    return execute(
        """
        SELECT mkp_component AS module_component,
               plant_code
          FROM CSC.dwd_tb_dim_md_plant_material
         WHERE material_number = :mat
        """,
        mat=material_number,
    )

def get_material_endnumbers(material_number: str) -> list[str]:
    """
    Return all endnumber values for the given material.
    """
    rows = execute(
        """
        SELECT endnumber
          FROM CSC.dwd_tb_dim_md_material
         WHERE material_number = :mat
        """,
        mat=material_number,
    )
    return [r["endnumber"] for r in rows]
