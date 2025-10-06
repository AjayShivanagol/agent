import os
import pyodbc
from dotenv import load_dotenv
from azure.identity import ClientSecretCredential
from azure.core.exceptions import ClientAuthenticationError
from app.logger.logger_config import setup_logger
logger= setup_logger("CONFIG")

# Load environment variables from .env file
logger.info("Loading Env variables")
load_dotenv()
logger.info("Env variables loaded Successfully")

# Database configuration - using Service Principal authentication
DB_CONFIG = {
    "server": os.getenv("AZURE_SQL_SERVER"),
    "database": os.getenv("AZURE_SQL_DATABASE"),
    "tenant_id": os.getenv("AZURE_TENANT_ID"),
    "client_id": os.getenv("AZURE_CLIENT_ID"),
    "client_secret": os.getenv("AZURE_CLIENT_SECRET"),
    "sp_name": os.getenv("AZURE_SP_NAME"),
}

def get_db_connection():
    """Establish and return a database connection using Service Principal authentication."""
    try:
        # Get Service Principal credentials from environment
        tenant_id = os.getenv('AZURE_TENANT_ID')
        client_id = os.getenv('AZURE_CLIENT_ID')
        client_secret = os.getenv('AZURE_CLIENT_SECRET')
        server = os.getenv('AZURE_SQL_SERVER')
        database = os.getenv('AZURE_SQL_DATABASE')
        logger.info("Loading all DB connection variables")
        # Validate required environment variables
        if not all([tenant_id, client_id, client_secret, server, database]):
            missing = []
            if not tenant_id: missing.append("AZURE_TENANT_ID")
            if not client_id: missing.append("AZURE_CLIENT_ID") 
            if not client_secret: missing.append("AZURE_CLIENT_SECRET")
            if not server: missing.append("AZURE_SQL_SERVER")
            if not database: missing.append("AZURE_SQL_DATABASE")
            logger.info(f"❌ Missing required environment variables: {', '.join(missing)}")
            return None
        
        logger.info(f"🔄 Connecting to Azure SQL: {server}/{database}")
        logger.info(f"🔐 Using Service Principal authentication with client_id: {client_id[:8]}...")
        
        logger.info("Creating Secret credentials")
        # Create Service Principal credential
        credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret
        )
        logger.info("Accessing tokens for Azure SQL")
        # Get access token for Azure SQL Database
        token = credential.get_token("https://database.windows.net/.default")
        access_token = token.token
        
        # Encode token properly for ODBC driver
        import struct
        token_bytes = access_token.encode('utf-16le')
        token_struct = struct.pack('<I', len(token_bytes)) + token_bytes
        
        # Connection string for Azure SQL with Service Principal authentication
        conn_str = (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};"
            f"SERVER=tcp:{server},1433;"
            f"DATABASE={database};"
            f"Encrypt=yes;"
            f"TrustServerCertificate=no;"
            f"Connection Timeout=30;"
            f"Login Timeout=30;"
        )
        logger.info("Connecting to Principlal Tokens")
        # Connect using Service Principal token
        connection = pyodbc.connect(
            conn_str,
            attrs_before={1256: token_struct}  # SQL_COPT_SS_ACCESS_TOKEN = 1256
        )
        logger.info("✅ Azure SQL connection successful with Service Principal!")
        return connection
        
    except ClientAuthenticationError as e:
        logger.error(f"❌ Service Principal authentication failed: {e}")
        logger.info("💡 Please verify your tenant_id, client_id, and client_secret are correct")
        return None
    except pyodbc.Error as e:
        logger.error(f"❌ Azure SQL connection failed: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return None
