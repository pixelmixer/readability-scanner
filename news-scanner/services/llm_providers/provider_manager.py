"""
LLM Provider Manager with fallback logic.
"""

import logging
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
        Generate completion with automatic fallback.

        Args:
            messages: List of message dictionaries
            **kwargs: Additional parameters

        Returns:
            Completion result or None if all providers fail
        """
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

        logger.error("All LLM providers failed or are unavailable")
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
