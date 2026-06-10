from __future__ import annotations

from .logger import get_logger, log_exceptions
from .models import MedicalTerm

MODEL_NAME = "Clinical-AI-Apollo/Medical-NER"

_CATEGORY_MAP = {
    "DISEASE_DISORDER": "disease",
    "SIGN_SYMPTOM": "symptom",
    "MEDICATION": "therapy",
    "THERAPEUTIC_PROCEDURE": "therapy",
    "DIAGNOSTIC_PROCEDURE": "diagnostics",
    "BIOLOGICAL_STRUCTURE": "anatomy",
}

RELEVANT_CATEGORIES = {
    "disease",
    "symptom",
    "therapy",
    "diagnostics",
    "anatomy",
}


class MedicalNERAnalyzer:
    def __init__(
        self,
        model_name: str = MODEL_NAME,
        min_score: float = 0.0,
    ) -> None:
        self.model_name = model_name
        self.min_score = min_score
        self._pipeline = None
        self._log = get_logger()

    @property
    def is_loaded(self) -> bool:
        return self._pipeline is not None

    @log_exceptions
    def load(self) -> None:
        if self._pipeline is not None:
            return

        from transformers import (
            AutoModelForTokenClassification,
            AutoTokenizer,
            pipeline,
        )

        self._log.info("Loading model '%s'...", self.model_name)
        tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        model = AutoModelForTokenClassification.from_pretrained(
            self.model_name
        )
        self._pipeline = pipeline(
            task="ner",
            model=model,
            tokenizer=tokenizer,
            aggregation_strategy="simple",
        )
        self._log.info("Model loaded successfully.")

    @log_exceptions
    def analyze(self, text: str) -> list[MedicalTerm]:
        text = (text or "").strip()
        if not text:
            return []

        if self._pipeline is None:
            self.load()

        raw_entities = self._pipeline(text)

        terms: list[MedicalTerm] = []
        seen: set[tuple[str, str]] = set()
        for ent in raw_entities:
            score = float(ent.get("score", 0.0))
            if score < self.min_score:
                continue

            raw_label = ent.get("entity_group", "")
            category = _CATEGORY_MAP.get(raw_label, raw_label.lower())
            if category not in RELEVANT_CATEGORIES:
                continue

            word = ent.get("word", "").strip()
            if not word:
                continue

            key = (word.lower(), category)
            if key in seen:
                continue
            seen.add(key)

            terms.append(
                MedicalTerm(
                    text=word,
                    category=category,
                    score=score,
                    start=int(ent.get("start", -1)),
                    end=int(ent.get("end", -1)),
                )
            )

        terms.sort(key=lambda t: t.score, reverse=True)
        self._log.info("Found %d medical terms.", len(terms))
        return terms
