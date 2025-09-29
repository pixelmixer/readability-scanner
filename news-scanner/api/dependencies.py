"""
FastAPI dependencies for database, templates, and other shared resources.
"""

import logging
from fastapi import Depends, HTTPException
from fastapi.templating import Jinja2Templates
from motor.motor_asyncio import AsyncIOMotorDatabase

from database.connection import get_database as get_db_connection
from config import settings

logger = logging.getLogger(__name__)

# Initialize Jinja2 templates
templates = Jinja2Templates(directory="templates")


async def get_database() -> AsyncIOMotorDatabase:
    """
    Dependency to get database connection.

    Raises HTTPException if database is not available.
    """
    try:
        return await get_db_connection()
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="Database service unavailable"
        )


def get_templates() -> Jinja2Templates:
    """Dependency to get template engine."""
    return templates


def get_settings():
    """Dependency to get application settings."""
    return settings
