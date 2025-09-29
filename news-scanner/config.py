"""
Configuration management for the News Scanner service.
"""

from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings and configuration."""

    # Application Info
    app_name: str = "News Scanner Service"
    app_version: str = "2.0.0"
    debug: bool = False

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8080

    # Database Configuration
    mongodb_url: str = "mongodb://readability-database:27017"
    database_name: str = "readability-database"

    # Readability Service Configuration
    readability_service_url: str = "http://readability:3000"

    # RSS-Bridge Configuration
    rss_bridge_url: str = "http://rss-bridge:80"

    # Scanning Configuration
    scan_interval: str = Field(default="0 */6 * * *", description="Cron expression for scanning interval")
    max_concurrent_scans: int = 5
    request_delay_ms: int = 100
    request_timeout_seconds: int = 30
    max_retries: int = 2

    # Content Processing
    min_word_count: int = 50
    min_article_count_for_stats: int = 1

    # User Agent Pool for rotation
    user_agents: list = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/119.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
    ]

    # Build Information
    build_timestamp: Optional[str] = None
    build_version: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()

# Initialize build info
from datetime import datetime
settings.build_timestamp = datetime.now().isoformat()
settings.build_version = f"v{settings.app_version}-{int(datetime.now().timestamp())}"
