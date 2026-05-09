"""EDGAR client tests with mocked SEC HTTP responses and local cache paths."""

from __future__ import annotations

import httpx
import pytest

from worker.sec_client import EDGARClient


@pytest.mark.asyncio
async def test_get_cik_resolves_amd_from_company_tickers(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["user-agent"] == "FinContextAgent/0.1 test@example.com"
        return httpx.Response(
            200,
            json={
                "0": {
                    "cik_str": 2488,
                    "ticker": "AMD",
                    "title": "Advanced Micro Devices, Inc.",
                }
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        edgar = EDGARClient(
            "FinContextAgent/0.1 test@example.com",
            cache_dir=tmp_path,
            http_client=client,
        )
        assert await edgar.get_cik("amd") == "0000002488"


def test_build_filing_url_uses_accession_without_dashes():
    url = EDGARClient.build_filing_url(
        "0000002488", "0000002488-25-000012", "amd-20241228.htm"
    )
    assert url == (
        "https://www.sec.gov/Archives/edgar/data/"
        "2488/000000248825000012/amd-20241228.htm"
    )
