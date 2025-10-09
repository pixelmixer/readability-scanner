"""
Database connection management.
"""

import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure
from typing import Optional

from config import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages MongoDB connection and database operations."""

    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.database: Optional[AsyncIOMotorDatabase] = None
        self._connected = False

    async def connect(self) -> None:
        """Establish connection to MongoDB."""
        try:
            logger.info(f"Connecting to MongoDB: {settings.mongodb_url}")

            self.client = AsyncIOMotorClient(
                settings.mongodb_url,
                serverSelectionTimeoutMS=5000,  # 5 second timeout
                connectTimeoutMS=5000,
                socketTimeoutMS=5000
            )

            # Test the connection
            await self.client.admin.command('ping')

            self.database = self.client[settings.database_name]
            self._connected = True

            # Create text index for article search if it doesn't exist
            await self._ensure_text_index()

            logger.info(f"Successfully connected to database: {settings.database_name}")

        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error connecting to MongoDB: {e}")
            raise

    async def disconnect(self) -> None:
        """Close MongoDB connection."""
        if self.client:
            logger.info("Closing MongoDB connection")
            self.client.close()
            self._connected = False
            self.client = None
            self.database = None

    async def health_check(self) -> bool:
        """Check if database connection is healthy."""
        try:
            if not self._connected or self.client is None:
                return False

            # Ping the database
            await self.client.admin.command('ping')
            return True

        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
            return False

    def get_database(self) -> AsyncIOMotorDatabase:
        """Get the database instance."""
        if not self._connected or self.database is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self.database

    def get_collection(self, collection_name: str):
        """Get a specific collection."""
        database = self.get_database()
        return database[collection_name]

    async def _ensure_text_index(self) -> None:
        """Ensure text index exists for article search."""
        try:
            collection = self.database["documents"]

            # Check if text index already exists
            existing_indexes = await collection.list_indexes().to_list(length=None)
            has_text_index = any(
                index.get("name", "").startswith("title_text_content_text") or
                any(key.startswith("$**") for key in index.get("key", {}))
                for index in existing_indexes
            )

            if not has_text_index:
                logger.info("Creating text index for article search...")
                # Create compound text index on title and content fields
                await collection.create_index([
                    ("title", "text"),
                    ("Cleaned Data", "text"),
                    ("content", "text")
                ])
                logger.info("Text index created successfully")
            else:
                logger.info("Text index already exists")

        except Exception as e:
            logger.warning(f"Failed to create text index: {e}")
            # Don't fail the connection if index creation fails


# Global database manager instance
db_manager = DatabaseManager()


async def get_database() -> AsyncIOMotorDatabase:
    """Dependency to get database instance."""
    return db_manager.get_database()


# Startup and shutdown handlers
async def connect_to_database():
    """Connect to database on startup."""
    await db_manager.connect()


async def close_database_connection():
    """Close database connection on shutdown."""
    await db_manager.disconnect()
