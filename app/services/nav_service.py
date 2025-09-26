"""
NAV fetching service for mutual funds using mfapi.in API
"""

import asyncio
import time
from decimal import Decimal
from typing import List, Optional

import httpx
from pydantic import BaseModel

from app.schemas.mutual_funds_schema import NavFetchResult


class NavService:
    """Service for fetching NAV data from mfapi.in"""

    BASE_URL = "https://api.mfapi.in"
    TIMEOUT = 10  # seconds
    RATE_LIMIT_DELAY = 0.1  # seconds between requests

    @staticmethod
    async def fetch_nav_for_scheme(scheme_code: str) -> NavFetchResult:
        """Fetch NAV data for a single scheme code."""
        try:
            async with httpx.AsyncClient(timeout=NavService.TIMEOUT) as client:
                url = f"{NavService.BASE_URL}/mf/{scheme_code}"
                response = await client.get(url)

                if response.status_code == 404:
                    return NavFetchResult(
                        scheme_code=scheme_code,
                        success=False,
                        error_message="Scheme code not found"
                    )

                response.raise_for_status()
                data = response.json()

                # Extract latest NAV data
                nav_data = data.get("data", [])
                if not nav_data:
                    return NavFetchResult(
                        scheme_code=scheme_code,
                        success=False,
                        error_message="No NAV data available"
                    )

                latest_nav = nav_data[0]  # Most recent NAV is first
                fund_name = data.get("meta", {}).get("scheme_name", "")

                return NavFetchResult(
                    scheme_code=scheme_code,
                    fund_name=fund_name,
                    nav_value=float(latest_nav.get("nav", 0)),
                    nav_date=latest_nav.get("date"),
                    success=True
                )

        except httpx.TimeoutException:
            return NavFetchResult(
                scheme_code=scheme_code,
                success=False,
                error_message="Request timeout"
            )
        except httpx.HTTPStatusError as e:
            return NavFetchResult(
                scheme_code=scheme_code,
                success=False,
                error_message=f"HTTP {e.response.status_code}: {e.response.text}"
            )
        except Exception as e:
            return NavFetchResult(
                scheme_code=scheme_code,
                success=False,
                error_message=str(e)
            )

    @staticmethod
    async def fetch_nav_bulk(scheme_codes: List[str]) -> List[NavFetchResult]:
        """Fetch NAV data for multiple scheme codes with rate limiting."""
        results = []

        # Process in batches to avoid overwhelming the API
        for scheme_code in scheme_codes:
            result = await NavService.fetch_nav_for_scheme(scheme_code)
            results.append(result)

            # Rate limiting delay
            if len(scheme_codes) > 1:
                await asyncio.sleep(NavService.RATE_LIMIT_DELAY)

        return results

    @staticmethod
    def fetch_nav_bulk_sync(scheme_codes: List[str]) -> List[NavFetchResult]:
        """Synchronous wrapper for bulk NAV fetching."""
        async def run_async():
            return await NavService.fetch_nav_bulk(scheme_codes)

        # Run the async function in a new event loop
        try:
            import nest_asyncio
            nest_asyncio.apply()
        except ImportError:
            pass

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(run_async())
        finally:
            loop.close()