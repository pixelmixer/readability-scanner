"""
Date normalization utilities for consistent date handling across the application.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Union
from dateutil import parser, tz

logger = logging.getLogger(__name__)


def normalize_date(date_input: Union[str, datetime, None]) -> Optional[datetime]:
    """
    Normalize a date input to UTC datetime.

    Args:
        date_input: String, datetime, or None

    Returns:
        UTC datetime object or None if parsing fails
    """
    if date_input is None:
        return None

    try:
        # If it's already a datetime, convert to UTC
        if isinstance(date_input, datetime):
            if date_input.tzinfo is None:
                # Assume naive datetime is UTC
                return date_input.replace(tzinfo=timezone.utc)
            else:
                # Convert to UTC
                return date_input.astimezone(timezone.utc)

        # If it's a string, parse it
        if isinstance(date_input, str):
            date_str = str(date_input).strip()
            if not date_str:
                return None

            # Try parsing with dateutil (handles most formats)
            parsed_date = parser.parse(date_str)

            # Ensure it has timezone info
            if parsed_date.tzinfo is None:
                # Assume naive datetime is UTC
                parsed_date = parsed_date.replace(tzinfo=timezone.utc)
            else:
                # Convert to UTC
                parsed_date = parsed_date.astimezone(timezone.utc)

            return parsed_date

        # Handle other types (like feedparser time_struct)
        if hasattr(date_input, 'time_struct'):
            import time
            naive_dt = datetime.fromtimestamp(time.mktime(date_input.time_struct))
            return naive_dt.replace(tzinfo=timezone.utc)

        # Try to convert to string and parse
        return normalize_date(str(date_input))

    except Exception as e:
        logger.warning(f"Failed to normalize date '{date_input}': {e}")
        return None


def ensure_utc_datetime(dt: datetime) -> datetime:
    """
    Ensure a datetime object is in UTC timezone.

    Args:
        dt: datetime object

    Returns:
        UTC datetime object
    """
    if dt.tzinfo is None:
        # Assume naive datetime is UTC
        return dt.replace(tzinfo=timezone.utc)
    else:
        # Convert to UTC
        return dt.astimezone(timezone.utc)


def format_date_for_storage(date_input: Union[str, datetime, None]) -> Optional[datetime]:
    """
    Format a date for consistent storage in MongoDB.
    This is an alias for normalize_date for clarity.

    Args:
        date_input: String, datetime, or None

    Returns:
        UTC datetime object or None if parsing fails
    """
    return normalize_date(date_input)
