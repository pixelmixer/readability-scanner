"""
LLM Provider Manager with fallback logic.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional

from .base_provider import BaseLLMProvider
from .lmstudio_provider import LMStudioProvider
from .gemini_provider import GeminiProvider
from config import settings

logger = logging.getLogger(__name__)


class LLMProviderManager:
    """Manager for LLM providers with automatic fallback."""

    def __init__(self):
        self.local_provider = LMStudioProvider()
        self.remote_provider = GeminiProvider()
        self.fallback_enabled = settings.llm_fallback_enabled

    async def generate_completion(self, messages: List[Dict[str, str]], **kwargs) -> Optional[Dict[str, Any]]:
        """
        Generate completion with automatic fallback and retry logic.

        Args:
            messages: List of message dictionaries
            **kwargs: Additional parameters

        Returns:
            Completion result or None if all providers fail
        """
        max_retries = 3
        retry_delay = 5  # seconds

        for attempt in range(max_retries):
            logger.debug(f"LLM request attempt {attempt + 1}/{max_retries}")

            # Try local provider first
            if await self.local_provider.is_available():
                logger.info(f"Using {self.local_provider.get_provider_name()} for LLM request")
                result = await self.local_provider.generate_completion(messages, **kwargs)
                if result:
                    return result
                else:
                    logger.warning(f"{self.local_provider.get_provider_name()} returned no result")
            else:
                logger.info(f"{self.local_provider.get_provider_name()} is not available")

            # Fallback to remote provider if enabled
            if self.fallback_enabled:
                if await self.remote_provider.is_available():
                    logger.info(f"Falling back to {self.remote_provider.get_provider_name()} for LLM request")
                    result = await self.remote_provider.generate_completion(messages, **kwargs)
                    if result:
                        return result
                    else:
                        logger.warning(f"{self.remote_provider.get_provider_name()} returned no result")
                else:
                    logger.warning(f"{self.remote_provider.get_provider_name()} is not available")
            else:
                logger.info("Fallback to remote provider is disabled")

            # If we get here, both providers failed
            if attempt < max_retries - 1:
                logger.info(f"All providers failed, retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff

        logger.error("All LLM providers failed or are unavailable after all retries")
        return None

    async def is_any_available(self) -> bool:
        """Check if any provider is available."""
        local_available = await self.local_provider.is_available()
        remote_available = await self.remote_provider.is_available()

        return local_available or (self.fallback_enabled and remote_available)

    def get_available_providers(self) -> List[str]:
        """Get list of available provider names."""
        providers = []
        if self.local_provider:
            providers.append(self.local_provider.get_provider_name())
        if self.remote_provider:
            providers.append(self.remote_provider.get_provider_name())
        return providers

    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get rate limiting status from all providers."""
        status = {
            "local_provider": {},
            "remote_provider": {},
            "fallback_enabled": self.fallback_enabled
        }

        # Get local provider status
        if hasattr(self.local_provider, 'get_rate_limit_status'):
            status["local_provider"] = self.local_provider.get_rate_limit_status()

        # Get remote provider status
        if hasattr(self.remote_provider, 'get_rate_limit_status'):
            status["remote_provider"] = self.remote_provider.get_rate_limit_status()

        return status

    def reset_rate_limits(self):
        """Reset rate limiting state for all providers."""
        if hasattr(self.local_provider, 'reset_rate_limits'):
            self.local_provider.reset_rate_limits()
        if hasattr(self.remote_provider, 'reset_rate_limits'):
            self.remote_provider.reset_rate_limits()
        logger.info("Rate limits reset for all providers")
