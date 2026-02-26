from typing import Optional
from clarence.tools.finance.api import call_api


def get_financial_metrics_snapshot(ticker: str) -> dict:
    """Fetch a snapshot of current financial metrics for a company."""
    params = {"ticker": ticker}
    data = call_api("/financial-metrics/snapshot/", params)
    return data.get("snapshot", {})


def get_financial_metrics(
    ticker: str,
    period: str = "ttm",
    limit: int = 4,
    report_period: Optional[str] = None,
) -> list:
    """Retrieve historical financial metrics for a company."""
    params = {"ticker": ticker, "period": period, "limit": limit}
    if report_period:
        params["report_period"] = report_period
    data = call_api("/financial-metrics/", params)
    return data.get("financial_metrics", [])
