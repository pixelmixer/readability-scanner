#!/usr/bin/env python3
"""
Script to fix articles with erroneous future publication dates.

This script identifies articles with publication dates in the future and provides
options to either:
1. Set them to the analysis_date (when the article was processed)
2. Set them to a reasonable past date based on the analysis_date
3. Delete them entirely

Usage:
    python fix_future_dates.py --dry-run  # Preview changes
    python fix_future_dates.py --fix     # Apply fixes
    python fix_future_dates.py --delete  # Delete future-dated articles
"""

import asyncio
import argparse
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
import sys
import os

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import db_manager
from database.articles import article_repository
from utils.date_normalizer import normalize_date

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FutureDateFixer:
    """Handles fixing articles with future publication dates."""

    def __init__(self):
        self.future_articles = []
        self.stats = {
            'total_future': 0,
            'by_source': {},
            'by_date': {},
            'fixed': 0,
            'deleted': 0,
            'errors': 0
        }

    async def find_future_articles(self) -> List[Dict[str, Any]]:
        """Find all articles with publication dates in the future."""
        try:
            await db_manager.connect()

            # Get current time in UTC
            now = datetime.now(timezone.utc)

            # Query for articles with future publication dates
            future_articles = await article_repository.get_articles_with_future_dates(now)

            self.future_articles = future_articles
            self.stats['total_future'] = len(future_articles)

            # Analyze by source
            for article in future_articles:
                origin = article.get('origin', 'Unknown')
                if origin not in self.stats['by_source']:
                    self.stats['by_source'][origin] = 0
                self.stats['by_source'][origin] += 1

                # Analyze by date
                pub_date = article.get('publication_date')
                if pub_date:
                    date_str = pub_date.strftime('%Y-%m-%d')
                    if date_str not in self.stats['by_date']:
                        self.stats['by_date'][date_str] = 0
                    self.stats['by_date'][date_str] += 1

            logger.info(f"Found {len(future_articles)} articles with future publication dates")
            return future_articles

        except Exception as e:
            logger.error(f"Error finding future articles: {e}")
            return []

    def print_analysis(self):
        """Print analysis of future-dated articles."""
        print("\n" + "="*60)
        print("FUTURE DATE ANALYSIS")
        print("="*60)
        print(f"Total articles with future dates: {self.stats['total_future']}")

        print("\nBy RSS Source:")
        for source, count in sorted(self.stats['by_source'].items(), key=lambda x: x[1], reverse=True):
            print(f"  {source}: {count} articles")

        print("\nBy Publication Date:")
        for date, count in sorted(self.stats['by_date'].items()):
            print(f"  {date}: {count} articles")

        print("\nSample articles:")
        for i, article in enumerate(self.future_articles[:5]):
            pub_date = article.get('publication_date', 'Unknown')
            analysis_date = article.get('analysis_date') or article.get('date', 'Unknown')
            print(f"  {i+1}. {article.get('title', 'No title')[:60]}...")
            print(f"     Publication: {pub_date}")
            print(f"     Analysis: {analysis_date}")
            print(f"     Source: {article.get('origin', 'Unknown')}")
            print()

    async def fix_articles(self, strategy: str = 'analysis_date') -> bool:
        """
        Fix future-dated articles using the specified strategy.

        Args:
            strategy: 'analysis_date', 'past_date', or 'delete'
        """
        try:
            await db_manager.connect()

            fixed_count = 0
            deleted_count = 0
            error_count = 0

            for article in self.future_articles:
                try:
                    article_id = article['_id']
                    url = article.get('url', 'Unknown')

                    if strategy == 'delete':
                        # Delete the article
                        success = await article_repository.delete_article(str(article_id))
                        if success:
                            deleted_count += 1
                            logger.info(f"Deleted article: {url}")
                        else:
                            error_count += 1
                            logger.error(f"Failed to delete article: {url}")

                    elif strategy == 'analysis_date':
                        # Set publication_date to analysis_date (or date field)
                        analysis_date = article.get('analysis_date') or article.get('date')
                        if analysis_date:
                            success = await article_repository.update_article_publication_date(
                                url, analysis_date
                            )
                            if success:
                                fixed_count += 1
                                logger.info(f"Fixed article (set to analysis_date): {url}")
                            else:
                                error_count += 1
                                logger.error(f"Failed to fix article: {url}")
                        else:
                            error_count += 1
                            logger.error(f"No analysis_date or date for article: {url}")

                    elif strategy == 'past_date':
                        # Set publication_date to a reasonable past date (current time minus 1 day)
                        current_time = datetime.now(timezone.utc)
                        past_date = current_time - timedelta(days=1)
                        success = await article_repository.update_article_publication_date(
                            url, past_date
                        )
                        if success:
                            fixed_count += 1
                            logger.info(f"Fixed article (set to past date): {url}")
                        else:
                            error_count += 1
                            logger.error(f"Failed to fix article: {url}")

                except Exception as e:
                    error_count += 1
                    logger.error(f"Error processing article {url}: {e}")

            self.stats['fixed'] = fixed_count
            self.stats['deleted'] = deleted_count
            self.stats['errors'] = error_count

            print(f"\nFix Results:")
            print(f"  Fixed: {fixed_count}")
            print(f"  Deleted: {deleted_count}")
            print(f"  Errors: {error_count}")

            return error_count == 0

        except Exception as e:
            logger.error(f"Error fixing articles: {e}")
            return False


async def main():
    """Main function to run the future date fixer."""
    parser = argparse.ArgumentParser(description='Fix articles with future publication dates')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying them')
    parser.add_argument('--fix', action='store_true', help='Fix future dates by setting to analysis_date')
    parser.add_argument('--fix-past', action='store_true', help='Fix future dates by setting to past date')
    parser.add_argument('--delete', action='store_true', help='Delete articles with future dates')
    parser.add_argument('--strategy', choices=['analysis_date', 'past_date', 'delete'],
                       default='analysis_date', help='Fix strategy to use')

    args = parser.parse_args()

    if not any([args.dry_run, args.fix, args.fix_past, args.delete]):
        print("Please specify an action: --dry-run, --fix, --fix-past, or --delete")
        return

    fixer = FutureDateFixer()

    # Find future articles
    await fixer.find_future_articles()

    if not fixer.future_articles:
        print("No articles with future dates found.")
        return

    # Print analysis
    fixer.print_analysis()

    if args.dry_run:
        print("\nDRY RUN - No changes made")
        return

    # Apply fixes
    if args.fix or args.fix_past or args.delete:
        strategy = 'analysis_date'
        if args.fix_past:
            strategy = 'past_date'
        elif args.delete:
            strategy = 'delete'

        print(f"\nApplying fixes using strategy: {strategy}")
        success = await fixer.fix_articles(strategy)

        if success:
            print("✅ All fixes applied successfully!")
        else:
            print("❌ Some errors occurred during fixing")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
