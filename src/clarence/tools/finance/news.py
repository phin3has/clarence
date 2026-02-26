from typing import Optional
from clarence.tools.finance.api import call_api


def get_news(
    ticker: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 5,
) -> list:
    """Retrieve recent news articles for a ticker."""
    params = {"ticker": ticker, "limit": limit}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    data = call_api("/news/", params)
    return data.get("news", [])
