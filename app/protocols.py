from __future__ import annotations

from typing import Protocol, runtime_checkable

from .models import MedicalTerm


@runtime_checkable
class Analyzer(Protocol):
    def analyze(self, text: str) -> list[MedicalTerm]:
        ...


@runtime_checkable
class DescriptionFetcher(Protocol):
    async def fetch_all(
        self, terms: list[MedicalTerm]
    ) -> list[MedicalTerm]:
        ...
