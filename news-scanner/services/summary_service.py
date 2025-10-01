"""
Summary generation service using external LLM API.
"""

import logging
import aiohttp
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import hashlib

from config import settings

logger = logging.getLogger(__name__)


class SummaryService:
    """Service for generating article summaries using external LLM API."""

    def __init__(self):
        self.llm_api_url = "http://192.168.86.32:1234/v1/chat/completions"
        self.model = "openai/gpt-oss-20b"
        self.timeout = 90  # seconds - increased to handle LLM API delays
        self.max_retries = 3
        self.retry_delay = 5  # seconds

        # Load prompt from file
        self.prompt_template = self._load_prompt_template()
        self.prompt_version = self._get_prompt_version()

    def _load_prompt_template(self) -> str:
        """Load the prompt template from file."""
        try:
            prompt_file = Path(__file__).parent.parent / "prompts" / "summary_prompt.txt"
            if prompt_file.exists():
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    logger.info(f"Loaded prompt template from {prompt_file}")
                    return content
            else:
                logger.warning(f"Prompt file not found at {prompt_file}, using default")
                return self._get_default_prompt()
        except Exception as e:
            logger.error(f"Error loading prompt template: {e}")
            return self._get_default_prompt()

    def _get_default_prompt(self) -> str:
        """Get default prompt if file loading fails."""
        return """You are an expert news analyst. Create a concise 2-3 sentence summary of the following article that captures the key facts and main points. Be objective and factual.

Article:"""

    def _get_prompt_version(self) -> str:
        """Generate a version hash for the current prompt."""
        try:
            return hashlib.md5(self.prompt_template.encode()).hexdigest()[:8]
        except Exception:
            return "unknown"

    async def _make_llm_request(self, content: str) -> Optional[Dict[str, Any]]:
        """Make a request to the LLM API."""
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": self.prompt_template
                },
                {
                    "role": "user",
                    "content": content
                }
            ],
            "temperature": 0.7,
            "max_tokens": -1,
            "stream": False
        }

        headers = {
            "Content-Type": "application/json"
        }

        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Making LLM request (attempt {attempt + 1}/{self.max_retries})")

                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                    async with session.post(self.llm_api_url, json=payload, headers=headers) as response:
                        if response.status == 200:
                            result = await response.json()
                            logger.debug("LLM request successful")
                            return result
                        else:
                            logger.warning(f"LLM API returned status {response.status}: {await response.text()}")

            except asyncio.TimeoutError:
                logger.warning(f"LLM request timeout (attempt {attempt + 1}/{self.max_retries})")
            except aiohttp.ClientError as e:
                logger.warning(f"LLM request client error (attempt {attempt + 1}/{self.max_retries}): {e}")
            except Exception as e:
                logger.error(f"Unexpected error in LLM request (attempt {attempt + 1}/{self.max_retries}): {e}")

            # Wait before retry
            if attempt < self.max_retries - 1:
                logger.info(f"Retrying LLM request in {self.retry_delay} seconds...")
                await asyncio.sleep(self.retry_delay)

        logger.error("All LLM request attempts failed")
        return None

    async def generate_summary(self, article_content: str, article_title: str = None) -> Dict[str, Any]:
        """
        Generate a summary for the given article content.

        Args:
            article_content: The main content of the article
            article_title: Optional article title for context

        Returns:
            Dict containing summary result and metadata
        """
        try:
            # Prepare content for LLM
            content_parts = []
            if article_title:
                content_parts.append(f"Title: {article_title}")
            content_parts.append(f"Content: {article_content}")

            full_content = "\n\n".join(content_parts)

            # Send full content without truncation - let the LLM API handle any limits
            logger.info(f"Sending full article content to LLM ({len(full_content)} characters)")

            # Make request to LLM
            llm_response = await self._make_llm_request(full_content)

            if llm_response is None:
                return {
                    "success": False,
                    "error": "LLM API unavailable after multiple retries",
                    "summary": None,
                    "model": self.model,
                    "prompt_version": self.prompt_version,
                    "generated_at": datetime.utcnow()
                }

            # Extract summary from response
            try:
                choices = llm_response.get("choices", [])
                if choices and len(choices) > 0:
                    summary = choices[0].get("message", {}).get("content", "").strip()

                    if summary:
                        return {
                            "success": True,
                            "summary": summary,
                            "model": self.model,
                            "prompt_version": self.prompt_version,
                            "generated_at": datetime.utcnow(),
                            "llm_usage": llm_response.get("usage", {}),
                            "llm_response_id": llm_response.get("id")
                        }
                    else:
                        return {
                            "success": False,
                            "error": "Empty summary returned from LLM",
                            "summary": None,
                            "model": self.model,
                            "prompt_version": self.prompt_version,
                            "generated_at": datetime.utcnow()
                        }
                else:
                    return {
                        "success": False,
                        "error": "No choices in LLM response",
                        "summary": None,
                        "model": self.model,
                        "prompt_version": self.prompt_version,
                        "generated_at": datetime.utcnow()
                    }

            except Exception as e:
                logger.error(f"Error parsing LLM response: {e}")
                return {
                    "success": False,
                    "error": f"Error parsing LLM response: {str(e)}",
                    "summary": None,
                    "model": self.model,
                    "prompt_version": self.prompt_version,
                    "generated_at": datetime.utcnow()
                }

        except Exception as e:
            logger.error(f"Error in generate_summary: {e}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "summary": None,
                "model": self.model,
                "prompt_version": self.prompt_version,
                "generated_at": datetime.utcnow()
            }

    async def test_connection(self) -> bool:
        """Test if the LLM API is accessible."""
        try:
            test_result = await self.generate_summary("This is a test article for connection testing.")
            return test_result["success"]
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False


# Global service instance
summary_service = SummaryService()

