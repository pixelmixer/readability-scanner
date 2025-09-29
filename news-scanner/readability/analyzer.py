"""
Main readability analyzer that combines text statistics and formula calculations.
"""

import logging
import re
from typing import Dict, Any
from html2text import html2text
from bs4 import BeautifulSoup

from models.readability import ReadabilityMetrics
from .text_stats import TextStatistics, calculate_text_statistics
from .formulas import (
    calculate_flesch_reading_ease,
    calculate_flesch_kincaid_grade,
    calculate_smog_index,
    calculate_dale_chall,
    get_dale_chall_grade_level,
    calculate_coleman_liau,
    calculate_gunning_fog,
    calculate_spache,
    calculate_automated_readability
)

logger = logging.getLogger(__name__)


class ReadabilityAnalyzer:
    """Main readability analysis engine."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def clean_html_content(self, html_content: str) -> str:
        """
        Clean HTML content to extract plain text for analysis.

        This mirrors the Node.js cleaning process:
        1. Strip all HTML tags except paragraphs
        2. Remove HTML entities
        3. Replace paragraph tags with newlines
        4. Normalize whitespace
        """
        try:
            # Use BeautifulSoup to parse HTML safely
            soup = BeautifulSoup(html_content, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Get text content
            text = soup.get_text()

            # Clean up whitespace - replace multiple spaces/newlines with single space
            text = re.sub(r'\s+', ' ', text)

            # Remove HTML entities that might remain
            text = text.replace('&nbsp;', ' ')
            text = text.replace('&amp;', '&')
            text = text.replace('&lt;', '<')
            text = text.replace('&gt;', '>')
            text = text.replace('&quot;', '"')

            # Strip leading/trailing whitespace
            text = text.strip()

            self.logger.debug(f"Cleaned HTML content: {len(text)} characters")
            return text

        except Exception as e:
            self.logger.error(f"Error cleaning HTML content: {e}")
            # Fallback to simple tag removal
            return re.sub(r'<[^>]+>', ' ', html_content).strip()

    def analyze_text(self, text: str, is_html: bool = False) -> ReadabilityMetrics:
        """
        Perform complete readability analysis on text.

        Args:
            text: Input text (HTML or plain text)
            is_html: Whether the input is HTML that needs cleaning

        Returns:
            ReadabilityMetrics object with all computed scores
        """
        try:
            # Clean HTML if needed
            if is_html:
                cleaned_text = self.clean_html_content(text)
            else:
                cleaned_text = text.strip()

            if not cleaned_text:
                self.logger.warning("Empty text provided for analysis")
                return self._create_empty_metrics()

            # Calculate text statistics
            stats = calculate_text_statistics(cleaned_text)

            if stats.words == 0:
                self.logger.warning("No words found in text")
                return self._create_empty_metrics()

            # Calculate all readability formulas
            flesch = calculate_flesch_reading_ease(stats)
            flesch_kincaid = calculate_flesch_kincaid_grade(stats)
            smog = calculate_smog_index(stats)
            dale_chall = calculate_dale_chall(stats)
            dale_chall_grade = get_dale_chall_grade_level(dale_chall)
            coleman_liau = calculate_coleman_liau(stats)
            gunning_fog = calculate_gunning_fog(stats)
            spache = calculate_spache(stats)
            automated_readability = calculate_automated_readability(stats)

            # Create metrics object
            metrics = ReadabilityMetrics(
                words=stats.words,
                sentences=stats.sentences,
                paragraphs=stats.paragraphs,
                characters=stats.characters,
                syllables=stats.syllables,
                word_syllables=stats.word_syllables,
                complex_polysillabic_words=stats.complex_polysillabic_words,
                flesch=flesch,
                flesch_kincaid=flesch_kincaid,
                smog=smog,
                dale_chall=dale_chall,
                dale_chall_grade=dale_chall_grade,
                coleman_liau=coleman_liau,
                gunning_fog=gunning_fog,
                spache=spache,
                automated_readability=automated_readability
            )

            self.logger.info(f"Readability analysis completed: {stats.words} words, Flesch: {flesch:.1f}")
            return metrics

        except Exception as e:
            self.logger.error(f"Error in readability analysis: {e}")
            return self._create_empty_metrics()

    def _create_empty_metrics(self) -> ReadabilityMetrics:
        """Create empty/zero readability metrics for error cases."""
        return ReadabilityMetrics(
            words=0,
            sentences=0,
            paragraphs=0,
            characters=0,
            syllables=0,
            word_syllables=0.0,
            complex_polysillabic_words=0,
            flesch=0.0,
            flesch_kincaid=0.0,
            smog=0.0,
            dale_chall=0.0,
            dale_chall_grade="Unknown",
            coleman_liau=0.0,
            gunning_fog=0.0,
            spache=0.0,
            automated_readability=0.0
        )

    def analyze_and_convert_to_dict(self, text: str, is_html: bool = False) -> Dict[str, Any]:
        """
        Analyze text and return results as dictionary for database storage.

        This format matches the Node.js version for compatibility.
        """
        metrics = self.analyze_text(text, is_html)

        # Convert to dictionary with both original and alias field names
        return {
            # Basic statistics
            "words": metrics.words,
            "sentences": metrics.sentences,
            "paragraphs": metrics.paragraphs,
            "characters": metrics.characters,
            "syllables": metrics.syllables,
            "word syllables": metrics.word_syllables,
            "complex polysillabic words": metrics.complex_polysillabic_words,

            # Readability scores
            "Flesch": metrics.flesch,
            "Flesch Kincaid": metrics.flesch_kincaid,
            "Smog": metrics.smog,
            "Dale Chall": metrics.dale_chall,
            "Dale Chall: Grade": metrics.dale_chall_grade,
            "Coleman Liau": metrics.coleman_liau,
            "Gunning Fog": metrics.gunning_fog,
            "Spache": metrics.spache,
            "Automated Readability": metrics.automated_readability
        }


# Global analyzer instance
analyzer = ReadabilityAnalyzer()


def analyze_text(text: str, is_html: bool = False) -> ReadabilityMetrics:
    """Convenience function for text analysis."""
    return analyzer.analyze_text(text, is_html)
