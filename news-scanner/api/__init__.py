"""
FastAPI web application and routes.
"""

from .app import create_app, app
from .routes import sources, daily, graph, export, scan
from .dependencies import get_database, get_templates

__all__ = [
    "create_app",
    "app",
    "sources",
    "daily",
    "graph",
    "export",
    "scan",
    "get_database",
    "get_templates"
]
