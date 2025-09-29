"""
Text statistics calculation for readability analysis.
"""

import re
import logging
from dataclasses import dataclass
from typing import List
import syllables

logger = logging.getLogger(__name__)


@dataclass
class TextStatistics:
    """Container for text statistics."""

    words: int
    sentences: int
    paragraphs: int
    characters: int
    syllables: int
    word_syllables: float  # Average syllables per word
    complex_polysillabic_words: int  # Words with 3+ syllables


def count_sentences(text: str) -> int:
    """
    Count sentences in text.

    Uses regex to identify sentence boundaries based on punctuation.
    """
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text.strip())

    # Split on sentence-ending punctuation followed by whitespace or end of string
    sentences = re.split(r'[.!?]+(?:\s+|$)', text)

    # Filter out empty strings
    sentences = [s for s in sentences if s.strip()]

    return len(sentences)


def count_paragraphs(text: str) -> int:
    """
    Count paragraphs in text.

    Paragraphs are separated by double newlines or paragraph tags.
    """
    # Split on double newlines or paragraph boundaries
    paragraphs = re.split(r'\n\s*\n|\r\n\s*\r\n', text)

    # Filter out empty paragraphs
    paragraphs = [p for p in paragraphs if p.strip()]

    return len(paragraphs)


def count_words(text: str) -> int:
    """
    Count words in text.

    Words are sequences of alphanumeric characters.
    """
    # Use regex to find word boundaries
    words = re.findall(r'\b\w+\b', text)
    return len(words)


def count_characters(text: str) -> int:
    """Count characters in text (excluding whitespace)."""
    # Remove all whitespace and count remaining characters
    return len(re.sub(r'\s', '', text))


def count_syllables_in_word(word: str) -> int:
    """
    Count syllables in a single word.

    Uses the syllables library for accuracy.
    """
    try:
        count = syllables.estimate(word)
        # Ensure at least 1 syllable per word
        return max(count, 1)
    except Exception:
        # Fallback: simple vowel counting
        word = word.lower()
        vowels = 'aeiouy'
        syllable_count = 0
        prev_was_vowel = False

        for char in word:
            if char in vowels:
                if not prev_was_vowel:
                    syllable_count += 1
                prev_was_vowel = True
            else:
                prev_was_vowel = False

        # Adjust for silent 'e'
        if word.endswith('e') and syllable_count > 1:
            syllable_count -= 1

        return max(syllable_count, 1)


def count_total_syllables(text: str) -> int:
    """Count total syllables in text."""
    words = re.findall(r'\b\w+\b', text)
    return sum(count_syllables_in_word(word) for word in words)


def get_word_syllable_counts(text: str) -> List[int]:
    """Get syllable count for each word in text."""
    words = re.findall(r'\b\w+\b', text)
    return [count_syllables_in_word(word) for word in words]


def count_complex_words(text: str, syllable_threshold: int = 3) -> int:
    """
    Count complex words (words with 3+ syllables by default).

    Args:
        text: Input text
        syllable_threshold: Minimum syllables to consider a word complex

    Returns:
        Number of complex words
    """
    word_syllables = get_word_syllable_counts(text)
    return len([count for count in word_syllables if count >= syllable_threshold])


def calculate_text_statistics(text: str) -> TextStatistics:
    """
    Calculate comprehensive text statistics.

    Args:
        text: Input text to analyze

    Returns:
        TextStatistics object with all computed metrics
    """
    try:
        # Clean up text
        cleaned_text = text.strip()

        if not cleaned_text:
            # Return zero stats for empty text
            return TextStatistics(
                words=0,
                sentences=0,
                paragraphs=0,
                characters=0,
                syllables=0,
                word_syllables=0.0,
                complex_polysillabic_words=0
            )

        # Calculate basic counts
        words = count_words(cleaned_text)
        sentences = count_sentences(cleaned_text)
        paragraphs = count_paragraphs(cleaned_text)
        characters = count_characters(cleaned_text)
        total_syllables = count_total_syllables(cleaned_text)

        # Calculate averages and complex metrics
        word_syllables = total_syllables / words if words > 0 else 0.0
        complex_words = count_complex_words(cleaned_text)

        # Ensure minimum values
        sentences = max(sentences, 1)
        words = max(words, 1)

        stats = TextStatistics(
            words=words,
            sentences=sentences,
            paragraphs=paragraphs,
            characters=characters,
            syllables=total_syllables,
            word_syllables=word_syllables,
            complex_polysillabic_words=complex_words
        )

        logger.debug(f"Text statistics calculated: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Error calculating text statistics: {e}")
        # Return minimal stats on error
        return TextStatistics(
            words=1,
            sentences=1,
            paragraphs=1,
            characters=len(text),
            syllables=1,
            word_syllables=1.0,
            complex_polysillabic_words=0
        )
