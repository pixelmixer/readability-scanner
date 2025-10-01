"""
RSS feed parsing functionality.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
import feedparser
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .user_agents import user_agent_rotator
from utils.date_normalizer import normalize_date
from config import settings

logger = logging.getLogger(__name__)


class RSSParser:
    """RSS feed parser with error handling and user agent rotation."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create a requests session with retry strategy."""
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
            backoff_factor=1
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def parse_feed(self, feed_url: str) -> Dict[str, Any]:
        """
        Parse an RSS feed and return structured data.

        Args:
            feed_url: URL of the RSS feed

        Returns:
            Dictionary containing feed metadata and articles
        """
        try:
            self.logger.info(f"Parsing RSS feed: {feed_url}")

            # Validate URL
            parsed_url = urlparse(feed_url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise ValueError(f"Invalid URL format: {feed_url}")

            # Get user agent for this request
            user_agent = user_agent_rotator.get_random_user_agent()
            user_agent_summary = user_agent_rotator.get_user_agent_summary(user_agent)
            self.logger.debug(f"Using User-Agent: {user_agent_summary}")

            # Set user agent in feedparser
            feedparser.USER_AGENT = user_agent

            # Parse the feed
            feed_data = feedparser.parse(feed_url)

            # Check for parsing errors
            if hasattr(feed_data, 'bozo') and feed_data.bozo:
                if hasattr(feed_data, 'bozo_exception'):
                    self.logger.warning(f"Feed parsing warning for {feed_url}: {feed_data.bozo_exception}")
                else:
                    self.logger.warning(f"Feed parsing warning for {feed_url}: Malformed feed")

            # Check if feed was successfully parsed
            if not hasattr(feed_data, 'entries'):
                raise ValueError("Feed parsing failed - no entries found")

            # Extract feed metadata
            feed_info = {
                "title": getattr(feed_data.feed, 'title', 'Unknown Feed'),
                "description": getattr(feed_data.feed, 'description', ''),
                "link": getattr(feed_data.feed, 'link', feed_url),
                "language": getattr(feed_data.feed, 'language', ''),
                "updated": self._parse_feed_date(getattr(feed_data.feed, 'updated', None)),
                "total_articles": len(feed_data.entries)
            }

            # Extract articles
            articles = []
            for entry in feed_data.entries:
                article = self._parse_article_entry(entry, feed_url)
                if article:
                    articles.append(article)

            result = {
                "feed": feed_info,
                "articles": articles,
                "user_agent_used": user_agent_summary
            }

            self.logger.info(f"Successfully parsed feed {feed_url}: {len(articles)} articles found")
            return result

        except Exception as e:
            self.logger.error(f"Error parsing RSS feed {feed_url}: {e}")
            raise

    def _parse_article_entry(self, entry: Any, feed_url: str) -> Optional[Dict[str, Any]]:
        """
        Parse a single RSS entry into article data.

        Args:
            entry: RSS entry from feedparser
            feed_url: Original feed URL for reference

        Returns:
            Dictionary with article data or None if invalid
        """
        try:
            # Extract article URL
            article_url = getattr(entry, 'link', None)
            if not article_url:
                self.logger.warning("RSS entry missing link, skipping")
                return None

            # Extract title
            title = getattr(entry, 'title', 'Untitled Article')

            # Extract publication date - check multiple possible fields
            pub_date = None
            date_fields = [
                'published',      # Atom published
                'updated',        # Atom updated
                'created',        # Generic created
                'pubDate',        # RSS pubDate
                'dc:date',        # Dublin Core date
                'dc:created',     # Dublin Core created
                'dc:modified',    # Dublin Core modified
                'prism:publicationDate',  # PRISM publication date
            ]

            # Debug: Log all available date-related fields
            available_date_fields = [field for field in dir(entry) if any(keyword in field.lower() for keyword in ['date', 'time', 'pub', 'created', 'updated'])]
            if available_date_fields:
                self.logger.debug(f"Available date fields in entry: {available_date_fields}")

            for date_field in date_fields:
                if hasattr(entry, date_field):
                    date_value = getattr(entry, date_field)
                    if date_value:
                        self.logger.debug(f"Trying to parse date from field '{date_field}': {date_value}")
                        pub_date = self._parse_feed_date(date_value)
                        if pub_date:
                            # Normalize to UTC for consistent storage
                            pub_date = normalize_date(pub_date)
                            if pub_date:
                                self.logger.debug(f"Successfully parsed and normalized date from field '{date_field}': {pub_date}")
                                break
                            else:
                                self.logger.debug(f"Failed to normalize date from field '{date_field}': {date_value}")
                        else:
                            self.logger.debug(f"Failed to parse date from field '{date_field}': {date_value}")

            # Extract content/summary
            content = ''
            if hasattr(entry, 'content') and entry.content:
                # Get the first content entry
                content = entry.content[0].value if isinstance(entry.content, list) else str(entry.content)
            elif hasattr(entry, 'summary'):
                content = entry.summary
            elif hasattr(entry, 'description'):
                content = entry.description

            # Extract author
            author = getattr(entry, 'author', '')

            # Extract tags/categories
            tags = []
            if hasattr(entry, 'tags'):
                tags = [tag.term for tag in entry.tags if hasattr(tag, 'term')]

            article = {
                "url": article_url,
                "title": title,
                "content": content,
                "publication_date": pub_date,  # Primary date field for sorting
                "author": author,
                "tags": tags,
                "origin": feed_url
            }

            return article

        except Exception as e:
            self.logger.warning(f"Error parsing RSS entry: {e}")
            return None

    def _parse_feed_date(self, date_string: str) -> Optional[datetime]:
        """
        Parse various date formats from RSS feeds.
        Handles multiple date formats commonly found in RSS/Atom feeds.

        Args:
            date_string: Date string from RSS feed

        Returns:
            Parsed datetime or None if parsing fails
        """
        if not date_string:
            return None

        try:
            # feedparser usually provides a time_struct - this is the most reliable
            if hasattr(date_string, 'time_struct'):
                import time
                return datetime.fromtimestamp(time.mktime(date_string.time_struct))

            # Convert to string for manual parsing
            date_str = str(date_string).strip()

            # Try dateutil parser first (handles most formats)
            from dateutil import parser
            try:
                return parser.parse(date_str)
            except:
                pass

            # Manual parsing for specific formats that dateutil might miss
            import re

            # Handle ISO 8601 formats: 2025-09-30T15:28:22+00:00, 2025-09-30T15:28:22Z
            iso_pattern = r'(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})([+-]\d{2}:\d{2}|Z)?'
            iso_match = re.match(iso_pattern, date_str)
            if iso_match:
                date_part, time_part, tz_part = iso_match.groups()
                if tz_part == 'Z':
                    tz_part = '+00:00'
                elif tz_part is None:
                    tz_part = '+00:00'
                return parser.parse(f"{date_part}T{time_part}{tz_part}")

            # Handle simple date format: 2025-09-30
            simple_date_pattern = r'^\d{4}-\d{2}-\d{2}$'
            if re.match(simple_date_pattern, date_str):
                return parser.parse(f"{date_str}T00:00:00+00:00")

            # Handle RSS pubDate format: Tue, 30 Sep 2025 19:50:52 GMT
            rss_pattern = r'^[A-Za-z]{3},\s+\d{1,2}\s+[A-Za-z]{3}\s+\d{4}\s+\d{2}:\d{2}:\d{2}\s+[A-Za-z]{3,4}$'
            if re.match(rss_pattern, date_str):
                return parser.parse(date_str)

            # Handle formats with timezone offsets: Tue, 30 Sep 2025 16:22:49 -0400
            rss_tz_pattern = r'^[A-Za-z]{3},\s+\d{1,2}\s+[A-Za-z]{3}\s+\d{4}\s+\d{2}:\d{2}:\d{2}\s+[+-]\d{4}$'
            if re.match(rss_tz_pattern, date_str):
                return parser.parse(date_str)

            # Last resort: try dateutil with fuzzy parsing
            return parser.parse(date_str, fuzzy=True)

        except Exception as e:
            self.logger.debug(f"Could not parse date '{date_string}': {e}")
            return None

    def validate_feed_url(self, feed_url: str) -> bool:
        """
        Validate that a URL is actually an RSS feed.

        Args:
            feed_url: URL to validate

        Returns:
            True if valid RSS feed, False otherwise
        """
        try:
            self.logger.info(f"Validating RSS feed: {feed_url}")

            # Basic URL validation
            parsed_url = urlparse(feed_url)
            if not parsed_url.scheme or not parsed_url.netloc:
                return False

            # Check for obvious API endpoints
            url_lower = feed_url.lower()
            if any(indicator in url_lower for indicator in ['/api/', 'json', 'format=json']):
                self.logger.warning(f"URL appears to be an API endpoint, not RSS: {feed_url}")
                return False

            # Try to parse the feed
            feed_data = self.parse_feed(feed_url)

            # Check if we got valid feed data
            if not feed_data.get('articles'):
                self.logger.warning(f"No articles found in feed: {feed_url}")
                return False

            feed_info = feed_data.get('feed', {})
            if not feed_info.get('title'):
                self.logger.warning(f"Feed has no title: {feed_url}")
                return False

            self.logger.info(f"RSS feed validation successful: {feed_info['title']}")
            return True

        except Exception as e:
            self.logger.error(f"RSS feed validation failed for {feed_url}: {e}")
            return False

    def get_feed_title(self, feed_url: str) -> Optional[str]:
        """
        Get the title of an RSS feed.

        Args:
            feed_url: URL of the RSS feed

        Returns:
            Feed title if successful, None otherwise
        """
        try:
            self.logger.info(f"Fetching feed title from: {feed_url}")

            # Fetch with appropriate headers and timeout
            headers = {
                'User-Agent': user_agent_rotator.get_random_user_agent(),
                'Accept': 'application/rss+xml, application/atom+xml, application/xml, text/xml'
            }

            response = self.session.get(feed_url, headers=headers, timeout=30)
            response.raise_for_status()

            # Parse feed
            feed_info = feedparser.parse(response.content)

            if feed_info.bozo and hasattr(feed_info, 'bozo_exception'):
                self.logger.warning(f"Feed parsing warning for {feed_url}: {feed_info.bozo_exception}")

            # Extract title
            title = getattr(feed_info.feed, 'title', None)
            if title:
                return title.strip()
            else:
                return None

        except Exception as e:
            self.logger.error(f"Error fetching feed title for {feed_url}: {e}")
            return None


# Global RSS parser instance
rss_parser = RSSParser()


def parse_feed(feed_url: str) -> Dict[str, Any]:
    """Convenience function for parsing RSS feeds."""
    return rss_parser.parse_feed(feed_url)
