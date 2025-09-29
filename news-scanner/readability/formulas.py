"""
Readability formula implementations.

This module implements all the readability formulas used in the original Node.js version
to ensure compatibility and consistent results.
"""

import logging
import math
from .text_stats import TextStatistics

logger = logging.getLogger(__name__)


def calculate_flesch_reading_ease(stats: TextStatistics) -> float:
    """
    Calculate Flesch Reading Ease score.

    Formula: 206.835 - (1.015 × ASL) - (84.6 × ASW)
    Where ASL = Average Sentence Length, ASW = Average Syllables per Word

    Score interpretation:
    90-100: Very Easy
    80-90: Easy
    70-80: Fairly Easy
    60-70: Standard
    50-60: Fairly Difficult
    30-50: Difficult
    0-30: Very Difficult
    """
    try:
        if stats.sentences == 0 or stats.words == 0:
            return 0.0

        asl = stats.words / stats.sentences  # Average Sentence Length
        asw = stats.syllables / stats.words  # Average Syllables per Word

        score = 206.835 - (1.015 * asl) - (84.6 * asw)

        # Clamp to reasonable range
        return max(0.0, min(100.0, score))

    except Exception as e:
        logger.error(f"Error calculating Flesch Reading Ease: {e}")
        return 0.0


def calculate_flesch_kincaid_grade(stats: TextStatistics) -> float:
    """
    Calculate Flesch-Kincaid Grade Level.

    Formula: (0.39 × ASL) + (11.8 × ASW) - 15.59
    Where ASL = Average Sentence Length, ASW = Average Syllables per Word

    Result represents U.S. grade level needed to understand the text.
    """
    try:
        if stats.sentences == 0 or stats.words == 0:
            return 0.0

        asl = stats.words / stats.sentences  # Average Sentence Length
        asw = stats.syllables / stats.words  # Average Syllables per Word

        grade = (0.39 * asl) + (11.8 * asw) - 15.59

        # Grade levels shouldn't be negative
        return max(0.0, grade)

    except Exception as e:
        logger.error(f"Error calculating Flesch-Kincaid Grade: {e}")
        return 0.0


def calculate_smog_index(stats: TextStatistics) -> float:
    """
    Calculate SMOG (Simple Measure of Gobbledygook) Index.

    Formula: 1.0430 × sqrt(polysyllables × (30 / sentences)) + 3.1291

    SMOG estimates the years of education needed to understand the text.
    """
    try:
        if stats.sentences == 0:
            return 0.0

        # Use complex polysyllabic words (3+ syllables)
        polysyllables = stats.complex_polysillabic_words

        # SMOG formula
        smog = 1.0430 * math.sqrt(polysyllables * (30 / stats.sentences)) + 3.1291

        return max(0.0, smog)

    except Exception as e:
        logger.error(f"Error calculating SMOG index: {e}")
        return 0.0


def calculate_dale_chall(stats: TextStatistics) -> float:
    """
    Calculate Dale-Chall Readability Score.

    Simplified version without the full Dale-Chall word list.
    Uses complex words as proxy for difficult words.

    Formula: 0.1579 × (PDW × 100) + 0.0496 × ASL
    Where PDW = Percentage of Difficult Words, ASL = Average Sentence Length
    """
    try:
        if stats.sentences == 0 or stats.words == 0:
            return 0.0

        # Use complex words as proxy for difficult words
        difficult_words_percentage = (stats.complex_polysillabic_words / stats.words) * 100
        asl = stats.words / stats.sentences

        dale_chall = 0.1579 * difficult_words_percentage + 0.0496 * asl

        # Add adjustment for high percentage of difficult words
        if difficult_words_percentage > 5:
            dale_chall += 3.6365

        return max(0.0, dale_chall)

    except Exception as e:
        logger.error(f"Error calculating Dale-Chall: {e}")
        return 0.0


def get_dale_chall_grade_level(score: float) -> str:
    """Convert Dale-Chall score to grade level description."""
    if score <= 4.9:
        return "4th grade or lower"
    elif score <= 5.9:
        return "5th-6th grade"
    elif score <= 6.9:
        return "7th-8th grade"
    elif score <= 7.9:
        return "9th-10th grade"
    elif score <= 8.9:
        return "11th-12th grade"
    elif score <= 9.9:
        return "13th-15th grade (college)"
    else:
        return "16th grade or higher (graduate)"


def calculate_coleman_liau(stats: TextStatistics) -> float:
    """
    Calculate Coleman-Liau Index.

    Formula: 0.0588 × L - 0.296 × S - 15.8
    Where L = average letters per 100 words, S = average sentences per 100 words
    """
    try:
        if stats.words == 0:
            return 0.0

        # Calculate letters per 100 words
        l = (stats.characters / stats.words) * 100

        # Calculate sentences per 100 words
        s = (stats.sentences / stats.words) * 100

        cli = 0.0588 * l - 0.296 * s - 15.8

        return max(0.0, cli)

    except Exception as e:
        logger.error(f"Error calculating Coleman-Liau: {e}")
        return 0.0


def calculate_gunning_fog(stats: TextStatistics) -> float:
    """
    Calculate Gunning Fog Index.

    Formula: 0.4 × (ASL + PHW)
    Where ASL = Average Sentence Length, PHW = Percentage of Hard Words (3+ syllables)
    """
    try:
        if stats.sentences == 0 or stats.words == 0:
            return 0.0

        asl = stats.words / stats.sentences
        phw = (stats.complex_polysillabic_words / stats.words) * 100

        fog = 0.4 * (asl + phw)

        return max(0.0, fog)

    except Exception as e:
        logger.error(f"Error calculating Gunning Fog: {e}")
        return 0.0


def calculate_spache(stats: TextStatistics) -> float:
    """
    Calculate Spache Readability Formula.

    Simplified version: 0.141 × ASL + 0.086 × PDW + 0.839
    Where ASL = Average Sentence Length, PDW = Percentage of Difficult Words
    """
    try:
        if stats.sentences == 0 or stats.words == 0:
            return 0.0

        asl = stats.words / stats.sentences
        pdw = (stats.complex_polysillabic_words / stats.words) * 100

        spache = 0.141 * asl + 0.086 * pdw + 0.839

        return max(0.0, spache)

    except Exception as e:
        logger.error(f"Error calculating Spache: {e}")
        return 0.0


def calculate_automated_readability(stats: TextStatistics) -> float:
    """
    Calculate Automated Readability Index (ARI).

    Formula: 4.71 × (characters / words) + 0.5 × (words / sentences) - 21.43
    """
    try:
        if stats.sentences == 0 or stats.words == 0:
            return 0.0

        chars_per_word = stats.characters / stats.words
        words_per_sentence = stats.words / stats.sentences

        ari = 4.71 * chars_per_word + 0.5 * words_per_sentence - 21.43

        return max(0.0, ari)

    except Exception as e:
        logger.error(f"Error calculating Automated Readability: {e}")
        return 0.0
