import json
import os
import tempfile
import unittest
from pathlib import Path

from aiohttp.test_utils import AioHTTPTestCase

from app.models import MedicalTerm
from app.paths import ENV_DATA_DIR
from app.protocols import Analyzer, DescriptionFetcher
from app.web import _term_from_json, _term_to_json, create_app


class FakeAnalyzer:
    """Stands in for the neural network: no model, no download."""

    def __init__(self, terms=None, error=None):
        self._terms = terms or []
        self._error = error
        self.calls = []
        self.is_loaded = False

    def analyze(self, text):
        self.calls.append(text)
        if self._error is not None:
            raise self._error
        return [MedicalTerm(**t.__dict__) for t in self._terms]

    def load(self):
        self.is_loaded = True


class FakeFetcher:
    """Stands in for Wikipedia: adds a description without any network call."""

    async def fetch_all(self, terms):
        for term in terms:
            term.description = f"Description of {term.text}."
            term.source_url = f"https://example.invalid/{term.text}"
        return terms


TERMS = [
    MedicalTerm("pneumonia", "disease", 0.93, 0, 9),
    MedicalTerm("fever", "symptom", 0.81, 20, 25),
]


class WebTestCase(AioHTTPTestCase):
    analyzer_error = None

    async def get_application(self):
        self.analyzer = FakeAnalyzer(TERMS, error=self.analyzer_error)
        self.fetcher = FakeFetcher()
        return create_app(analyzer=self.analyzer, fetcher=self.fetcher)

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._previous = os.environ.get(ENV_DATA_DIR)
        os.environ[ENV_DATA_DIR] = self._tmp.name
        super().setUp()

    def tearDown(self):
        super().tearDown()
        if self._previous is None:
            os.environ.pop(ENV_DATA_DIR, None)
        else:
            os.environ[ENV_DATA_DIR] = self._previous
        self._tmp.cleanup()


class TestPages(WebTestCase):
    async def test_index_is_served(self):
        resp = await self.client.get("/")
        self.assertEqual(resp.status, 200)
        body = await resp.text()
        self.assertIn("Medical Term Analysis", body)

    async def test_static_files_are_served(self):
        resp = await self.client.get("/static/app.js")
        self.assertEqual(resp.status, 200)

    async def test_healthz_reports_model_state(self):
        resp = await self.client.get("/healthz")
        self.assertEqual(resp.status, 200)
        data = await resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertFalse(data["model_loaded"])

    async def test_info_contains_runtime_details(self):
        resp = await self.client.get("/api/info")
        data = await resp.json()
        for key in ("version", "model", "machine", "python", "data_dir"):
            self.assertIn(key, data)


class TestAnalyzeEndpoint(WebTestCase):
    async def test_returns_terms_with_descriptions(self):
        resp = await self.client.post(
            "/api/analyze", json={"text": "pneumonia and fever"}
        )
        self.assertEqual(resp.status, 200)
        data = await resp.json()

        self.assertEqual(data["count"], 2)
        self.assertEqual(self.analyzer.calls, ["pneumonia and fever"])
        self.assertEqual(
            [t["text"] for t in data["terms"]], ["pneumonia", "fever"]
        )
        self.assertTrue(
            all(t["description"] for t in data["terms"]),
            "fetcher must fill in the descriptions",
        )

    async def test_empty_text_is_rejected(self):
        resp = await self.client.post("/api/analyze", json={"text": "   "})
        self.assertEqual(resp.status, 400)

    async def test_missing_field_is_rejected(self):
        resp = await self.client.post("/api/analyze", json={})
        self.assertEqual(resp.status, 400)

    async def test_invalid_json_is_rejected(self):
        resp = await self.client.post(
            "/api/analyze",
            data="not json",
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(resp.status, 400)

    async def test_oversized_text_is_rejected(self):
        resp = await self.client.post(
            "/api/analyze", json={"text": "a" * 20_001}
        )
        self.assertEqual(resp.status, 413)

    async def test_analyzer_is_used_through_protocol(self):
        self.assertIsInstance(self.analyzer, Analyzer)
        self.assertIsInstance(self.fetcher, DescriptionFetcher)


class TestAnalyzeFailure(WebTestCase):
    analyzer_error = RuntimeError("model unavailable")

    async def test_failure_returns_json_error(self):
        resp = await self.client.post("/api/analyze", json={"text": "x"})
        self.assertEqual(resp.status, 500)
        data = await resp.json()
        self.assertIn("model unavailable", data["error"])


class TestExportEndpoint(WebTestCase):
    async def test_csv_export_downloads_and_is_saved(self):
        payload = {"terms": [_term_to_json(t) for t in TERMS]}
        resp = await self.client.post("/api/export/csv", json=payload)

        self.assertEqual(resp.status, 200)
        self.assertIn("attachment", resp.headers["Content-Disposition"])

        body = await resp.text()
        self.assertIn("pneumonia", body)
        self.assertIn("term,category,confidence", body)

        saved = Path(resp.headers["X-Export-Path"])
        self.assertTrue(saved.is_file())
        self.assertEqual(saved.parent.parent.name, Path(self._tmp.name).name)

    async def test_unknown_format_is_rejected(self):
        resp = await self.client.post("/api/export/xlsx", json={"terms": []})
        self.assertEqual(resp.status, 404)

    async def test_empty_term_list_is_rejected(self):
        resp = await self.client.post("/api/export/csv", json={"terms": []})
        self.assertEqual(resp.status, 400)

    async def test_pdf_export(self):
        try:
            import reportlab  # noqa: F401
        except ImportError:
            self.skipTest("reportlab is not installed")

        payload = {"terms": [_term_to_json(t) for t in TERMS]}
        resp = await self.client.post("/api/export/pdf", json=payload)
        self.assertEqual(resp.status, 200)
        body = await resp.read()
        self.assertTrue(body.startswith(b"%PDF"))


class TestSerialization(unittest.TestCase):
    def test_round_trip_keeps_values(self):
        original = MedicalTerm(
            "stroke", "disease", 0.8712, 3, 9, "A stroke.", "https://x.invalid"
        )
        restored = _term_from_json(json.loads(json.dumps(_term_to_json(original))))

        self.assertEqual(restored.text, original.text)
        self.assertEqual(restored.category, original.category)
        self.assertAlmostEqual(restored.score, original.score, places=4)
        self.assertEqual(restored.start, original.start)
        self.assertEqual(restored.end, original.end)
        self.assertEqual(restored.description, original.description)
        self.assertEqual(restored.source_url, original.source_url)

    def test_missing_fields_get_defaults(self):
        term = _term_from_json({"text": "flu"})
        self.assertEqual(term.text, "flu")
        self.assertEqual(term.category, "")
        self.assertEqual(term.score, 0.0)
        self.assertEqual(term.description, "")


if __name__ == "__main__":
    unittest.main()
