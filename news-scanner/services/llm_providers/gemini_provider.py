"""
Google Gemini provider for remote LLM inference.
"""

import logging
import aiohttp
import asyncio
from typing import List, Dict, Any, Optional

from .base_provider import BaseLLMProvider
from config import settings

logger = logging.getLogger(__name__)


class GeminiProvider(BaseLLMProvider):
    """Provider for Google Gemini API."""

    def __init__(self):
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent"
        self.api_key = settings.google_gemini_api_key
        self.model = settings.gemini_model
        self.timeout = 10  # Timeout for availability checks
        self.request_timeout = 90  # Timeout for actual requests

    async def is_available(self) -> bool:
        """Check if Gemini API is available."""
        if not self.api_key:
            logger.debug("Gemini API key not configured")
            return False

        try:
            # Simple test request to check API availability
            test_payload = {
                "contents": [{
                    "parts": [{"text": "test"}]
                }]
            }

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(
                    f"{self.api_url}?key={self.api_key}",
                    json=test_payload
                ) as response:
                    return response.status in [200, 400]  # 400 might be due to test content, but API is available
        except Exception as e:
            logger.debug(f"Gemini availability check failed: {e}")
            return False

    def _transform_messages_to_gemini(self, messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Transform OpenAI format messages to Gemini format."""
        contents = []
        current_content = {"parts": []}

        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")

            if role == "system":
                # Gemini doesn't have system messages, prepend to first user message
                if contents and contents[0].get("role") == "user":
                    # Add system content to first user message
                    first_part = contents[0]["parts"][0]
                    first_part["text"] = f"System: {content}\n\n{first_part['text']}"
                else:
                    # Store for later if no user message yet
                    current_content["parts"].append({"text": f"System: {content}"})
            elif role == "user":
                if current_content["parts"]:
                    contents.append({"role": "user", "parts": current_content["parts"]})
                current_content = {"parts": [{"text": content}]}
            elif role == "assistant":
                if current_content["parts"]:
                    contents.append({"role": "user", "parts": current_content["parts"]})
                contents.append({"role": "model", "parts": [{"text": content}]})
                current_content = {"parts": []}

        # Add any remaining content
        if current_content["parts"]:
            contents.append({"role": "user", "parts": current_content["parts"]})

        return contents

    def _transform_gemini_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Gemini response to OpenAI format."""
        try:
            candidates = response.get("candidates", [])
            if not candidates:
                return {"choices": []}

            candidate = candidates[0]
            content = candidate.get("content", {})
            parts = content.get("parts", [])

            if not parts:
                return {"choices": []}

            # Extract text from first part
            text = parts[0].get("text", "")

            # Transform to OpenAI format
            return {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": text
                    },
                    "finish_reason": candidate.get("finishReason", "stop")
                }],
                "usage": response.get("usageMetadata", {}),
                "model": self.model
            }
        except Exception as e:
            logger.error(f"Error transforming Gemini response: {e}")
            return {"choices": []}

    async def generate_completion(self, messages: List[Dict[str, str]], **kwargs) -> Optional[Dict[str, Any]]:
        """
        Generate completion using Gemini API.

        Args:
            messages: List of message dictionaries
            **kwargs: Additional parameters

        Returns:
            Completion result in OpenAI format or None if failed
        """
        if not self.api_key:
            logger.error("Gemini API key not configured")
            return None

        try:
            # Transform messages to Gemini format
            contents = self._transform_messages_to_gemini(messages)

            payload = {
                "contents": contents,
                "generationConfig": {
                    "temperature": kwargs.get("temperature", 0.7),
                    "maxOutputTokens": kwargs.get("max_tokens", 2048) if kwargs.get("max_tokens", -1) > 0 else 2048
                }
            }

            logger.debug(f"Making Gemini request to {self.api_url}")

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.request_timeout)) as session:
                async with session.post(
                    f"{self.api_url}?key={self.api_key}",
                    json=payload
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.debug("Gemini request successful")
                        return self._transform_gemini_response(result)
                    else:
                        error_text = await response.text()
                        logger.warning(f"Gemini returned status {response.status}: {error_text}")
                        return None

        except asyncio.TimeoutError:
            logger.warning("Gemini request timeout")
            return None
        except aiohttp.ClientError as e:
            logger.warning(f"Gemini request client error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in Gemini request: {e}")
            return None

    def get_provider_name(self) -> str:
        """Get provider name."""
        return f"Gemini ({self.model})"
