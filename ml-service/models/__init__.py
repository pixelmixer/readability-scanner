"""
Data models for the News Scanner service.
"""

from .article import Article, ArticleCreate, ArticleUpdate
from .source import Source, SourceCreate, SourceUpdate
from .readability import ReadabilityMetrics
from .scan_result import ScanResult, ScanStats

__all__ = [
    "Article",
    "ArticleCreate",
    "ArticleUpdate",
    "Source",
    "SourceCreate",
    "SourceUpdate",
    "ReadabilityMetrics",
    "ScanResult",
    "ScanStats"
]
