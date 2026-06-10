import csv
import os
import tempfile
import unittest

from app.exporters import CSVExporter, Exporter, PDFExporter
from app.models import MedicalTerm


class TestExporters(unittest.TestCase):
    def setUp(self):
        self.terms = [
            MedicalTerm(
                "stroke", "disease", 0.72, 0, 6,
                "A stroke is bad.", "http://a",
            ),
            MedicalTerm(
                "fever", "symptom", 0.83, 7, 12,
                "Fever is a symptom.", "http://b",
            ),
        ]
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_exporter_cannot_be_instantiated(self):
        with self.assertRaises(TypeError):
            Exporter()

    def test_csv_roundtrip(self):
        path = os.path.join(self.tmp.name, "out.csv")
        CSVExporter().export(self.terms, path)
        self.assertTrue(os.path.exists(path))
        with open(path, newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 2)
        self.assertEqual(list(rows[0].keys()), MedicalTerm.fieldnames())
        self.assertEqual(rows[0]["term"], "stroke")
        self.assertEqual(rows[0]["category"], "disease")
        self.assertEqual(rows[1]["term"], "fever")

    def test_csv_includes_definition(self):
        path = os.path.join(self.tmp.name, "out.csv")
        CSVExporter().export(self.terms, path)
        with open(path, encoding="utf-8-sig") as f:
            content = f.read()
        self.assertIn("A stroke is bad.", content)

    def test_pdf_is_created_and_valid(self):
        path = os.path.join(self.tmp.name, "out.pdf")
        PDFExporter().export(self.terms, path)
        self.assertTrue(os.path.exists(path))
        self.assertGreater(os.path.getsize(path), 0)
        with open(path, "rb") as f:
            self.assertEqual(f.read(5), b"%PDF-")

    def test_export_returns_path(self):
        path = os.path.join(self.tmp.name, "ret.csv")
        result = CSVExporter().export(self.terms, path)
        self.assertEqual(str(result), path)


if __name__ == "__main__":
    unittest.main()
