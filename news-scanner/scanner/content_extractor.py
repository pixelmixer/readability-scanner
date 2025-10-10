"""
Content extraction using the readability service.
"""

import logging
import asyncio
from typing import Dict, Any, Optional
import aiohttp
from aiohttp import ClientTimeout, ClientError

from .user_agents import user_agent_rotator
from config import settings

logger = logging.getLogger(__name__)


class ContentExtractor:
    """Extracts article content using the readability service."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.readability_url = settings.readability_service_url
        self.timeout = ClientTimeout(total=settings.request_timeout_seconds)

    async def extract_content(
        self,
        article_url: str,
        session: aiohttp.ClientSession,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract content from an article URL using the readability service.

        Args:
            article_url: URL of the article to extract
            session: aiohttp session for making requests
            user_agent: Optional user agent to use

        Returns:
            Dictionary containing extracted content and metadata

        Raises:
            ContentExtractionError: If extraction fails
        """
        try:
            # Get user agent if not provided
            if not user_agent:
                user_agent = user_agent_rotator.get_random_user_agent()

            user_agent_summary = user_agent_rotator.get_user_agent_summary(user_agent)
            self.logger.debug(f"Extracting content from {article_url[:80]}... using {user_agent_summary}")

            # Prepare request body
            request_body = {
                "url": article_url,
                "headers": {
                    "User-Agent": user_agent
                }
            }

            # Make request to readability service
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "NewsAnalysis-Scanner/2.0"
            }

            async with session.post(
                self.readability_url,
                json=request_body,
                headers=headers,
                timeout=self.timeout
            ) as response:

                # Log response details
                self.logger.debug(f"Readability service response: {response.status} for {article_url}")

                # Handle HTTP errors
                if not response.ok:
                    error_text = ""
                    try:
                        error_text = await response.text()
                    except Exception:
                        pass

                    error_info = {
                        "status": response.status,
                        "url": article_url,
                        "error_text": error_text[:500] if error_text else "",
                        "user_agent": user_agent_summary
                    }

                    # Analyze error patterns for better diagnostics
                    self._analyze_error_response(response.status, error_text, article_url)

                    raise ContentExtractionError(
                        f"HTTP {response.status}: {response.reason}",
                        status_code=response.status,
                        details=error_info
                    )

                # Parse JSON response
                try:
                    content_data = await response.json()
                except Exception as e:
                    raise ContentExtractionError(f"Invalid JSON response: {e}")

                # Validate response contains content
                if not content_data.get('content'):
                    self.logger.warning(f"No content extracted from {article_url}")
                    raise ContentExtractionError("No content extracted", status_code=204)

                # Extract primary image URL
                image_url = self._extract_primary_image(content_data, article_url)
                if image_url:
                    content_data['image_url'] = image_url
                    self.logger.debug(f"Extracted primary image: {image_url}")

                # Add metadata
                content_data['extraction_user_agent'] = user_agent_summary
                content_data['extraction_timestamp'] = asyncio.get_event_loop().time()

                self.logger.debug(f"Successfully extracted content from {article_url}")
                return content_data

        except ContentExtractionError:
            # Re-raise our custom errors
            raise
        except asyncio.TimeoutError:
            raise ContentExtractionError(f"Request timeout for {article_url}", status_code=408)
        except ClientError as e:
            raise ContentExtractionError(f"Client error: {e}", status_code=500)
        except Exception as e:
            self.logger.error(f"Unexpected error extracting content from {article_url}: {e}")
            raise ContentExtractionError(f"Unexpected error: {e}")

    def _extract_primary_image(self, content_data: Dict[str, Any], article_url: str) -> Optional[str]:
        """
        Extract the primary image URL from readability response data.

        Args:
            content_data: Response data from readability service
            article_url: Original article URL for relative URL resolution

        Returns:
            Primary image URL or None if no suitable image found
        """
        try:
            # Check for lead_image_url (common in readability responses)
            if content_data.get('lead_image_url'):
                return content_data['lead_image_url']

            # Check for image in meta data
            if content_data.get('meta', {}).get('image'):
                return content_data['meta']['image']

            # Check for og:image in meta data
            if content_data.get('meta', {}).get('og', {}).get('image'):
                return content_data['meta']['og']['image']

            # Look for images in the content HTML
            content = content_data.get('content', '')
            if content:
                # Simple regex to find first img src
                import re
                img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>', content, re.IGNORECASE)
                if img_match:
                    img_url = img_match.group(1)
                    # Convert relative URLs to absolute
                    if img_url.startswith('/'):
                        from urllib.parse import urljoin
                        img_url = urljoin(article_url, img_url)
                    elif not img_url.startswith(('http://', 'https://')):
                        img_url = urljoin(article_url, img_url)

                    # Basic validation - ensure it's a reasonable image URL
                    if self._is_valid_image_url(img_url):
                        return img_url

            return None

        except Exception as e:
            self.logger.warning(f"Error extracting primary image from {article_url}: {e}")
            return None

    def _is_valid_image_url(self, url: str) -> bool:
        """
        Basic validation for image URLs.

        Args:
            url: Image URL to validate

        Returns:
            True if URL appears to be a valid image URL
        """
        if not url or not isinstance(url, str):
            return False

        # Check for common image extensions
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']
        url_lower = url.lower()

        # Check file extension
        if any(url_lower.endswith(ext) for ext in image_extensions):
            return True

        # Check for image hosting domains or paths
        if any(domain in url_lower for domain in ['imgur.com', 'cloudinary.com', 'unsplash.com']):
            return True

        # Check for common image URL patterns
        if '/image/' in url_lower or '/img/' in url_lower or '/photo/' in url_lower:
            return True

        return False

    def _analyze_error_response(self, status_code: int, response_text: str, url: str) -> None:
        """Analyze error responses to provide diagnostic information."""
        try:
            lower_response = response_text.lower() if response_text else ""

            if status_code == 403 or status_code == 401:
                if any(pattern in lower_response for pattern in ['blocked', 'forbidden', 'access denied']):
                    self.logger.warning(f"🚫 ACCESS BLOCKED detected for {url}")
                if any(pattern in lower_response for pattern in ['robot', 'bot']):
                    self.logger.warning(f"🤖 BOT DETECTION detected for {url}")
                if any(pattern in lower_response for pattern in ['captcha', 'verify']):
                    self.logger.warning(f"🔐 CAPTCHA/VERIFICATION required for {url}")

            elif status_code == 429:
                if any(pattern in lower_response for pattern in ['rate limit', 'too many requests']):
                    self.logger.warning(f"🚫 RATE LIMITING detected for {url}")

            elif status_code >= 500:
                self.logger.warning(f"💥 SERVER ERROR ({status_code}) for {url}")

            # Check for protection services
            if any(pattern in lower_response for pattern in ['cloudflare', 'ddos protection']):
                self.logger.warning(f"☁️ CLOUDFLARE/DDOS PROTECTION detected for {url}")

        except Exception as e:
            self.logger.debug(f"Error analyzing response: {e}")


class ContentExtractionError(Exception):
    """Custom exception for content extraction errors."""

    def __init__(self, message: str, status_code: int = None, details: Dict[str, Any] = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}


# Global content extractor instance
content_extractor = ContentExtractor()


async def extract_article_content(
    article_url: str,
    session: aiohttp.ClientSession,
    user_agent: Optional[str] = None
) -> Dict[str, Any]:
    """Convenience function for extracting article content."""
    return await content_extractor.extract_content(article_url, session, user_agent)
