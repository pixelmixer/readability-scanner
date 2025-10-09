"""
Readability metrics data model.
"""

from pydantic import BaseModel, Field
from typing import Optional


class ReadabilityMetrics(BaseModel):
    """Readability analysis metrics for an article."""

    # Basic text statistics
    words: int = Field(..., description="Total word count")
    sentences: int = Field(..., description="Total sentence count")
    paragraphs: int = Field(..., description="Total paragraph count")
    characters: int = Field(..., description="Total character count")
    syllables: int = Field(..., description="Total syllable count")

    # Advanced metrics
    word_syllables: float = Field(..., alias="word syllables", description="Average syllables per word")
    complex_polysillabic_words: int = Field(..., alias="complex polysillabic words", description="Number of words with 3+ syllables")

    # Readability formulas
    flesch: float = Field(..., alias="Flesch", description="Flesch Reading Ease score")
    flesch_kincaid: float = Field(..., alias="Flesch Kincaid", description="Flesch-Kincaid Grade Level")
    smog: float = Field(..., alias="Smog", description="SMOG readability index")
    dale_chall: float = Field(..., alias="Dale Chall", description="Dale-Chall readability score")
    dale_chall_grade: Optional[str] = Field(None, alias="Dale Chall: Grade", description="Dale-Chall grade level")
    coleman_liau: float = Field(..., alias="Coleman Liau", description="Coleman-Liau index")
    gunning_fog: float = Field(..., alias="Gunning Fog", description="Gunning Fog index")
    spache: float = Field(..., alias="Spache", description="Spache readability formula")
    automated_readability: float = Field(..., alias="Automated Readability", description="Automated Readability Index")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "words": 250,
                "sentences": 15,
                "paragraphs": 5,
                "characters": 1200,
                "syllables": 350,
                "word_syllables": 1.4,
                "complex_polysillabic_words": 12,
                "flesch": 65.2,
                "flesch_kincaid": 8.5,
                "smog": 9.2,
                "dale_chall": 7.8,
                "dale_chall_grade": "9-10",
                "coleman_liau": 8.9,
                "gunning_fog": 9.1,
                "spache": 6.5,
                "automated_readability": 8.7
            }
        }
