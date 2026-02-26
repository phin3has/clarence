"""Local tools that are NOT exposed to the LLM but used by the scanner."""

import os
from alpaca.data.enums import MostActivesBy
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.historical.screener import ScreenerClient
from alpaca.data.timeframe import TimeFrame

from clarence.tools.finance.news import get_news
from clarence.tools.finance.metrics import get_financial_metrics_snapshot, get_financial_metrics


def _get_screener_client() -> ScreenerClient:
    return ScreenerClient(
        api_key=os.getenv("ALPACA_API_KEY", ""),
        secret_key=os.getenv("ALPACA_SECRET_KEY", ""),
    )


def _get_data_client() -> StockHistoricalDataClient:
    return StockHistoricalDataClient(
        api_key=os.getenv("ALPACA_API_KEY", ""),
        secret_key=os.getenv("ALPACA_SECRET_KEY", ""),
    )


def get_stock_quote(symbol: str) -> dict:
    """Fetch latest bid/ask quote for a symbol via alpaca-py."""
    try:
        from alpaca.data.requests import StockLatestQuoteRequest
        client = _get_data_client()
        result = client.get_stock_latest_quote(StockLatestQuoteRequest(symbol_or_symbols=symbol))
        quote = result.get(symbol)
        if not quote:
            return {}
        return {
            "bid_price": float(quote.bid_price or 0),
            "ask_price": float(quote.ask_price or 0),
        }
    except Exception as e:
        return {"error": str(e)}


def get_stock_bars_data(symbol: str, limit: int = 5) -> list[dict]:
    """Fetch recent daily bars for a symbol via alpaca-py."""
    try:
        from alpaca.data.requests import StockBarsRequest
        client = _get_data_client()
        result = client.get_stock_bars(StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Day,
            limit=limit,
        ))
        bars = result.data.get(symbol, [])
        return [
            {
                "open": float(b.open),
                "high": float(b.high),
                "low": float(b.low),
                "close": float(b.close),
                "volume": int(b.volume),
            }
            for b in bars
        ]
    except Exception as e:
        return [{"error": str(e)}]


def get_most_active_stocks(top: int = 20) -> list[dict]:
    """Use Alpaca screener to find most active stocks by volume."""
    try:
        from alpaca.data.requests import MostActivesRequest
        client = _get_screener_client()
        request = MostActivesRequest(top=top, by=MostActivesBy.VOLUME)
        result = client.get_most_actives(request)
        actives = []
        for item in result.most_actives:
            actives.append({
                "symbol": item.symbol,
                "volume": item.volume,
                "trade_count": item.trade_count,
            })
        return actives
    except Exception as e:
        return [{"error": str(e)}]


def get_top_movers(top: int = 20, market_type: str = "stocks") -> list[dict]:
    """Use Alpaca screener to find top market movers."""
    try:
        from alpaca.data.requests import MarketMoversRequest
        client = _get_screener_client()
        request = MarketMoversRequest(top=top, market_type=market_type)
        result = client.get_market_movers(request)
        movers = []
        for item in result.gainers:
            movers.append({
                "symbol": item.symbol,
                "percent_change": item.percent_change,
                "change": item.change,
                "price": item.price,
                "direction": "gainer",
            })
        for item in result.losers:
            movers.append({
                "symbol": item.symbol,
                "percent_change": item.percent_change,
                "change": item.change,
                "price": item.price,
                "direction": "loser",
            })
        return movers
    except Exception as e:
        return [{"error": str(e)}]
