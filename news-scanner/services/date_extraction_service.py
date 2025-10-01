"""
Service for extracting publication dates from article content and metadata.
"""

import logging
import re
from datetime import datetime
from typing import Optional, Dict, Any
from dateutil import parser
import requests
from bs4 import BeautifulSoup
from utils.date_normalizer import normalize_date

logger = logging.getLogger(__name__)


class DateExtractionService:
    """Service for extracting publication dates from various sources."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    async def extract_publication_date(self, article_data: Dict[str, Any]) -> Optional[datetime]:
        """
        Extract publication date from article data using multiple strategies.

        Args:
            article_data: Article data dictionary

        Returns:
            Parsed datetime or None if not found
        """
        url = article_data.get('url', '')
        content = article_data.get('content', '')
        cleaned_data = article_data.get('cleaned_data', '')

        # Strategy 1: Check if we already have a publication date
        if article_data.get('publication_date'):
            parsed_date = self._parse_date_string(str(article_data['publication_date']))
            if parsed_date:
                return normalize_date(parsed_date)
            return None

        # Strategy 2: Extract from HTML content using meta tags
        if content:
            date_from_content = self._extract_date_from_html(content)
            if date_from_content:
                normalized_date = normalize_date(date_from_content)
                if normalized_date:
                    logger.debug(f"Found date in HTML content (normalized): {normalized_date}")
                    return normalized_date

        # Strategy 3: Extract from cleaned text content
        if cleaned_data:
            date_from_text = self._extract_date_from_text(cleaned_data)
            if date_from_text:
                normalized_date = normalize_date(date_from_text)
                if normalized_date:
                    logger.debug(f"Found date in cleaned text (normalized): {normalized_date}")
                    return normalized_date

        # Strategy 4: Try to fetch the article page and extract date
        if url:
            try:
                date_from_page = await self._extract_date_from_url(url)
                if date_from_page:
                    normalized_date = normalize_date(date_from_page)
                    if normalized_date:
                        logger.debug(f"Found date from article page (normalized): {normalized_date}")
                        return normalized_date
            except Exception as e:
                logger.debug(f"Failed to extract date from URL {url}: {e}")

        return None

    def _extract_date_from_html(self, html_content: str) -> Optional[datetime]:
        """Extract publication date from HTML content using meta tags."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Common meta tag patterns for publication dates
            meta_selectors = [
                'meta[property="article:published_time"]',
                'meta[name="article:published_time"]',
                'meta[property="og:published_time"]',
                'meta[name="pubdate"]',
                'meta[name="publication_date"]',
                'meta[name="date"]',
                'meta[property="datePublished"]',
                'meta[name="DC.date.issued"]',
                'meta[name="DC.date.created"]',
                'meta[name="sailthru.date"]',
                'meta[name="parsely-pub-date"]',
                'meta[name="publish_date"]',
                'meta[name="article:published"]',
                'meta[property="article:published"]',
                'time[datetime]',
                'time[pubdate]'
            ]

            for selector in meta_selectors:
                elements = soup.select(selector)
                for element in elements:
                    # Get content from content attribute or datetime attribute
                    date_value = element.get('content') or element.get('datetime')
                    if date_value:
                        parsed_date = self._parse_date_string(date_value)
                        if parsed_date:
                            return parsed_date

            # Look for JSON-LD structured data
            json_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_scripts:
                try:
                    import json
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        date_value = self._extract_date_from_json_ld(data)
                        if date_value:
                            return date_value
                except:
                    continue

            return None

        except Exception as e:
            logger.debug(f"Error extracting date from HTML: {e}")
            return None

    def _extract_date_from_text(self, text_content: str) -> Optional[datetime]:
        """Extract publication date from plain text content."""
        try:
            # Common date patterns in text
            date_patterns = [
                # ISO formats
                r'\b(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2})\b',
                r'\b(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\b',
                r'\b(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\b',
                # Date only
                r'\b(\d{4}-\d{2}-\d{2})\b',
                # Common formats
                r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
                r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+\d{1,2},?\s+\d{4}\b',
                r'\b\d{1,2}\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b',
                r'\b\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+\d{4}\b',
                # RSS format
                r'\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s+\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+\d{4}\s+\d{2}:\d{2}:\d{2}\s+[A-Z]{3,4}\b',
            ]

            for pattern in date_patterns:
                matches = re.findall(pattern, text_content, re.IGNORECASE)
                for match in matches:
                    parsed_date = self._parse_date_string(match)
                    if parsed_date:
                        return parsed_date

            return None

        except Exception as e:
            logger.debug(f"Error extracting date from text: {e}")
            return None

    async def _extract_date_from_url(self, url: str) -> Optional[datetime]:
        """Extract publication date by fetching the article page."""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            # Extract from HTML
            date_from_html = self._extract_date_from_html(response.text)
            if date_from_html:
                return date_from_html

            # Extract from text content
            soup = BeautifulSoup(response.text, 'html.parser')
            text_content = soup.get_text()
            return self._extract_date_from_text(text_content)

        except Exception as e:
            logger.debug(f"Error fetching date from URL {url}: {e}")
            return None

    def _extract_date_from_json_ld(self, data: Dict[str, Any]) -> Optional[datetime]:
        """Extract date from JSON-LD structured data."""
        try:
            # Check for common date fields in JSON-LD
            date_fields = [
                'datePublished',
                'dateCreated',
                'dateModified',
                'publishedTime',
                'createdTime',
                'modifiedTime',
                'publishDate',
                'publicationDate'
            ]

            for field in date_fields:
                if field in data:
                    parsed_date = self._parse_date_string(str(data[field]))
                    if parsed_date:
                        return parsed_date

            # Check nested objects
            if 'article' in data and isinstance(data['article'], dict):
                return self._extract_date_from_json_ld(data['article'])

            if 'newsArticle' in data and isinstance(data['newsArticle'], dict):
                return self._extract_date_from_json_ld(data['newsArticle'])

            return None

        except Exception as e:
            logger.debug(f"Error extracting date from JSON-LD: {e}")
            return None

    def _parse_date_string(self, date_string: str) -> Optional[datetime]:
        """Parse a date string using multiple strategies."""
        if not date_string:
            return None

        try:
            # Clean the date string
            date_str = str(date_string).strip()

            # Try dateutil parser first
            try:
                return parser.parse(date_str)
            except:
                pass

            # Manual parsing for specific formats
            import re

            # Handle ISO 8601 formats
            iso_pattern = r'(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})([+-]\d{2}:\d{2}|Z)?'
            iso_match = re.match(iso_pattern, date_str)
            if iso_match:
                date_part, time_part, tz_part = iso_match.groups()
                if tz_part == 'Z':
                    tz_part = '+00:00'
                elif tz_part is None:
                    tz_part = '+00:00'
                return parser.parse(f"{date_part}T{time_part}{tz_part}")

            # Handle simple date format
            simple_date_pattern = r'^\d{4}-\d{2}-\d{2}$'
            if re.match(simple_date_pattern, date_str):
                return parser.parse(f"{date_str}T00:00:00+00:00")

            # Handle RSS pubDate format
            rss_pattern = r'^[A-Za-z]{3},?\s+\d{1,2}\s+[A-Za-z]{3}\s+\d{4}\s+\d{2}:\d{2}:\d{2}\s+[A-Za-z]{3,4}$'
            if re.match(rss_pattern, date_str):
                return parser.parse(date_str)

            # Handle formats with timezone offsets
            rss_tz_pattern = r'^[A-Za-z]{3},?\s+\d{1,2}\s+[A-Za-z]{3}\s+\d{4}\s+\d{2}:\d{2}:\d{2}\s+[+-]\d{4}$'
            if re.match(rss_tz_pattern, date_str):
                return parser.parse(date_str)

            # Last resort: try dateutil with fuzzy parsing
            return parser.parse(date_str, fuzzy=True)

        except Exception as e:
            logger.debug(f"Could not parse date '{date_string}': {e}")
            return None


# Global instance
date_extraction_service = DateExtractionService()
