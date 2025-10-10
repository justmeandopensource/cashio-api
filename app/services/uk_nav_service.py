"""
UK NAV fetching service for mutual funds using Alpha Vantage API
"""

import asyncio
from typing import List

import httpx

from app.schemas.mutual_funds_schema import NavFetchResult


class UkNavService:
    """Service for fetching NAV data from Alpha Vantage API"""

    BASE_URL = "https://www.alphavantage.co/query"
    TIMEOUT = 10  # seconds
    RATE_LIMIT_DELAY = 0.1  # seconds between requests

    @staticmethod
    async def fetch_nav_for_symbol(api_key: str, symbol: str) -> NavFetchResult:
        """Fetch NAV data for a single symbol."""
        try:
            async with httpx.AsyncClient(timeout=UkNavService.TIMEOUT) as client:
                params = {
                    "function": "GLOBAL_QUOTE",
                    "symbol": symbol,
                    "apikey": api_key
                }
                response = await client.get(UkNavService.BASE_URL, params=params)

                if response.status_code == 200:
                    data = response.json()

                    # Check for API errors
                    if "Error Message" in data:
                        return NavFetchResult(
                            scheme_code=symbol,
                            success=False,
                            error_message=data["Error Message"],
                        )

                    if "Note" in data:
                        return NavFetchResult(
                            scheme_code=symbol,
                            success=False,
                            error_message=data["Note"],
                        )

                    global_quote = data.get("Global Quote", {})
                    if not global_quote:
                        return NavFetchResult(
                            scheme_code=symbol,
                            success=False,
                            error_message="No quote data available",
                        )

                    price_str = global_quote.get("05. price")
                    date_str = global_quote.get("07. latest trading day")

                    if not price_str or not date_str:
                        return NavFetchResult(
                            scheme_code=symbol,
                            success=False,
                            error_message="Price or date data missing",
                        )

                    try:
                        nav_value = float(price_str)
                        # Convert date from YYYY-MM-DD to DD-MM-YYYY format to match Indian service
                        date_parts = date_str.split('-')
                        if len(date_parts) == 3:
                            nav_date = f"{date_parts[2]}-{date_parts[1]}-{date_parts[0]}"
                        else:
                            nav_date = date_str

                        return NavFetchResult(
                            scheme_code=symbol,
                            fund_name=symbol,  # Alpha Vantage doesn't provide fund names
                            nav_value=nav_value,
                            nav_date=nav_date,
                            success=True,
                        )
                    except (ValueError, TypeError) as e:
                        return NavFetchResult(
                            scheme_code=symbol,
                            success=False,
                            error_message=f"Invalid price format: {price_str}",
                        )

                elif response.status_code == 429:
                    return NavFetchResult(
                        scheme_code=symbol,
                        success=False,
                        error_message="API rate limit exceeded",
                    )
                else:
                    return NavFetchResult(
                        scheme_code=symbol,
                        success=False,
                        error_message=f"HTTP {response.status_code}: {response.text}",
                    )

        except httpx.TimeoutException:
            return NavFetchResult(
                scheme_code=symbol, success=False, error_message="Request timeout"
            )
        except httpx.HTTPStatusError as e:
            return NavFetchResult(
                scheme_code=symbol,
                success=False,
                error_message=f"HTTP {e.response.status_code}: {e.response.text}",
            )
        except Exception as e:
            return NavFetchResult(
                scheme_code=symbol, success=False, error_message=str(e)
            )

    @staticmethod
    async def fetch_nav_bulk(api_key: str, symbols: List[str]) -> List[NavFetchResult]:
        """Fetch NAV data for multiple symbols with rate limiting."""
        results = []

        # Process in batches to avoid overwhelming the API
        for symbol in symbols:
            result = await UkNavService.fetch_nav_for_symbol(api_key, symbol)
            results.append(result)

            # Rate limiting delay
            if len(symbols) > 1:
                await asyncio.sleep(UkNavService.RATE_LIMIT_DELAY)

        return results

    @staticmethod
    def fetch_nav_bulk_sync(api_key: str, symbols: List[str]) -> List[NavFetchResult]:
        """Synchronous wrapper for bulk NAV fetching."""

        async def run_async():
            return await UkNavService.fetch_nav_bulk(api_key, symbols)

        # Run the async function in a new event loop
        try:
            import nest_asyncio  # type: ignore[import]

            nest_asyncio.apply()
        except ImportError:
            pass

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(run_async())
        finally:
            loop.close()