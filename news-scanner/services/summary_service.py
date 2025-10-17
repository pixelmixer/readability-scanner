"""
Summary generation service using LLM provider abstraction.
"""

import logging
import asyncio
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import hashlib

from config import settings
from .llm_providers import LLMProviderManager

logger = logging.getLogger(__name__)


class SummaryService:
    """Service for generating article summaries using LLM provider abstraction."""

    def __init__(self):
        self.provider_manager = LLMProviderManager()
        self.max_retries = 3
        self.retry_delay = 5  # seconds
        self.model = "unknown"  # Default model name for error cases

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
        """Make a request using the LLM provider manager."""
        messages = [
            {
                "role": "system",
                "content": self.prompt_template
            },
            {
                "role": "user",
                "content": content
            }
        ]

        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Making LLM request (attempt {attempt + 1}/{self.max_retries})")

                result = await self.provider_manager.generate_completion(
                    messages=messages,
                    temperature=0.7,
                    max_tokens=-1
                )

                if result:
                    logger.debug("LLM request successful")
                    return result
                else:
                    logger.warning(f"LLM request returned no result (attempt {attempt + 1}/{self.max_retries})")

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
                            "model": llm_response.get("model", "unknown"),
                            "provider": "llm_provider_manager",
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
                            "model": llm_response.get("model", "unknown"),
                            "provider": "llm_provider_manager",
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

    async def generate_combined_summary(self, summaries: list[str], topic_context: str = None) -> Dict[str, Any]:
        """
        Generate a combined summary from multiple article summaries.

        Args:
            summaries: List of individual article summaries
            topic_context: Optional context about the topic grouping

        Returns:
            Dict containing combined summary result and metadata
        """
        try:
            if not summaries:
                return {
                    "success": False,
                    "error": "No summaries provided",
                    "summary": None
                }

            # Prepare combined content
            combined_prompt = """You are a skilled news writer. Using the summaries below as your primary sources, write a cohesive 4-5 sentence news article that tells the complete story. Write in the style of professional journalism - lead with the most newsworthy information, provide context and details, and ensure the piece is readable and informative on its own without requiring readers to consult the original articles. Reference the information naturally as if you're synthesizing multiple reports into one comprehensive story.

Article Summaries (Your Source Material):
"""

            for i, summary in enumerate(summaries, 1):
                combined_prompt += f"\n{i}. {summary}"

            if topic_context:
                combined_prompt += f"\n\nContext: {topic_context}"

            combined_prompt += "\n\nWrite your news synthesis now (4-5 sentences, journalistic style):"

            logger.info(f"Generating combined summary from {len(summaries)} article summaries")

            # Make request to LLM
            llm_response = await self._make_llm_request(combined_prompt)

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
                            "model": llm_response.get("model", "unknown"),
                            "provider": "llm_provider_manager",
                            "prompt_version": self.prompt_version,
                            "generated_at": datetime.utcnow(),
                            "source_summaries_count": len(summaries),
                            "llm_usage": llm_response.get("usage", {}),
                            "llm_response_id": llm_response.get("id")
                        }
                    else:
                        return {
                            "success": False,
                            "error": "Empty summary returned from LLM",
                            "summary": None,
                            "model": llm_response.get("model", "unknown"),
                            "provider": "llm_provider_manager",
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
            logger.error(f"Error in generate_combined_summary: {e}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "summary": None,
                "model": self.model,
                "prompt_version": self.prompt_version,
                "generated_at": datetime.utcnow()
            }

    async def generate_topic_headline(self, summaries: list[str], combined_summary: str = None) -> Dict[str, Any]:
        """
        Generate a short, compelling headline for a topic group.

        Args:
            summaries: List of individual article summaries
            combined_summary: Optional pre-generated combined summary

        Returns:
            Dict with success status and headline
        """
        try:
            if not summaries and not combined_summary:
                return {
                    "success": False,
                    "error": "No content provided for headline generation",
                    "headline": None
                }

            # Prepare prompt
            headline_prompt = """You are a headline writer for a major news publication. Create a short, punchy headline (5-8 words maximum) that captures the main newsworthy angle of this topic. The headline should be clear, engaging, and follow AP style.

IMPORTANT: Return ONLY the headline text with no formatting, no markdown, no "Headline:" prefix, no asterisks, no bold text, and no other formatting characters. Just plain text.

"""

            if combined_summary:
                headline_prompt += f"Topic Summary:\n{combined_summary}\n\n"
            else:
                headline_prompt += "Related Article Summaries:\n"
                for i, summary in enumerate(summaries[:3], 1):  # Use first 3 summaries
                    headline_prompt += f"{i}. {summary}\n"
                headline_prompt += "\n"

            headline_prompt += "Write a headline (5-8 words, AP style, no punctuation at end). Return only the headline text with no formatting:"

            logger.info(f"Generating topic headline")

            # Make request to LLM
            llm_response = await self._make_llm_request(headline_prompt)

            if llm_response is None:
                return {
                    "success": False,
                    "error": "LLM API unavailable after multiple retries",
                    "headline": None
                }

            # Extract headline from response
            try:
                choices = llm_response.get("choices", [])
                if choices and len(choices) > 0:
                    headline = choices[0].get("message", {}).get("content", "").strip()
                    # Remove quotes if LLM added them
                    headline = headline.strip('"\'')

                    # Clean up any markdown formatting that might have been added
                    # Remove markdown bold formatting
                    headline = re.sub(r'\*\*(.*?)\*\*', r'\1', headline)
                    # Remove any "Headline:" prefix
                    headline = re.sub(r'^Headline:\s*', '', headline, flags=re.IGNORECASE)
                    # Remove any other markdown formatting
                    headline = re.sub(r'[*_`]', '', headline)
                    # Clean up extra whitespace
                    headline = ' '.join(headline.split())

                    if headline:
                        return {
                            "success": True,
                            "headline": headline
                        }
                    else:
                        return {
                            "success": False,
                            "error": "Empty headline returned from LLM",
                            "headline": None
                        }
                else:
                    return {
                        "success": False,
                        "error": "No choices in LLM response",
                        "headline": None
                    }

            except Exception as e:
                logger.error(f"Error parsing LLM response for headline: {e}")
                return {
                    "success": False,
                    "error": f"Error parsing LLM response: {str(e)}",
                    "headline": None
                }

        except Exception as e:
            logger.error(f"Error in generate_topic_headline: {e}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "headline": None
            }


# Global service instance
summary_service = SummaryService()

