"""
Google Gemini provider for remote LLM inference.
"""

import logging
import aiohttp
import asyncio
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

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

        # Rate limiting state
        self.rate_limit_reset_time = None
        self.quota_limit = None
        self.quota_used = 0
        self.last_request_time = None
        self.min_request_interval = 1.0  # Minimum seconds between requests

    async def is_available(self) -> bool:
        """Check if Gemini API is available."""
        if not self.api_key:
            logger.debug("Gemini API key not configured")
            return False

        # Check if we're currently rate limited
        if self._is_rate_limited():
            logger.debug("Gemini API is rate limited")
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
                    if response.status == 429:
                        # Parse rate limit info
                        try:
                            error_data = await response.json()
                            quota_info = self._parse_rate_limit_error(error_data)
                            if quota_info:
                                self._update_rate_limit_state(quota_info)
                        except Exception:
                            pass
                        return False

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

    def _parse_rate_limit_error(self, error_response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse rate limit error response to extract quota and retry information."""
        try:
            error = error_response.get("error", {})
            if error.get("code") != 429:
                return None

            # Extract quota information
            quota_info = {
                "retry_after": None,
                "quota_limit": None,
                "quota_used": None,
                "reset_time": None
            }

            # Look for retry delay in details
            details = error.get("details", [])
            for detail in details:
                if detail.get("@type") == "type.googleapis.com/google.rpc.RetryInfo":
                    retry_info = detail.get("retryDelay", "0s")
                    # Parse retry delay (format: "46s" or "46.831699407s")
                    if retry_info.endswith("s"):
                        try:
                            quota_info["retry_after"] = float(retry_info[:-1])
                        except ValueError:
                            pass

                elif detail.get("@type") == "type.googleapis.com/google.rpc.QuotaFailure":
                    violations = detail.get("violations", [])
                    for violation in violations:
                        quota_value = violation.get("quotaValue")
                        if quota_value:
                            try:
                                quota_info["quota_limit"] = int(quota_value)
                            except ValueError:
                                pass

            # Extract quota used from error message if available
            message = error.get("message", "")
            if "limit:" in message:
                try:
                    # Extract limit from message like "limit: 200"
                    limit_part = message.split("limit:")[-1].strip().split()[0]
                    quota_info["quota_limit"] = int(limit_part)
                except (ValueError, IndexError):
                    pass

            return quota_info

        except Exception as e:
            logger.warning(f"Error parsing rate limit response: {e}")
            return None

    def _update_rate_limit_state(self, quota_info: Dict[str, Any]):
        """Update internal rate limiting state based on API response."""
        if quota_info.get("quota_limit"):
            self.quota_limit = quota_info["quota_limit"]
            logger.info(f"Updated Gemini quota limit: {self.quota_limit}")

        if quota_info.get("retry_after"):
            self.rate_limit_reset_time = datetime.utcnow() + timedelta(seconds=quota_info["retry_after"])
            logger.info(f"Rate limit will reset at: {self.rate_limit_reset_time}")

        # Increment usage counter
        self.quota_used += 1

    def _is_rate_limited(self) -> bool:
        """Check if we're currently rate limited."""
        if self.rate_limit_reset_time and datetime.utcnow() < self.rate_limit_reset_time:
            return True

        # Check if we're approaching quota limit
        if self.quota_limit and self.quota_used >= self.quota_limit * 0.9:  # 90% threshold
            logger.warning(f"Approaching quota limit: {self.quota_used}/{self.quota_limit}")
            return True

        return False

    async def _wait_for_rate_limit(self):
        """Wait for rate limit to reset."""
        if self.rate_limit_reset_time:
            wait_time = (self.rate_limit_reset_time - datetime.utcnow()).total_seconds()
            if wait_time > 0:
                logger.info(f"Waiting {wait_time:.1f} seconds for rate limit reset...")
                await asyncio.sleep(wait_time)
                self.rate_limit_reset_time = None

    async def _enforce_request_interval(self):
        """Enforce minimum interval between requests."""
        if self.last_request_time:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.min_request_interval:
                wait_time = self.min_request_interval - elapsed
                logger.debug(f"Enforcing request interval: waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)

        self.last_request_time = time.time()

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
        Generate completion using Gemini API with rate limiting.

        Args:
            messages: List of message dictionaries
            **kwargs: Additional parameters

        Returns:
            Completion result in OpenAI format or None if failed
        """
        if not self.api_key:
            logger.error("Gemini API key not configured")
            return None

        # Check if we're rate limited before making request
        if self._is_rate_limited():
            logger.warning("Gemini API is rate limited, waiting for reset...")
            await self._wait_for_rate_limit()

        # Enforce minimum interval between requests
        await self._enforce_request_interval()

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
                        self._update_rate_limit_state({"quota_limit": None, "retry_after": None})  # Increment usage
                        return self._transform_gemini_response(result)
                    elif response.status == 429:
                        # Handle rate limiting
                        try:
                            error_data = await response.json()
                            quota_info = self._parse_rate_limit_error(error_data)
                            if quota_info:
                                self._update_rate_limit_state(quota_info)
                                logger.warning(f"Gemini rate limited: {quota_info}")

                                # If we have retry info, we could retry after the delay
                                if quota_info.get("retry_after"):
                                    logger.info(f"Rate limit will reset in {quota_info['retry_after']} seconds")
                            else:
                                logger.warning("Gemini rate limited but couldn't parse retry info")
                        except Exception as e:
                            logger.warning(f"Error parsing rate limit response: {e}")

                        return None
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

    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limiting status for monitoring."""
        status = {
            "is_rate_limited": self._is_rate_limited(),
            "quota_limit": self.quota_limit,
            "quota_used": self.quota_used,
            "rate_limit_reset_time": self.rate_limit_reset_time.isoformat() if self.rate_limit_reset_time else None,
            "min_request_interval": self.min_request_interval
        }

        if self.quota_limit and self.quota_used > 0:
            status["quota_usage_percent"] = (self.quota_used / self.quota_limit) * 100

        return status

    def reset_rate_limits(self):
        """Reset rate limiting state (useful for testing or manual intervention)."""
        self.rate_limit_reset_time = None
        self.quota_used = 0
        logger.info("Rate limits reset manually")
