"""
RSS source data models.
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Any
from datetime import datetime
from bson import ObjectId


class SourceBase(BaseModel):
    """Base source model with common fields."""

    url: HttpUrl = Field(..., description="RSS feed URL")
    name: Optional[str] = Field(None, description="Human-readable source name")
    description: Optional[str] = Field(None, description="Source description")


class SourceCreate(SourceBase):
    """Model for creating a new RSS source."""
    pass


class SourceUpdate(BaseModel):
    """Model for updating an existing RSS source."""

    url: Optional[HttpUrl] = None
    name: Optional[str] = None
    description: Optional[str] = None


class Source(SourceBase):
    """Complete RSS source model with metadata."""

    id: Optional[str] = Field(None, alias="_id", description="MongoDB ObjectId")
    date_added: Optional[datetime] = Field(None, alias="dateAdded", description="When the source was added")
    last_modified: Optional[datetime] = Field(None, alias="lastModified", description="Last modification date")
    last_refreshed: Optional[datetime] = Field(None, alias="lastRefreshed", description="Last scan/refresh date")

    # Computed fields (not stored in DB, calculated on-the-fly)
    article_count: Optional[int] = Field(None, description="Number of articles from this source")
    last_fetched: Optional[datetime] = Field(None, description="Date of most recent article")

    @classmethod
    def from_mongo(cls, doc: dict):
        """Create Source instance from MongoDB document."""
        if doc is None:
            return None

        # Convert ObjectId to string
        if "_id" in doc and doc["_id"]:
            doc["_id"] = str(doc["_id"])

        return cls(**doc)

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "url": "https://example.com/rss",
                "name": "Example News",
                "description": "A sample news source",
                "date_added": "2024-01-01T12:00:00Z",
                "last_modified": "2024-01-01T12:00:00Z",
                "last_refreshed": "2024-01-01T13:00:00Z",
                "article_count": 150,
                "last_fetched": "2024-01-01T13:00:00Z"
            }
        }
