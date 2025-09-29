"""
Main article scanning orchestrator.
"""

import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
import aiohttp

from models.scan_result import ScanResult, ScanStats
from readability.analyzer import analyzer
from database.articles import article_repository
from .rss_parser import rss_parser
from .content_extractor import content_extractor, ContentExtractionError
from .user_agents import user_agent_rotator
from config import settings

logger = logging.getLogger(__name__)


class ArticleScanner:
    """Main article scanner that orchestrates the scanning process."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.max_concurrent = settings.max_concurrent_scans
        self.request_delay = settings.request_delay_ms / 1000.0  # Convert to seconds
        self.max_retries = settings.max_retries

    async def scan_source(self, source_url: str, source_name: str = None) -> ScanResult:
        """
        Scan a single RSS source and process all articles.

        Args:
            source_url: URL of the RSS feed
            source_name: Optional name for the source

        Returns:
            ScanResult with detailed scanning statistics
        """
        start_time = datetime.now()
        scan_result = ScanResult(
            source_url=source_url,
            source_name=source_name or urlparse(source_url).hostname,
            start_time=start_time,
            stats=ScanStats(total=0, scanned=0, failed=0)
        )

        try:
            self.logger.info(f"🔍 Starting scan of source: {scan_result.source_name} ({source_url})")

            # Validate URL format
            try:
                urlparse(source_url)
            except Exception:
                scan_result.error = "Invalid URL format"
                scan_result.finalize()
                return scan_result

            # Parse RSS feed
            try:
                feed_data = rss_parser.parse_feed(source_url)
                articles = feed_data.get('articles', [])
                scan_result.user_agent_used = feed_data.get('user_agent_used')
            except Exception as e:
                self.logger.error(f"Failed to parse RSS feed {source_url}: {e}")
                scan_result.error = f"RSS parsing failed: {e}"
                scan_result.finalize()
                return scan_result

            if not articles:
                self.logger.info(f"No articles found in feed: {source_url}")
                scan_result.stats.total = 0
                scan_result.finalize()
                return scan_result

            scan_result.stats.total = len(articles)
            self.logger.info(f"Found {len(articles)} articles in {source_url}")

            # Process articles with concurrency control
            async with aiohttp.ClientSession() as session:
                results = await self._process_articles_concurrently(
                    articles, session, scan_result
                )

                # Update statistics based on results
                self._update_scan_statistics(results, scan_result)

            # Generate diagnosis and warnings
            self._generate_scan_insights(scan_result)

            scan_result.finalize()

            # Log results
            success_rate = scan_result.stats.success_rate
            self.logger.info(
                f"✅ Scan completed for {scan_result.source_name}: "
                f"{scan_result.stats.scanned}/{scan_result.stats.total} articles "
                f"({success_rate:.1f}% success rate)"
            )

            return scan_result

        except Exception as e:
            self.logger.error(f"Unexpected error scanning {source_url}: {e}")
            scan_result.error = f"Unexpected error: {e}"
            scan_result.finalize()
            return scan_result

    async def _process_articles_concurrently(
        self,
        articles: List[Dict[str, Any]],
        session: aiohttp.ClientSession,
        scan_result: ScanResult
    ) -> List[Dict[str, Any]]:
        """Process articles with controlled concurrency."""

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrent)

        # Create tasks for all articles
        tasks = []
        for index, article in enumerate(articles):
            task = self._process_single_article(
                article, session, index, len(articles), semaphore, scan_result
            )
            tasks.append(task)

        # Execute all tasks and wait for completion
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and return successful results
        successful_results = []
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"Task failed with exception: {result}")
            elif result is not None:
                successful_results.append(result)

        return successful_results

    async def _process_single_article(
        self,
        article: Dict[str, Any],
        session: aiohttp.ClientSession,
        index: int,
        total: int,
        semaphore: asyncio.Semaphore,
        scan_result: ScanResult
    ) -> Optional[Dict[str, Any]]:
        """Process a single article with retry logic."""

        async with semaphore:  # Limit concurrent requests

            article_url = article.get('url')
            if not article_url:
                self.logger.warning("Article missing URL, skipping")
                return None

            # Add delay to avoid overwhelming servers
            if index > 0:
                delay = self.request_delay * (index // 5)  # Increased delay every 5 articles
                await asyncio.sleep(delay)

            # Retry logic
            for attempt in range(self.max_retries + 1):
                try:
                    self.logger.debug(f"📄 Processing article {index + 1}/{total}: {article_url[:80]}...")

                    # Get user agent for this request
                    user_agent = user_agent_rotator.get_random_user_agent()

                    # Extract content
                    content_data = await content_extractor.extract_content(
                        article_url, session, user_agent
                    )

                    if not content_data.get('content'):
                        scan_result.stats.no_content += 1
                        return None

                    # Enhance with article metadata
                    content_data.update({
                        'title': article.get('title', ''),
                        'publication date': article.get('publication_date'),
                        'origin': scan_result.source_url,
                        'Host': urlparse(article_url).hostname
                    })

                    # Perform readability analysis
                    await self._analyze_and_save_article(content_data)

                    self.logger.debug(f"✅ Successfully processed: {article_url}")
                    return content_data

                except ContentExtractionError as e:
                    self._record_extraction_error(e, scan_result)

                    # Retry on server errors
                    if e.status_code and e.status_code >= 500 and attempt < self.max_retries:
                        retry_delay = 2 ** attempt  # Exponential backoff
                        self.logger.warning(
                            f"🔄 Retrying HTTP {e.status_code} for {article_url} "
                            f"(attempt {attempt + 1}/{self.max_retries + 1}) in {retry_delay}s"
                        )
                        await asyncio.sleep(retry_delay)
                        continue

                    # Don't retry on other errors
                    break

                except Exception as e:
                    self.logger.error(f"💥 Unexpected error processing {article_url}: {e}")
                    scan_result.stats.other += 1

                    # Retry on unexpected errors
                    if attempt < self.max_retries:
                        await asyncio.sleep(1)
                        continue
                    break

            return None

    def _record_extraction_error(self, error: ContentExtractionError, scan_result: ScanResult):
        """Record extraction error in scan statistics."""
        status_code = error.status_code

        if status_code == 429:
            scan_result.stats.http_429 += 1
        elif status_code in [401, 403]:
            scan_result.stats.http_403 += 1
        elif status_code and status_code >= 500:
            scan_result.stats.http_500 += 1
        elif status_code == 408:
            scan_result.stats.timeout += 1
        elif status_code == 204:
            scan_result.stats.no_content += 1
        else:
            scan_result.stats.other += 1

    async def _analyze_and_save_article(self, content_data: Dict[str, Any]) -> bool:
        """Analyze article content and save to database."""
        try:
            # Perform readability analysis
            readability_metrics = analyzer.analyze_and_convert_to_dict(
                content_data['content'],
                is_html=True
            )

            # Merge readability data with content data
            content_data.update(readability_metrics)

            # Clean the content for storage
            cleaned_content = analyzer.clean_html_content(content_data['content'])
            content_data['Cleaned Data'] = cleaned_content

            # Add analysis timestamp
            content_data['date'] = datetime.now()

            # Save to database
            success = await article_repository.upsert_article(content_data)
            return success

        except Exception as e:
            self.logger.error(f"Error analyzing/saving article: {e}")
            return False

    def _update_scan_statistics(self, results: List[Dict[str, Any]], scan_result: ScanResult):
        """Update scan statistics based on processing results."""
        scan_result.stats.scanned = len(results)
        scan_result.stats.failed = scan_result.stats.total - scan_result.stats.scanned

    def _generate_scan_insights(self, scan_result: ScanResult):
        """Generate diagnostic insights for the scan."""
        stats = scan_result.stats

        if stats.failed == 0:
            return

        # Add warnings based on failure patterns
        if stats.http_403 > stats.failed * 0.5:
            scan_result.add_warning(
                "High number of 403 errors suggests bot detection. Consider user-agent rotation."
            )

        if stats.http_429 > stats.failed * 0.3:
            scan_result.add_warning(
                "Rate limiting detected. Consider slower request timing."
            )

        if stats.http_500 > stats.failed * 0.7:
            scan_result.add_warning(
                "High server errors. Readability service may be struggling with this site's content."
            )

        if stats.no_content > stats.failed * 0.8:
            scan_result.add_warning(
                "High 'no content' rate suggests redirect URLs or paywall protection."
            )

            if "google" in scan_result.source_url.lower():
                scan_result.add_warning(
                    "Google News feeds often contain redirect URLs. Consider direct publisher feeds."
                )

        if stats.failure_rate > 75:
            scan_result.add_warning(
                "High failure rate suggests anti-bot protection or content structure issues."
            )


# Global scanner instance
article_scanner = ArticleScanner()


async def scan_single_source(source_url: str, source_name: str = None) -> ScanResult:
    """Convenience function for scanning a single source."""
    return await article_scanner.scan_source(source_url, source_name)
