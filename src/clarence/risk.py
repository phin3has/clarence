from dataclasses import dataclass
from typing import List
from clarence.schemas import DayTradingScore


@dataclass
class RiskParameters:
    max_spread_pct: float
    position_size_min_pct: float
    position_size_max_pct: float
    stop_loss_pct: float
    min_volume: int
    volatility_min: float
    volatility_max: float
    min_score: float


RISK_LEVELS = {
    "low": RiskParameters(
        max_spread_pct=0.10,
        position_size_min_pct=1.0,
        position_size_max_pct=2.0,
        stop_loss_pct=1.0,
        min_volume=1_000_000,
        volatility_min=0.5,
        volatility_max=2.0,
        min_score=70,
    ),
    "medium": RiskParameters(
        max_spread_pct=0.25,
        position_size_min_pct=2.0,
        position_size_max_pct=4.0,
        stop_loss_pct=2.0,
        min_volume=500_000,
        volatility_min=1.0,
        volatility_max=4.0,
        min_score=55,
    ),
    "high": RiskParameters(
        max_spread_pct=0.50,
        position_size_min_pct=3.0,
        position_size_max_pct=5.0,
        stop_loss_pct=3.0,
        min_volume=200_000,
        volatility_min=2.0,
        volatility_max=8.0,
        min_score=40,
    ),
}


def get_risk_parameters(level: str) -> RiskParameters:
    return RISK_LEVELS.get(level, RISK_LEVELS["medium"])


def filter_by_risk(scores: List[DayTradingScore], params: RiskParameters) -> List[DayTradingScore]:
    """Filter scored candidates by risk parameters."""
    filtered = []
    for s in scores:
        m = s.metrics
        if s.total_score < params.min_score:
            continue
        if m.spread_percent > params.max_spread_pct:
            continue
        if m.volume < params.min_volume:
            continue
        filtered.append(s)
    return filtered


def calculate_position_size(buying_power: float, params: RiskParameters, price: float) -> int:
    """Calculate number of shares based on risk parameters and buying power."""
    mid_pct = (params.position_size_min_pct + params.position_size_max_pct) / 2
    dollar_amount = buying_power * (mid_pct / 100)
    if price <= 0:
        return 0
    shares = int(dollar_amount / price)
    return max(shares, 0)


def calculate_stop_loss(entry_price: float, params: RiskParameters) -> float:
    """Calculate stop loss price based on risk parameters."""
    return round(entry_price * (1 - params.stop_loss_pct / 100), 2)
