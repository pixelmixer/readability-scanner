"""
Article data models.
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from datetime import datetime
from .readability import ReadabilityMetrics


class ArticleBase(BaseModel):
    """Base article model with common fields."""

    url: HttpUrl = Field(..., description="Article URL")
    title: Optional[str] = Field(None, description="Article title")
    content: Optional[str] = Field(None, description="Extracted article content")
    cleaned_data: Optional[str] = Field(None, alias="Cleaned Data", description="Cleaned text content for analysis")
    host: Optional[str] = Field(None, alias="Host", description="Hostname of the article")
    origin: Optional[str] = Field(None, description="RSS feed origin URL")
    publication_date: Optional[datetime] = Field(None, alias="publication date", description="Article publication date")


class ArticleCreate(ArticleBase):
    """Model for creating a new article."""
    pass


class ArticleUpdate(BaseModel):
    """Model for updating an existing article."""

    title: Optional[str] = None
    content: Optional[str] = None
    cleaned_data: Optional[str] = None
    publication_date: Optional[datetime] = None


class Article(ArticleBase):
    """Complete article model with readability metrics."""

    # Readability metrics (flattened from ReadabilityMetrics for MongoDB compatibility)
    words: Optional[int] = None
    sentences: Optional[int] = None
    paragraphs: Optional[int] = None
    characters: Optional[int] = None
    syllables: Optional[int] = None
    word_syllables: Optional[float] = Field(None, alias="word syllables")
    complex_polysillabic_words: Optional[int] = Field(None, alias="complex polysillabic words")

    # Readability scores
    flesch: Optional[float] = Field(None, alias="Flesch")
    flesch_kincaid: Optional[float] = Field(None, alias="Flesch Kincaid")
    smog: Optional[float] = Field(None, alias="Smog")
    dale_chall: Optional[float] = Field(None, alias="Dale Chall")
    dale_chall_grade: Optional[str] = Field(None, alias="Dale Chall: Grade")
    coleman_liau: Optional[float] = Field(None, alias="Coleman Liau")
    gunning_fog: Optional[float] = Field(None, alias="Gunning Fog")
    spache: Optional[float] = Field(None, alias="Spache")
    automated_readability: Optional[float] = Field(None, alias="Automated Readability")

    # Metadata
    date: Optional[datetime] = Field(None, description="Analysis date")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "url": "https://example.com/article",
                "title": "Sample News Article",
                "content": "<p>This is the article content...</p>",
                "cleaned_data": "This is the article content...",
                "host": "example.com",
                "origin": "https://example.com/rss",
                "publication_date": "2024-01-01T12:00:00Z",
                "words": 250,
                "sentences": 15,
                "paragraphs": 5,
                "characters": 1200,
                "syllables": 350,
                "word_syllables": 1.4,
                "complex_polysillabic_words": 12,
                "flesch": 65.2,
                "flesch_kincaid": 8.5,
                "smog": 9.2,
                "dale_chall": 7.8,
                "coleman_liau": 8.9,
                "gunning_fog": 9.1,
                "spache": 6.5,
                "automated_readability": 8.7,
                "date": "2024-01-01T12:05:00Z"
            }
        }
