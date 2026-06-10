import unittest

from app.models import MedicalTerm


class TestMedicalTerm(unittest.TestCase):
    def test_defaults(self):
        t = MedicalTerm("pain", "symptom")
        self.assertEqual(t.score, 0.0)
        self.assertEqual(t.start, -1)
        self.assertEqual(t.end, -1)
        self.assertEqual(t.description, "")
        self.assertEqual(t.source_url, "")

    def test_fieldnames(self):
        self.assertEqual(
            MedicalTerm.fieldnames(),
            [
                "term",
                "category",
                "confidence",
                "start",
                "end",
                "description",
                "source",
            ],
        )

    def test_as_row_values(self):
        t = MedicalTerm("stroke", "disease", 0.7234, 5, 11, "desc", "u")
        row = t.as_row()
        self.assertEqual(row["term"], "stroke")
        self.assertEqual(row["category"], "disease")
        self.assertEqual(row["confidence"], "0.7234")
        self.assertEqual(row["start"], 5)
        self.assertEqual(row["end"], 11)
        self.assertEqual(row["description"], "desc")
        self.assertEqual(row["source"], "u")

    def test_as_row_confidence_is_formatted_string(self):
        row = MedicalTerm("x", "disease", 0.5).as_row()
        self.assertEqual(row["confidence"], "0.5000")

    def test_as_row_has_exactly_the_fieldnames(self):
        row = MedicalTerm("x", "disease").as_row()
        self.assertEqual(set(row), set(MedicalTerm.fieldnames()))


if __name__ == "__main__":
    unittest.main()
