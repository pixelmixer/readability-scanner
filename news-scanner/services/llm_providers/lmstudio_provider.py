"""
LM Studio provider for local LLM inference.
"""

import logging
import aiohttp
import asyncio
from typing import List, Dict, Any, Optional

from .base_provider import BaseLLMProvider
from config import settings

logger = logging.getLogger(__name__)


class LMStudioProvider(BaseLLMProvider):
    """Provider for local LM Studio instance."""

    def __init__(self):
        self.api_url = settings.lmstudio_api_url
        self.model = settings.lmstudio_model
        self.timeout = 5  # Short timeout for availability checks
        self.request_timeout = 90  # Longer timeout for actual requests

    async def is_available(self) -> bool:
        """Check if LM Studio is available."""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                # Try to get models endpoint to check if LM Studio is running
                async with session.get(f"{self.api_url.replace('/v1/chat/completions', '/v1/models')}") as response:
                    return response.status == 200
        except Exception as e:
            logger.debug(f"LM Studio availability check failed: {e}")
            return False

    async def generate_completion(self, messages: List[Dict[str, str]], **kwargs) -> Optional[Dict[str, Any]]:
        """
        Generate completion using LM Studio.

        Args:
            messages: List of message dictionaries
            **kwargs: Additional parameters

        Returns:
            Completion result or None if failed
        """
        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": kwargs.get("temperature", 0.7),
                "max_tokens": kwargs.get("max_tokens", -1),
                "stream": False
            }

            headers = {
                "Content-Type": "application/json"
            }

            logger.debug(f"Making LM Studio request to {self.api_url}")

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.request_timeout)) as session:
                async with session.post(self.api_url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.debug("LM Studio request successful")
                        return result
                    else:
                        logger.warning(f"LM Studio returned status {response.status}: {await response.text()}")
                        return None

        except asyncio.TimeoutError:
            logger.warning("LM Studio request timeout")
            return None
        except aiohttp.ClientError as e:
            logger.warning(f"LM Studio request client error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in LM Studio request: {e}")
            return None

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "LM Studio"
