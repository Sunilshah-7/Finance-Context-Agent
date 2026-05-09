"""Async SEC EDGAR client used by the pre-demo ingestion CLI.

The client enforces the SEC User-Agent requirement, caches ticker-to-CIK data
and filing HTML locally, rate-limits requests to EDGAR, and returns lightweight
``FilingRef`` records for the parser/chunker pipeline.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path
from typing import Any

import httpx

from .models import FilingRef


class AsyncRateLimiter:
    def __init__(self, requests_per_second: float) -> None:
        if requests_per_second <= 0:
            raise ValueError("requests_per_second must be positive")
        self._interval = 1.0 / requests_per_second
        self._lock = asyncio.Lock()
        self._last_request = 0.0

    async def wait(self) -> None:
        async with self._lock:
            loop = asyncio.get_running_loop()
            now = loop.time()
            sleep_for = self._interval - (now - self._last_request)
            if sleep_for > 0:
                await asyncio.sleep(sleep_for)
            self._last_request = loop.time()


class EDGARClient:
    DATA_URL = "https://data.sec.gov"
    SEC_URL = "https://www.sec.gov"
    TICKERS_URL = f"{SEC_URL}/files/company_tickers.json"

    def __init__(
        self,
        user_agent: str | None = None,
        *,
        cache_dir: str | Path = ".cache/edgar",
        rate_limit: float = 10.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.user_agent = user_agent or os.getenv("SEC_USER_AGENT", "")
        if not self.user_agent or "@" not in self.user_agent:
            raise ValueError(
                "SEC_USER_AGENT must identify the app and include a contact email"
            )

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(
            headers={"User-Agent": self.user_agent},
            timeout=httpx.Timeout(30.0, connect=10.0),
        )
        self._rate_limiter = AsyncRateLimiter(rate_limit)
        self._ticker_map: dict[str, dict[str, Any]] | None = None

    async def __aenter__(self) -> EDGARClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    @staticmethod
    def normalize_cik(cik: str | int) -> str:
        return str(cik).strip().zfill(10)

    @staticmethod
    def accession_path(accession_number: str) -> str:
        return accession_number.replace("-", "")

    @classmethod
    def build_filing_url(
        cls, cik: str | int, accession_number: str, primary_document: str
    ) -> str:
        cik_stripped = str(int(str(cik)))
        accession = cls.accession_path(accession_number)
        return (
            f"{cls.SEC_URL}/Archives/edgar/data/"
            f"{cik_stripped}/{accession}/{primary_document}"
        )

    async def get_cik(self, ticker: str) -> str:
        record = await self.get_company_record(ticker)
        return self.normalize_cik(record["cik_str"])

    async def get_company_record(self, ticker: str) -> dict[str, Any]:
        mapping = await self._load_ticker_map()
        ticker_upper = ticker.upper()
        try:
            return mapping[ticker_upper]
        except KeyError as exc:
            raise KeyError(f"ticker not found in SEC company_tickers: {ticker}") from exc

    async def get_filings(
        self,
        *,
        ticker: str,
        cik: str,
        filing_type: str,
        from_date: str | None = None,
        to_date: str | None = None,
        company_name: str | None = None,
    ) -> list[FilingRef]:
        cik_padded = self.normalize_cik(cik)
        url = f"{self.DATA_URL}/submissions/CIK{cik_padded}.json"
        data = await self._get_json(url)
        recent = data.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        results: list[FilingRef] = []

        for index, form in enumerate(forms):
            if form != filing_type:
                continue
            filed_at = self._recent_value(recent, "filingDate", index)
            if from_date and filed_at < from_date:
                continue
            if to_date and filed_at > to_date:
                continue

            accession_number = self._recent_value(recent, "accessionNumber", index)
            primary_document = self._recent_value(recent, "primaryDocument", index)
            report_date = self._recent_value(recent, "reportDate", index, default="")
            source_url = self.build_filing_url(cik_padded, accession_number, primary_document)
            results.append(
                FilingRef(
                    ticker=ticker.upper(),
                    cik=cik_padded,
                    company_name=company_name or data.get("name"),
                    filing_type=form,
                    accession_number=accession_number,
                    filed_at=filed_at,
                    primary_document=primary_document,
                    fiscal_period=self._infer_fiscal_period(form, report_date, filed_at),
                    source_url=source_url,
                )
            )

        return results

    async def download_filing(self, filing: FilingRef) -> str:
        source_url = filing.source_url or self.build_filing_url(
            filing.cik, filing.accession_number, filing.primary_document
        )
        cache_path = self._filing_cache_path(filing)
        if cache_path.exists():
            return cache_path.read_text(encoding="utf-8", errors="replace")

        await self._rate_limiter.wait()
        response = await self._client.get(
            source_url, headers={"User-Agent": self.user_agent}
        )
        response.raise_for_status()
        text = response.text
        cache_path.write_text(text, encoding="utf-8")
        await asyncio.sleep(0.1)
        return text

    async def _load_ticker_map(self) -> dict[str, dict[str, Any]]:
        if self._ticker_map is not None:
            return self._ticker_map

        cache_path = self.cache_dir / "company_tickers.json"
        if cache_path.exists():
            raw = json.loads(cache_path.read_text(encoding="utf-8"))
        else:
            raw = await self._get_json(self.TICKERS_URL)
            cache_path.write_text(json.dumps(raw, sort_keys=True), encoding="utf-8")

        self._ticker_map = {
            record["ticker"].upper(): record for record in raw.values()
        }
        return self._ticker_map

    async def _get_json(self, url: str) -> dict[str, Any]:
        await self._rate_limiter.wait()
        response = await self._client.get(url, headers={"User-Agent": self.user_agent})
        response.raise_for_status()
        return response.json()

    def _filing_cache_path(self, filing: FilingRef) -> Path:
        accession = self.accession_path(filing.accession_number)
        safe_doc = re.sub(r"[^A-Za-z0-9_.-]", "_", filing.primary_document)
        return self.cache_dir / f"{filing.ticker}_{filing.filing_type}_{accession}_{safe_doc}"

    @staticmethod
    def _recent_value(
        recent: dict[str, list[Any]], key: str, index: int, *, default: str | None = None
    ) -> str:
        values = recent.get(key, [])
        if index >= len(values) or values[index] in (None, ""):
            if default is not None:
                return default
            raise ValueError(f"SEC submissions response missing {key}[{index}]")
        return str(values[index])

    @staticmethod
    def _infer_fiscal_period(
        filing_type: str, report_date: str | None, filed_at: str
    ) -> str:
        date_value = report_date or filed_at
        year = date_value[:4]
        if filing_type == "10-K":
            return f"FY{year}"
        if filing_type == "10-Q":
            return f"Q-{year}"
        return year
