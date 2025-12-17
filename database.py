"""
MongoDB database connection and configuration
"""
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure
import os
import logging

logger = logging.getLogger(__name__)

# MongoDB connection settings
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "tourplanner")

# Global database client and database instance
client: AsyncIOMotorClient = None
database = None


async def connect_to_mongo():
    """Create database connection"""
    global client, database
    try:
        client = AsyncIOMotorClient(MONGODB_URL)
        # Test the connection
        await client.admin.command('ping')
        database = client[DATABASE_NAME]
        logger.info(f"Connected to MongoDB at {MONGODB_URL}")
        logger.info(f"Using database: {DATABASE_NAME}")
        return True
    except ConnectionFailure as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error connecting to MongoDB: {e}")
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
