"""
Database operations for the News Scanner service.
"""

from .connection import DatabaseManager, get_database
from .articles import ArticleRepository
from .sources import SourceRepository

__all__ = [
    "DatabaseManager",
    "get_database",
    "ArticleRepository",
    "SourceRepository"
]
