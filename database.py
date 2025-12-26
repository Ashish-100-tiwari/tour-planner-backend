"""
MongoDB database connection and configuration
"""
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure
import os
import logging
import ssl
import certifi
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

logger = logging.getLogger(__name__)

# MongoDB connection settings
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "tourplanner")

# Global database client and database instance
client: AsyncIOMotorClient = None
database = None


def convert_srv_to_standard(connection_string: str) -> str:
    """
    Convert mongodb+srv:// connection string to standard mongodb:// format
    This helps with Windows SSL compatibility issues
    """
    if not connection_string.startswith("mongodb+srv://"):
        return connection_string
    
    # Parse the connection string
    parsed = urlparse(connection_string)
    
    # Extract components
    username = parsed.username
    password = parsed.password
    hostname = parsed.hostname
    path = parsed.path
    query_params = parse_qs(parsed.query)
    
    # For mongodb+srv, we need to use the hostname with port 27017
    # The hostname from SRV is usually the cluster name
    # We'll use the same hostname but with standard mongodb:// protocol
    
    # Build new connection string
    auth = f"{username}:{password}@" if username and password else ""
    new_url = f"mongodb://{auth}{hostname}:27017{path}"
    
    # Preserve query parameters
    if query_params:
        query_string = urlencode(query_params, doseq=True)
        new_url = f"{new_url}?{query_string}"
    
    return new_url


async def connect_to_mongo():
    """Create database connection"""
    global client, database
    try:
        # For MongoDB Atlas, add SSL/TLS configuration
        # This helps with SSL handshake issues on Windows
        connection_kwargs = {}
        
        # If using MongoDB Atlas (mongodb+srv://), add TLS settings
        if MONGODB_URL.startswith("mongodb+srv://") or (MONGODB_URL.startswith("mongodb://") and "mongodb.net" in MONGODB_URL):
            # Try different TLS configurations for Windows compatibility
            # Approach 1: tlsAllowInvalidCertificates (recommended for pymongo 4.x)
            try:
                connection_kwargs = {
                    "tlsAllowInvalidCertificates": True,  # Allows invalid certificates (Windows compatibility)
                    "serverSelectionTimeoutMS": 20000,  # 20 second timeout
                    "connectTimeoutMS": 20000,  # 20 second connection timeout
                }
                logger.info(f"Attempting MongoDB Atlas connection with tlsAllowInvalidCertificates=True")
                client = AsyncIOMotorClient(MONGODB_URL, **connection_kwargs)
                await client.admin.command('ping')
                database = client[DATABASE_NAME]
                logger.info(f"Connected to MongoDB at {MONGODB_URL}")
                logger.info(f"Using database: {DATABASE_NAME}")
                return True
            except Exception as e1:
                logger.warning(f"Connection with tlsAllowInvalidCertificates failed: {e1}")
                # Close the failed client if it was created
                if 'client' in locals() and client is not None:
                    try:
                        client.close()
                    except:
                        pass
                # Approach 2: Use tlsInsecure alone (more permissive - disables all verification)
                try:
                    connection_kwargs = {
                        "tlsInsecure": True,  # Disables certificate and hostname verification
                        "serverSelectionTimeoutMS": 20000,
                        "connectTimeoutMS": 20000,
                    }
                    logger.info(f"Attempting MongoDB Atlas connection with tlsInsecure=True")
                    client = AsyncIOMotorClient(MONGODB_URL, **connection_kwargs)
                    await client.admin.command('ping')
                    database = client[DATABASE_NAME]
                    logger.info(f"Connected to MongoDB at {MONGODB_URL}")
                    logger.info(f"Using database: {DATABASE_NAME}")
                    return True
                except Exception as e2:
                    logger.warning(f"Connection with tlsInsecure failed: {e2}")
                    # Close the failed client if it was created
                    if 'client' in locals() and client is not None:
                        try:
                            client.close()
                        except:
                            pass
                    # Approach 3: Add TLS parameters directly to connection string (Windows workaround)
                    try:
                        # Add TLS parameters to the connection string itself
                        parsed = urlparse(MONGODB_URL)
                        query_params = parse_qs(parsed.query)
                        query_params['tlsAllowInvalidCertificates'] = ['true']
                        new_query = urlencode(query_params, doseq=True)
                        modified_url = urlunparse((
                            parsed.scheme,
                            parsed.netloc,
                            parsed.path,
                            parsed.params,
                            new_query,
                            parsed.fragment
                        ))
                        logger.info(f"Attempting MongoDB Atlas connection with TLS parameters in URL")
                        connection_kwargs = {
                            "serverSelectionTimeoutMS": 20000,
                            "connectTimeoutMS": 20000,
                        }
                        client = AsyncIOMotorClient(modified_url, **connection_kwargs)
                        await client.admin.command('ping')
                        database = client[DATABASE_NAME]
                        logger.info(f"Connected to MongoDB using URL with embedded TLS parameters")
                        logger.info(f"Using database: {DATABASE_NAME}")
                        return True
                    except Exception as e3:
                        logger.warning(f"Connection with TLS in URL failed: {e3}")
                        # Close the failed client if it was created
                        if 'client' in locals() and client is not None:
                            try:
                                client.close()
                            except:
                                pass
                        
                        # Approach 3b: Convert mongodb+srv:// to standard mongodb:// format
                        if MONGODB_URL.startswith("mongodb+srv://"):
                            try:
                                standard_url = convert_srv_to_standard(MONGODB_URL)
                                # Add TLS parameters to converted URL
                                parsed_std = urlparse(standard_url)
                                query_params_std = parse_qs(parsed_std.query)
                                query_params_std['tlsAllowInvalidCertificates'] = ['true']
                                query_params_std['ssl'] = ['true']
                                new_query_std = urlencode(query_params_std, doseq=True)
                                final_url = urlunparse((
                                    parsed_std.scheme,
                                    parsed_std.netloc,
                                    parsed_std.path,
                                    parsed_std.params,
                                    new_query_std,
                                    parsed_std.fragment
                                ))
                                logger.info(f"Attempting MongoDB Atlas connection with converted standard URL (mongodb+srv:// -> mongodb://)")
                                connection_kwargs = {
                                    "serverSelectionTimeoutMS": 20000,
                                    "connectTimeoutMS": 20000,
                                }
                                client = AsyncIOMotorClient(final_url, **connection_kwargs)
                                await client.admin.command('ping')
                                database = client[DATABASE_NAME]
                                logger.info(f"Connected to MongoDB using converted connection string")
                                logger.info(f"Using database: {DATABASE_NAME}")
                                return True
                            except Exception as e3b:
                                logger.warning(f"Connection with converted URL failed: {e3b}")
                                # Close the failed client if it was created
                                if 'client' in locals() and client is not None:
                                    try:
                                        client.close()
                                    except:
                                        pass
                    
                    # Approach 4: Try with certifi certificates explicitly
                    try:
                        connection_kwargs = {
                            "tlsCAFile": certifi.where(),  # Use certifi certificates
                            "serverSelectionTimeoutMS": 20000,
                            "connectTimeoutMS": 20000,
                        }
                        logger.info(f"Attempting MongoDB Atlas connection with certifi certificates")
                        client = AsyncIOMotorClient(MONGODB_URL, **connection_kwargs)
                        await client.admin.command('ping')
                        database = client[DATABASE_NAME]
                        logger.info(f"Connected to MongoDB at {MONGODB_URL}")
                        logger.info(f"Using database: {DATABASE_NAME}")
                        return True
                    except Exception as e4:
                        logger.error(f"All connection attempts failed. Last error: {e4}")
                        # Close the failed client if it was created
                        if 'client' in locals() and client is not None:
                            try:
                                client.close()
                            except:
                                pass
                        raise  # Re-raise to be caught by outer exception handler
        else:
            # Not MongoDB Atlas, use standard connection
            client = AsyncIOMotorClient(MONGODB_URL)
            await client.admin.command('ping')
            database = client[DATABASE_NAME]
            logger.info(f"Connected to MongoDB at {MONGODB_URL}")
            logger.info(f"Using database: {DATABASE_NAME}")
            return True
    except ConnectionFailure as e:
        logger.error(f"Failed to connect to MongoDB (ConnectionFailure): {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error connecting to MongoDB: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False


async def close_mongo_connection():
    """Close database connection"""
    global client
    if client:
        client.close()
        logger.info("Disconnected from MongoDB")


def get_database():
    """Get database instance"""
    return database
