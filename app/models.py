from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MedicalTerm:
    """A single medical term detected in the analyzed text.

    >>> t = MedicalTerm("stroke", "disease", 0.7234, 5, 11)
    >>> (t.text, t.category, t.start, t.end)
    ('stroke', 'disease', 5, 11)
    >>> MedicalTerm.fieldnames()
    ['term', 'category', 'confidence', 'start', 'end', 'description', 'source']
    """

    text: str
    category: str
    score: float = 0.0
    start: int = -1
    end: int = -1
    description: str = ""
    source_url: str = ""

    def as_row(self) -> dict:
        """Return the term as a row (dict) ready for CSV/PDF export.

        >>> row = MedicalTerm("flu", "disease", 0.5, 0, 3).as_row()
        >>> row["term"], row["category"], row["confidence"]
        ('flu', 'disease', '0.5000')
        >>> sorted(row) == sorted(MedicalTerm.fieldnames())
        True
        """
        return {
            "term": self.text,
            "category": self.category,
            "confidence": f"{self.score:.4f}",
            "start": self.start,
            "end": self.end,
            "description": self.description,
            "source": self.source_url,
        }

    @staticmethod
    def fieldnames() -> list[str]:
        """Return the ordered column names used for export.

        >>> MedicalTerm.fieldnames()[0]
        'term'
        """
        return [
            "term",
            "category",
            "confidence",
            "start",
            "end",
            "description",
            "source",
        ]
