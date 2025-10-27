"""
Script to identify and delete articles from theplainsman.com with incorrect publication dates.

These articles were ingested without publication dates in their RSS feed,
and were incorrectly assigned the current timestamp instead of being rejected.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from motor.motor_asyncio import AsyncIOMotorClient
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def identify_problematic_articles(collection, origin_pattern: str, dry_run: bool = True):
    """
    Identify articles from a specific origin with suspicious publication dates.

    Suspicious dates are those that:
    - Are very recent (within last 24 hours)
    - Have timestamps with milliseconds (indicating they were auto-assigned)
    - Match the pattern of being assigned during RSS scanning

    Args:
        collection: MongoDB collection
        origin_pattern: Origin URL pattern to match (e.g., "theplainsman.com")
        dry_run: If True, only report findings without deleting
    """
    # Find articles from the specified origin
    query = {
        "origin": {"$regex": origin_pattern, "$options": "i"}
    }

    cursor = collection.find(query)
    articles = await cursor.to_list(length=None)

    logger.info(f"Found {len(articles)} total articles from {origin_pattern}")

    # Analyze articles to identify problematic ones
    problematic = []
    suspicious = []
    ok = []

    # Get current time
    now = datetime.now(timezone.utc)
    recent_threshold = now - timedelta(days=1)

    for article in articles:
        url = article.get('url', 'unknown')
        pub_date = article.get('publication_date')
        title = article.get('title', 'Untitled')

        if not pub_date:
            logger.warning(f"Article without publication_date: {url}")
            continue

        # Ensure pub_date is a datetime object
        if isinstance(pub_date, str):
            from dateutil import parser
            try:
                pub_date = parser.parse(pub_date)
            except:
                logger.warning(f"Could not parse date for {url}: {pub_date}")
                continue

        # Ensure pub_date has timezone info for comparison
        if pub_date.tzinfo is None:
            # Assume UTC if no timezone info
            pub_date = pub_date.replace(tzinfo=timezone.utc)

        # Check if date is suspiciously recent (within last 24 hours)
        # AND has high precision (milliseconds/microseconds)
        # This pattern indicates it was auto-assigned by the system
        if pub_date > recent_threshold:
            # Check if it has milliseconds/microseconds (indication of auto-assignment)
            if pub_date.microsecond > 0:
                problematic.append({
                    'id': str(article['_id']),
                    'url': url,
                    'title': title,
                    'publication_date': pub_date.isoformat(),
                    'reason': 'Recent date with high precision (likely auto-assigned)'
                })
            else:
                suspicious.append({
                    'id': str(article['_id']),
                    'url': url,
                    'title': title,
                    'publication_date': pub_date.isoformat(),
                    'reason': 'Recent date without milliseconds (possibly legitimate)'
                })
        else:
            ok.append({
                'url': url,
                'title': title,
                'publication_date': pub_date.isoformat()
            })

    # Report findings
    logger.info(f"\n{'='*80}")
    logger.info(f"ANALYSIS RESULTS for {origin_pattern}")
    logger.info(f"{'='*80}")
    logger.info(f"Total articles: {len(articles)}")
    logger.info(f"Problematic (auto-assigned dates): {len(problematic)}")
    logger.info(f"Suspicious (needs review): {len(suspicious)}")
    logger.info(f"OK (older articles): {len(ok)}")
    logger.info(f"{'='*80}\n")

    if problematic:
        logger.info(f"\n{'-'*80}")
        logger.info(f"PROBLEMATIC ARTICLES (likely auto-assigned dates):")
        logger.info(f"{'-'*80}")
        for i, article in enumerate(problematic[:20], 1):  # Show first 20
            logger.info(f"{i}. {article['title'][:60]}")
            logger.info(f"   URL: {article['url']}")
            logger.info(f"   Date: {article['publication_date']}")
            logger.info(f"   ID: {article['id']}")
            logger.info(f"   Reason: {article['reason']}\n")

        if len(problematic) > 20:
            logger.info(f"... and {len(problematic) - 20} more problematic articles")

    if suspicious:
        logger.info(f"\n{'-'*80}")
        logger.info(f"SUSPICIOUS ARTICLES (may need review):")
        logger.info(f"{'-'*80}")
        for i, article in enumerate(suspicious[:10], 1):  # Show first 10
            logger.info(f"{i}. {article['title'][:60]}")
            logger.info(f"   URL: {article['url']}")
            logger.info(f"   Date: {article['publication_date']}\n")

    # Ask for confirmation if not dry_run
    if not dry_run and problematic:
        logger.info(f"\n{'='*80}")
        response = input(f"\nDelete {len(problematic)} problematic articles? (yes/no): ")

        if response.lower() == 'yes':
            from bson import ObjectId
            deleted_count = 0
            for article in problematic:
                try:
                    result = await collection.delete_one({"_id": ObjectId(article['id'])})
                    if result.deleted_count > 0:
                        deleted_count += 1
                        logger.info(f"Deleted: {article['title'][:60]}")
                except Exception as e:
                    logger.error(f"Error deleting {article['id']}: {e}")

            logger.info(f"\n{'='*80}")
            logger.info(f"Successfully deleted {deleted_count} articles")
            logger.info(f"{'='*80}")
        else:
            logger.info("Deletion cancelled")

    return problematic, suspicious, ok


async def main():
    """Main function to run the cleanup script."""
    import argparse

    parser = argparse.ArgumentParser(description='Fix articles with incorrect publication dates')
    parser.add_argument('--origin', type=str, default='theplainsman.com',
                        help='Origin pattern to match (default: theplainsman.com)')
    parser.add_argument('--delete', action='store_true',
                        help='Actually delete problematic articles (default is dry-run)')

    args = parser.parse_args()

    # Connect to MongoDB
    logger.info(f"Connecting to MongoDB at {settings.mongodb_url}...")
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.database_name]
    collection = db["documents"]

    try:
        # Run the analysis
        await identify_problematic_articles(
            collection,
            origin_pattern=args.origin,
            dry_run=not args.delete
        )

        if not args.delete:
            logger.info("\n" + "="*80)
            logger.info("DRY RUN MODE - No articles were deleted")
            logger.info("To actually delete problematic articles, run with --delete flag")
            logger.info("="*80)

    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())

