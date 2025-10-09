"""
Summary generation service stub for ML service.
This is a minimal implementation to support topic service functionality.
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class SummaryService:
    """Stub service for generating article summaries."""

    def __init__(self):
        logger.info("SummaryService initialized (stub implementation)")

    async def generate_summary(self, content: str) -> Optional[str]:
        """
        Generate a summary for the given content.

        Args:
            content: The content to summarize

        Returns:
            A summary string or None if generation fails
        """
        logger.warning("SummaryService.generate_summary called - stub implementation")

        # For now, return a simple truncated version
        if content and len(content) > 200:
            return content[:200] + "..."
        return content
