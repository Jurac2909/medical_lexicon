import asyncio
import unittest

from app.fetcher import TermInfoFetcher
from app.models import MedicalTerm


class FakeResponse:
    def __init__(self, status, data):
        self.status = status
        self._data = data

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def json(self):
        return self._data


class FakeSession:
    def __init__(self, data, status=200):
        self._data = data
        self._status = status
        self.requests = []

    def get(self, url, params=None):
        self.requests.append((url, params))
        return FakeResponse(self._status, self._data)


def run_fetch_one(data, term, status=200):
    fetcher = TermInfoFetcher()
    session = FakeSession(data, status)
    asyncio.run(fetcher._fetch_one(session, term, asyncio.Semaphore(1)))
    return session


def page(title, extract):
    return {"query": {"pages": {"1": {"title": title, "extract": extract}}}}


class TestFetcher(unittest.TestCase):
    def test_fetch_all_with_empty_list(self):
        result = asyncio.run(TermInfoFetcher().fetch_all([]))
        self.assertEqual(result, [])

    def test_populates_description_and_url(self):
        term = MedicalTerm("stroke", "disease", 0.7)
        run_fetch_one(page("Stroke", "A stroke is bad."), term)
        self.assertEqual(term.description, "A stroke is bad.")
        self.assertEqual(
            term.source_url, "https://en.wikipedia.org/wiki/Stroke"
        )

    def test_missing_page_leaves_term_empty(self):
        data = {"query": {"pages": {"-1": {"missing": ""}}}}
        term = MedicalTerm("zzz", "disease", 0.7)
        run_fetch_one(data, term)
        self.assertEqual(term.description, "")
        self.assertEqual(term.source_url, "")

    def test_http_error_is_handled_gracefully(self):
        term = MedicalTerm("stroke", "disease", 0.7)
        run_fetch_one({}, term, status=403)
        self.assertEqual(term.description, "")
        self.assertEqual(term.source_url, "")

    def test_long_extract_is_truncated(self):
        term = MedicalTerm("x", "disease", 0.7)
        run_fetch_one(page("X", "x" * 500), term)
        self.assertEqual(len(term.description), 400)
        self.assertTrue(term.description.endswith("..."))

    def test_sends_term_as_title_parameter(self):
        term = MedicalTerm("insulin", "therapy", 0.7)
        session = run_fetch_one(page("Insulin", "Hormone."), term)
        _, params = session.requests[0]
        self.assertEqual(params["titles"], "insulin")


if __name__ == "__main__":
    unittest.main()
