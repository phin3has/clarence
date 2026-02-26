import json
from typing import List

from clarence.mcp_client import AlpacaMCPClient
from clarence.model import call_llm, call_llm_stream
from clarence.prompts import SCANNING_PROMPT, OPPORTUNITY_PROMPT
from clarence.risk import RiskParameters, filter_by_risk, calculate_position_size, calculate_stop_loss
from clarence.schemas import DayTradingMetrics, DayTradingScore, TradeRecommendation
from clarence.tools import get_most_active_stocks, get_top_movers, get_stock_quote, get_stock_bars_data
from clarence.utils.scoring import calculate_day_trading_score, format_score_breakdown
from clarence.utils.logger import Logger


class OpportunityScanner:
    """Scans the market for day trading opportunities filtered by risk appetite."""

    def __init__(self, mcp: AlpacaMCPClient, risk_params: RiskParameters, logger: Logger):
        self.mcp = mcp
        self.risk_params = risk_params
        self.logger = logger

    async def scan(self) -> List[TradeRecommendation]:
        """Run the full scan pipeline: discover → score → filter → recommend."""
        # 1. Get account info
        account_text = await self.mcp.call_tool("get_account_info", {})
        try:
            account = json.loads(account_text)
        except json.JSONDecodeError:
            # MCP server returns a human-readable formatted string, not JSON —
            # parse "Key: $value" lines into a dict.
            account = _parse_account_text(account_text)

        if "error" in account:
            self.logger._log(f"  ! Account error: {account['error']}")

        buying_power = float(account.get("buying_power", 0))
        self.logger._log(f"Buying power: ${buying_power:,.2f}")

        # 2. Get current positions
        positions_text = await self.mcp.call_tool("get_all_positions", {})
        try:
            positions = json.loads(positions_text)
        except json.JSONDecodeError:
            positions = []

        held_symbols = set()
        positions_summary = "None"
        if positions and isinstance(positions, list):
            held_symbols = {p.get("symbol", "") for p in positions}
            lines = []
            for p in positions:
                sym = p.get("symbol", "?")
                qty = p.get("qty", 0)
                pnl = p.get("unrealized_pl", 0)
                lines.append(f"  {sym}: {qty} shares (P&L: ${float(pnl):+,.2f})")
            positions_summary = "\n".join(lines) if lines else "None"

        # 3. Get candidate symbols from screener
        with self.logger.progress("Scanning market for opportunities..."):
            actives = get_most_active_stocks(top=20)
            movers = get_top_movers(top=20)

        # Surface any screener errors before filtering
        for item in actives:
            if "error" in item:
                self.logger._log(f"  ! Screener (actives) error: {item['error']}")
        for item in movers:
            if "error" in item:
                self.logger._log(f"  ! Screener (movers) error: {item['error']}")

        candidates = set()
        for item in actives:
            sym = item.get("symbol", "")
            if sym and "error" not in item and not _is_warrant_or_unit(sym):
                candidates.add(sym)
        for item in movers:
            sym = item.get("symbol", "")
            if sym and "error" not in item and not _is_warrant_or_unit(sym):
                candidates.add(sym)

        candidates -= held_symbols
        self.logger._log(f"Found {len(candidates)} candidate symbols")

        if not candidates:
            self.logger._log("No candidates found.")
            return []

        # 4. Fetch metrics and score candidates via MCP
        scores: List[DayTradingScore] = []
        with self.logger.progress("Scoring candidates..."):
            for symbol in list(candidates)[:15]:  # Cap to avoid too many API calls
                metrics = await self._fetch_metrics(symbol)
                if metrics:
                    s = calculate_day_trading_score(metrics)
                    scores.append(s)

        scores.sort(key=lambda s: s.total_score, reverse=True)

        self.logger._log(f"Scored {len(scores)} symbols:")
        for s in scores:
            m = s.metrics
            self.logger._log(
                f"  {s.symbol}: score={s.total_score:.0f} | "
                f"spread={m.spread_percent:.3f}% | "
                f"vol={m.volume:,} | "
                f"vol_ratio={m.volume_ratio:.1f}x | "
                f"volatility={m.volatility:.1f}%"
            )

        # 5. Filter by risk
        filtered = filter_by_risk(scores, self.risk_params)
        self.logger._log(f"{len(filtered)} candidates passed risk filter (min score: {self.risk_params.min_score})")

        if not filtered:
            if scores:
                best = scores[0]
                m = best.metrics
                reasons = []
                if best.total_score < self.risk_params.min_score:
                    reasons.append(f"score {best.total_score:.0f} < min {self.risk_params.min_score}")
                if m.spread_percent > self.risk_params.max_spread_pct:
                    reasons.append(f"spread {m.spread_percent:.3f}% > max {self.risk_params.max_spread_pct}%")
                if m.volume < self.risk_params.min_volume:
                    reasons.append(f"volume {m.volume:,} < min {self.risk_params.min_volume:,}")
                self.logger._log(
                    f"No candidates passed risk filters. "
                    f"Best was {best.symbol} ({', '.join(reasons) if reasons else 'unknown reason'})."
                )
            else:
                self.logger._log("No candidates passed risk filters.")
            return []

        # 6. Generate recommendations via LLM
        scored_text = "\n".join([
            f"{s.symbol}: score={s.total_score:.0f} | "
            f"vol_ratio={s.metrics.volume_ratio:.1f}x | "
            f"spread={s.metrics.spread_percent:.3f}% | "
            f"volatility={s.metrics.volatility:.1f}% | "
            f"gap={s.metrics.gap_percent:+.1f}% | "
            f"price=${s.metrics.current_price:.2f}"
            for s in filtered[:8]
        ])

        prompt = SCANNING_PROMPT.format(
            risk_level=_risk_label(self.risk_params),
            buying_power=buying_power,
            stop_loss_pct=self.risk_params.stop_loss_pct,
            pos_size_min=self.risk_params.position_size_min_pct,
            pos_size_max=self.risk_params.position_size_max_pct,
            positions_summary=positions_summary,
            scored_candidates=scored_text,
        )

        with self.logger.progress("Generating recommendations..."):
            response = await call_llm(
                messages=[{"role": "user", "content": prompt}],
                system="You are a trading analysis engine. Return only valid JSON.",
            )

        # Parse recommendations
        text = ""
        for block in response.content:
            if hasattr(block, "text"):
                text += block.text

        recommendations = self._parse_recommendations(text, filtered)
        return recommendations

    async def present_opportunity(self, rec: TradeRecommendation):
        """Stream a recommendation presentation to the user."""
        prompt = OPPORTUNITY_PROMPT.format(recommendation_json=rec.model_dump_json(indent=2))
        stream = call_llm_stream(
            messages=[{"role": "user", "content": prompt}],
            system="You are Clarence, a day trading execution agent. Present concisely.",
        )
        text = await self.logger.ui.async_stream_answer(stream)
        return text

    async def execute_trade(self, rec: TradeRecommendation, quantity: int, price: float | None):
        """Place an order via MCP."""
        args = {
            "symbol": rec.symbol,
            "side": rec.action,
            "type": rec.order_type,
            "quantity": str(quantity),
            "time_in_force": "day",
        }
        if price and rec.order_type == "limit":
            args["limit_price"] = str(price)

        result_text = await self.mcp.call_tool("place_stock_order", args)
        return result_text

    async def _fetch_metrics(self, symbol: str) -> DayTradingMetrics | None:
        """Fetch quote and bars via alpaca-py, build DayTradingMetrics."""
        try:
            quote = get_stock_quote(symbol)
            if "error" in quote:
                self.logger._log(f"  ! {symbol}: quote error: {quote['error']}")
                return None

            bid = float(quote.get("bid_price", 0))
            ask = float(quote.get("ask_price", 0))
            mid = (bid + ask) / 2 if (bid and ask) else 0
            spread = ask - bid if (bid and ask) else 0
            spread_pct = (spread / mid * 100) if mid else 0

            bar_list = get_stock_bars_data(symbol, limit=5)
            if bar_list and "error" in bar_list[0]:
                self.logger._log(f"  ! {symbol}: bars error: {bar_list[0]['error']}")
                return None

            volume = 0
            avg_volume = 0
            volatility = 0.0
            gap_pct = 0.0

            if bar_list:
                latest = bar_list[-1]
                volume = int(latest.get("volume", 0))
                open_price = float(latest.get("open", mid))
                high = float(latest.get("high", mid))
                low = float(latest.get("low", mid))

                if open_price > 0:
                    volatility = (high - low) / open_price * 100

                if len(bar_list) > 1:
                    volumes = [int(b.get("volume", 0)) for b in bar_list[:-1]]
                    avg_volume = sum(volumes) // len(volumes) if volumes else volume
                    prev_close = float(bar_list[-2].get("close", mid))
                    if prev_close > 0:
                        gap_pct = (open_price - prev_close) / prev_close * 100

            vol_ratio = volume / avg_volume if avg_volume > 0 else 1.0

            return DayTradingMetrics(
                symbol=symbol,
                current_price=mid,
                bid_price=bid,
                ask_price=ask,
                spread=spread,
                spread_percent=spread_pct,
                volume=volume,
                avg_volume=avg_volume,
                volume_ratio=vol_ratio,
                volatility=volatility,
                gap_percent=gap_pct,
            )
        except Exception as e:
            self.logger._log(f"  ! {symbol}: metrics fetch failed ({type(e).__name__}: {e})")
            return None

    def _parse_recommendations(self, text: str, scores: List[DayTradingScore]) -> List[TradeRecommendation]:
        """Parse LLM JSON response into TradeRecommendation objects."""
        score_map = {s.symbol: s for s in scores}
        try:
            # Extract JSON from response
            start = text.find("{")
            end = text.rfind("}") + 1
            if start < 0 or end <= 0:
                self.logger._log(f"! LLM returned no JSON. Raw response:\n{text[:500]}")
                return []
            data = json.loads(text[start:end])
            recs = []
            for r in data.get("recommendations", []):
                symbol = r.get("symbol", "")
                score = score_map.get(symbol)
                if not score:
                    continue
                recs.append(TradeRecommendation(
                    symbol=symbol,
                    action=r.get("action", "buy"),
                    quantity=int(r.get("quantity", 0)),
                    order_type=r.get("order_type", "limit"),
                    limit_price=r.get("limit_price"),
                    estimated_cost=float(r.get("estimated_cost", 0)),
                    reasoning=r.get("reasoning", ""),
                    risk_factors=r.get("risk_factors", []),
                    score=score,
                ))
            return recs
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            self.logger._log(f"! Failed to parse LLM recommendations ({type(e).__name__}): {e}")
            self.logger._log(f"  Raw LLM response:\n{text[:500]}")
            return []


def _parse_account_text(text: str) -> dict:
    """Parse the MCP server's human-readable account format into a dict.

    Converts lines like "Buying Power: $499.75" into {"buying_power": "499.75"}.
    """
    result = {}
    for line in text.splitlines():
        line = line.strip()
        if ":" not in line or line.startswith("-"):
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower().replace(" ", "_")
        value = value.strip().lstrip("$").replace(",", "")
        if key and value:
            result[key] = value
    return result


def _is_warrant_or_unit(symbol: str) -> bool:
    """Filter out warrants, units, and rights.

    SPAC warrants/units are 5+ chars ending in W, U, or R (e.g. ACAMW, IPAXU).
    Four-char tickers ending in those letters are regular stocks (e.g. CRWD, UBER).
    """
    if "+" in symbol:
        return True
    if len(symbol) >= 5 and symbol[-1] in ("W", "U", "R"):
        return True
    return False


def _risk_label(params: RiskParameters) -> str:
    from clarence.risk import RISK_LEVELS
    for name, p in RISK_LEVELS.items():
        if p is params:
            return name
    return "medium"
