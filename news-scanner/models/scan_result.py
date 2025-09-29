"""
Scan result data models.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class ScanStats(BaseModel):
    """Statistics for a scanning operation."""

    total: int = Field(..., description="Total number of articles found")
    scanned: int = Field(..., description="Number of articles successfully processed")
    failed: int = Field(..., description="Number of articles that failed to process")

    # Failure breakdown
    http_500: int = Field(0, description="HTTP 5xx server errors")
    http_403: int = Field(0, description="HTTP 403/401 access denied errors")
    http_429: int = Field(0, description="HTTP 429 rate limiting errors")
    timeout: int = Field(0, description="Request timeout errors")
    no_content: int = Field(0, description="Articles with no extractable content")
    other: int = Field(0, description="Other types of errors")

    @property
    def success_rate(self) -> float:
        """Calculate success rate as a percentage."""
        if self.total == 0:
            return 0.0
        return (self.scanned / self.total) * 100

    @property
    def failure_rate(self) -> float:
        """Calculate failure rate as a percentage."""
        return 100.0 - self.success_rate


class ScanResult(BaseModel):
    """Result of scanning an RSS source."""

    source_url: str = Field(..., description="URL of the RSS source that was scanned")
    source_name: Optional[str] = Field(None, description="Name of the RSS source")
    start_time: datetime = Field(..., description="When the scan started")
    end_time: Optional[datetime] = Field(None, description="When the scan completed")
    duration_seconds: Optional[float] = Field(None, description="Scan duration in seconds")

    stats: ScanStats = Field(..., description="Scan statistics")

    error: Optional[str] = Field(None, description="Error message if scan failed")
    warnings: list[str] = Field(default_factory=list, description="Warning messages from the scan")

    # Diagnostic information
    user_agent_used: Optional[str] = Field(None, description="User agent string used for requests")
    diagnosis: Optional[str] = Field(None, description="Automated diagnosis of scan issues")

    @property
    def success(self) -> bool:
        """Whether the scan was successful overall."""
        return self.error is None and self.stats.total > 0

    @property
    def has_high_failure_rate(self) -> bool:
        """Whether the scan had a high failure rate (>75%)."""
        return self.stats.failure_rate > 75

    def add_warning(self, message: str):
        """Add a warning message to the result."""
        self.warnings.append(message)

    def finalize(self, end_time: Optional[datetime] = None):
        """Finalize the scan result with end time and duration."""
        if end_time is None:
            end_time = datetime.now()

        self.end_time = end_time
        self.duration_seconds = (end_time - self.start_time).total_seconds()

        # Generate diagnosis
        self._generate_diagnosis()

    def _generate_diagnosis(self):
        """Generate automated diagnosis based on failure patterns."""
        if self.stats.failed == 0:
            self.diagnosis = "All articles processed successfully"
            return

        failure_rate = self.stats.failure_rate
        total_failed = self.stats.failed

        diagnoses = []

        if self.stats.http_403 > total_failed * 0.5:
            diagnoses.append("High number of 403 errors suggests bot detection. Consider user-agent rotation.")

        if self.stats.http_429 > total_failed * 0.3:
            diagnoses.append("Rate limiting detected. Consider slower request timing.")

        if self.stats.http_500 > total_failed * 0.7:
            diagnoses.append("High server errors. Readability service may be struggling with this site's content.")

        if self.stats.no_content > total_failed * 0.8:
            diagnoses.append("High 'no content' rate suggests redirect URLs or paywall protection.")
            if "google" in self.source_url.lower():
                diagnoses.append("Google News feeds often contain redirect URLs that don't extract well. Consider direct publisher feeds.")

        if failure_rate > 75:
            diagnoses.append("High failure rate suggests anti-bot protection or content structure issues.")

        self.diagnosis = " ".join(diagnoses) if diagnoses else "Mixed failure types detected."

    class Config:
        json_schema_extra = {
            "example": {
                "source_url": "https://example.com/rss",
                "source_name": "Example News",
                "start_time": "2024-01-01T12:00:00Z",
                "end_time": "2024-01-01T12:05:00Z",
                "duration_seconds": 300.0,
                "stats": {
                    "total": 20,
                    "scanned": 18,
                    "failed": 2,
                    "http_500": 1,
                    "http_403": 1,
                    "http_429": 0,
                    "timeout": 0,
                    "no_content": 0,
                    "other": 0
                },
                "error": None,
                "warnings": ["Some articles failed to process"],
                "user_agent_used": "Mozilla/5.0...",
                "diagnosis": "Mixed failure types detected."
            }
        }
