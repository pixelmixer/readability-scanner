"""
Base abstract class for LLM providers.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate_completion(self, messages: List[Dict[str, str]], **kwargs) -> Optional[Dict[str, Any]]:
        """
        Generate a completion using the LLM provider.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            Dictionary containing the completion result or None if failed
        """
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """
        Check if the LLM provider is available and ready to use.

        Returns:
            True if available, False otherwise
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Get the name of this provider.

        Returns:
            Provider name string
        """
        pass
