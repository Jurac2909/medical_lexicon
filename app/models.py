from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MedicalTerm:
    text: str
    category: str
    score: float = 0.0
    start: int = -1
    end: int = -1
    description: str = ""
    source_url: str = ""

    def as_row(self) -> dict:
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
        return ["term", "category", "confidence", "start", "end", "description", "source"]
