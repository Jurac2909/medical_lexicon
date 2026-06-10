import unittest

from app.ner import MedicalNERAnalyzer
from app.protocols import Analyzer


class FakePipeline:
    def __init__(self, entities):
        self._entities = entities

    def __call__(self, text):
        return self._entities


def make_analyzer(entities, min_score=0.0):
    analyzer = MedicalNERAnalyzer(min_score=min_score)
    analyzer._pipeline = FakePipeline(entities)
    return analyzer


def ent(group, score, word, start=0, end=1):
    return {
        "entity_group": group,
        "score": score,
        "word": word,
        "start": start,
        "end": end,
    }


class TestAnalyze(unittest.TestCase):
    def test_empty_text_returns_empty(self):
        analyzer = make_analyzer([ent("DISEASE_DISORDER", 0.9, "x")])
        self.assertEqual(analyzer.analyze("   "), [])

    def test_category_mapping(self):
        entities = [
            ent("DISEASE_DISORDER", 0.9, "stroke"),
            ent("SIGN_SYMPTOM", 0.8, "fever"),
            ent("MEDICATION", 0.7, "insulin"),
            ent("THERAPEUTIC_PROCEDURE", 0.7, "surgery"),
            ent("DIAGNOSTIC_PROCEDURE", 0.6, "mri"),
            ent("BIOLOGICAL_STRUCTURE", 0.6, "artery"),
        ]
        terms = make_analyzer(entities).analyze("text")
        mapping = {t.text: t.category for t in terms}
        self.assertEqual(mapping["stroke"], "disease")
        self.assertEqual(mapping["fever"], "symptom")
        self.assertEqual(mapping["insulin"], "therapy")
        self.assertEqual(mapping["surgery"], "therapy")
        self.assertEqual(mapping["mri"], "diagnostics")
        self.assertEqual(mapping["artery"], "anatomy")

    def test_irrelevant_categories_filtered_out(self):
        entities = [
            ent("SEVERITY", 0.99, "high"),
            ent("DETAILED_DESCRIPTION", 0.99, "chronic"),
            ent("DOSAGE", 0.99, "10mg"),
        ]
        self.assertEqual(make_analyzer(entities).analyze("text"), [])

    def test_min_score_filters_low_confidence(self):
        entities = [
            ent("DISEASE_DISORDER", 0.10, "low"),
            ent("DISEASE_DISORDER", 0.90, "high"),
        ]
        terms = make_analyzer(entities, min_score=0.5).analyze("text")
        self.assertEqual([t.text for t in terms], ["high"])

    def test_deduplicates_same_word_and_category(self):
        entities = [
            ent("DISEASE_DISORDER", 0.9, "flu"),
            ent("DISEASE_DISORDER", 0.8, "Flu"),
        ]
        terms = make_analyzer(entities).analyze("text")
        self.assertEqual(len(terms), 1)
        self.assertEqual(terms[0].text, "flu")

    def test_results_sorted_by_score_descending(self):
        entities = [
            ent("DISEASE_DISORDER", 0.3, "a"),
            ent("DISEASE_DISORDER", 0.9, "b"),
            ent("DISEASE_DISORDER", 0.6, "c"),
        ]
        terms = make_analyzer(entities).analyze("text")
        self.assertEqual([t.text for t in terms], ["b", "c", "a"])

    def test_does_not_load_model_when_pipeline_present(self):
        analyzer = make_analyzer([])

        def fail():
            raise AssertionError("load() must not be called")

        analyzer.load = fail
        self.assertEqual(analyzer.analyze("text"), [])

    def test_analyzer_satisfies_protocol(self):
        self.assertIsInstance(make_analyzer([]), Analyzer)


if __name__ == "__main__":
    unittest.main()
