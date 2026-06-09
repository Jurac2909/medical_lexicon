from __future__ import annotations

import asyncio

from .logger import get_logger, log_exceptions
from .models import MedicalTerm

WIKI_API_URL = "https://en.wikipedia.org/w/api.php"

USER_AGENT = (
    "MedicalNERApp/1.0 (https://github.com/edu/medical-ner; "
    "jjurcevic7@gmail.com) python-aiohttp"
)

MAX_CONCURRENCY = 5
REQUEST_TIMEOUT = 10


class TermInfoFetcher:
    def __init__(self, max_concurrency: int = MAX_CONCURRENCY):
        self.max_concurrency = max_concurrency
        self._log = get_logger()

    @log_exceptions(reraise=False)
    async def _fetch_one(self, session, term: MedicalTerm, semaphore) -> None:
        params = {
            "action": "query",
            "format": "json",
            "prop": "extracts",
            "exintro": 1,
            "explaintext": 1,
            "redirects": 1,
            "titles": term.text.strip(),
        }

        async with semaphore:
            async with session.get(WIKI_API_URL, params=params) as resp:
                if resp.status != 200:
                    self._log.info(
                        "No Wikipedia article for '%s' (HTTP %s).",
                        term.text,
                        resp.status,
                    )
                    return
                data = await resp.json()

        pages = data.get("query", {}).get("pages", {})
        page = next(iter(pages.values()), {}) if pages else {}
        if "missing" in page or not page:
            self._log.info("No Wikipedia article for '%s'.", term.text)
            return

        extract = (page.get("extract") or "").strip()
        if extract:
            term.description = extract if len(extract) <= 400 else extract[:397] + "..."
        title = page.get("title", term.text).replace(" ", "_")
        term.source_url = f"https://en.wikipedia.org/wiki/{title}"

    @log_exceptions
    async def fetch_all(self, terms: list[MedicalTerm]) -> list[MedicalTerm]:
        if not terms:
            return terms

        import aiohttp

        semaphore = asyncio.Semaphore(self.max_concurrency)
        timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        headers = {"User-Agent": USER_AGENT}

        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            tasks = [
                asyncio.create_task(self._fetch_one(session, term, semaphore))
                for term in terms
            ]
            await asyncio.gather(*tasks)

        self._log.info("Fetched descriptions for %d terms.", len(terms))
        return terms
