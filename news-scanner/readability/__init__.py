"""
Readability analysis module for news articles.
"""

from .analyzer import ReadabilityAnalyzer, analyze_text
from .formulas import (
    calculate_flesch_reading_ease,
    calculate_flesch_kincaid_grade,
    calculate_smog_index,
    calculate_dale_chall,
    calculate_coleman_liau,
    calculate_gunning_fog,
    calculate_spache,
    calculate_automated_readability
)
from .text_stats import TextStatistics, calculate_text_statistics

__all__ = [
    "ReadabilityAnalyzer",
    "analyze_text",
    "calculate_flesch_reading_ease",
    "calculate_flesch_kincaid_grade",
    "calculate_smog_index",
    "calculate_dale_chall",
    "calculate_coleman_liau",
    "calculate_gunning_fog",
    "calculate_spache",
    "calculate_automated_readability",
    "TextStatistics",
    "calculate_text_statistics"
]
