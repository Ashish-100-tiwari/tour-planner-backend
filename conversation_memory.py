"""
Conversation memory management for short-term chat history
Stores user conversations in MongoDB with 30-minute TTL auto-expiration
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from database import get_database
import logging
import os

logger = logging.getLogger(__name__)

# Configuration from environment variables
CONVERSATION_TTL_MINUTES = int(os.getenv("CONVERSATION_TTL_MINUTES", "30"))
CONVERSATION_HISTORY_LIMIT = int(os.getenv("CONVERSATION_HISTORY_LIMIT", "10"))


async def setup_conversation_indexes():
    """
    Set up MongoDB indexes for conversation history
    Creates a TTL index that auto-deletes documents after 30 minutes
    """
    db = get_database()
    if db is None:
        logger.warning("Database not available, skipping conversation index setup")
        return False
    
    try:
        # Create TTL index on created_at field (expires after 30 minutes)
        await db.conversation_history.create_index(
            "created_at",
            expireAfterSeconds=CONVERSATION_TTL_MINUTES * 60
        )
        
        # Create index on user_email for faster queries
        await db.conversation_history.create_index("user_email")
        
        # Create compound index for efficient queries
        await db.conversation_history.create_index([
            ("user_email", 1),
            ("timestamp", -1)
        ])
        
        logger.info(f"Conversation history indexes created (TTL: {CONVERSATION_TTL_MINUTES} minutes)")
        return True
    except Exception as e:
        logger.error(f"Error setting up conversation indexes: {e}")
        return False


async def store_message(user_email: str, role: str, content: str) -> bool:
    """
    Store a conversation message in MongoDB
    
    Args:
        user_email: User's email address (identifier)
        role: Message role ('user' or 'assistant')
        content: Message content
    
    Returns:
        True if successful, False otherwise
    """
    db = get_database()
    if db is None:
        logger.warning("Database not available, cannot store message")
        return False
    
    try:
        message_doc = {
            "user_email": user_email.lower(),
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow(),
            "created_at": datetime.utcnow()  # TTL index field
        }
        
        await db.conversation_history.insert_one(message_doc)
        logger.debug(f"Stored {role} message for {user_email}")
        return True
    except Exception as e:
        logger.error(f"Error storing message: {e}")
        return False


async def get_conversation_history(
    user_email: str,
    limit: int = CONVERSATION_HISTORY_LIMIT
) -> List[Dict[str, str]]:
    """
    Retrieve conversation history for a user
    
    Args:
        user_email: User's email address
        limit: Maximum number of messages to retrieve (default: 10)
    
    Returns:
        List of message dictionaries with 'role' and 'content' keys
        Sorted chronologically (oldest first)
    """
    db = get_database()
    if db is None:
        logger.warning("Database not available, returning empty history")
        return []
    
    try:
        # Query messages for this user, sorted by timestamp descending
        cursor = db.conversation_history.find(
            {"user_email": user_email.lower()},
            {"role": 1, "content": 1, "timestamp": 1, "_id": 0}
        ).sort("timestamp", -1).limit(limit)
        
        messages = await cursor.to_list(length=limit)
        
        # Reverse to get chronological order (oldest first)
        messages.reverse()
        
        logger.debug(f"Retrieved {len(messages)} messages for {user_email}")
        return messages
    except Exception as e:
        logger.error(f"Error retrieving conversation history: {e}")
        return []


async def clear_conversation_history(user_email: str) -> bool:
    """
    Manually clear conversation history for a user
    
    Args:
        user_email: User's email address
    
    Returns:
        True if successful, False otherwise
    """
    db = get_database()
    if db is None:
        logger.warning("Database not available, cannot clear history")
        return False
    
    try:
        result = await db.conversation_history.delete_many(
            {"user_email": user_email.lower()}
        )
        logger.info(f"Cleared {result.deleted_count} messages for {user_email}")
        return True
    except Exception as e:
        logger.error(f"Error clearing conversation history: {e}")
        return False


async def get_conversation_stats(user_email: str) -> Dict:
    """
    Get statistics about a user's conversation history
    
    Args:
        user_email: User's email address
    
    Returns:
        Dictionary with message count and oldest message timestamp
    """
    db = get_database()
    if db is None:
        return {"message_count": 0, "oldest_message": None}
    
    try:
        count = await db.conversation_history.count_documents(
            {"user_email": user_email.lower()}
        )
        
        oldest = await db.conversation_history.find_one(
            {"user_email": user_email.lower()},
            sort=[("timestamp", 1)]
        )
        
        return {
            "message_count": count,
            "oldest_message": oldest.get("timestamp") if oldest else None
        }
    except Exception as e:
        logger.error(f"Error getting conversation stats: {e}")
        return {"message_count": 0, "oldest_message": None}
