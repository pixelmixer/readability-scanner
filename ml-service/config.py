"""
Configuration for ML Service.
"""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """ML Service configuration."""

    # Service settings
    service_name: str = "ml-service"
    host: str = "0.0.0.0"
    port: int = 8081

    # Database settings
    mongodb_url: str = "mongodb://readability-database:27017"
    database_name: str = "readability-database"

    # ML Model settings
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384

    # Similarity settings
    default_similarity_threshold: float = 0.7
    default_max_similar_articles: int = 10

    # Topic analysis settings
    default_topic_similarity_threshold: float = 0.75
    default_min_group_size: int = 2

    # Performance settings
    max_batch_size: int = 100
    max_content_length: int = 2000

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()

