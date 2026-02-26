"""
Day Trading Scoring System for Clarence.

This module evaluates stocks for day trading suitability based on four key factors:
1. Liquidity (volume) - Can you get in and out easily?
2. Spread (bid-ask tightness) - How much will you lose to slippage?
3. Volatility (intraday range) - Is there enough movement to profit?
4. Momentum (gap from previous close) - Is there a catalyst driving the move?

Each factor is scored 0-25, for a total possible score of 0-100.
"""

from typing import Tuple
from clarence.schemas import DayTradingMetrics, DayTradingScore


def calculate_liquidity_score(volume: int, avg_volume: int) -> Tuple[float, str]:
    """
    Calculate liquidity score based on volume ratio (today's volume / avg volume).

    Higher volume = easier entry/exit, tighter spreads, less slippage.

    Scoring:
        > 2.0x average  = 25 points (exceptional - lots of interest)
        1.5x - 2.0x     = 20 points (excellent)
        1.0x - 1.5x     = 15 points (good - normal trading)
        0.5x - 1.0x     = 10 points (moderate - below average)
        < 0.5x          = 5 points  (low - harder to trade)

    Args:
        volume: Today's trading volume
        avg_volume: Average daily volume (typically 20-day)

    Returns:
        Tuple of (score, explanation)
    """
    if avg_volume == 0:
        return 10.0, "No average volume data available"

    ratio = volume / avg_volume

    if ratio > 2.0:
        return 25.0, f"Exceptional volume ({ratio:.1f}x average) - high interest today"
    elif ratio >= 1.5:
        return 20.0, f"Excellent volume ({ratio:.1f}x average) - above normal trading"
    elif ratio >= 1.0:
        return 15.0, f"Good volume ({ratio:.1f}x average) - normal trading activity"
    elif ratio >= 0.5:
        return 10.0, f"Moderate volume ({ratio:.1f}x average) - below average interest"
    else:
        return 5.0, f"Low volume ({ratio:.1f}x average) - may be harder to enter/exit"


def calculate_spread_score(spread_percent: float) -> Tuple[float, str]:
    """
    Calculate spread score based on bid-ask spread as percentage of price.

    Tighter spread = less money lost to slippage when entering/exiting.

    Scoring:
        < 0.05%     = 25 points (excellent - ~$0.01 on a $20 stock)
        0.05-0.10%  = 20 points (good)
        0.10-0.20%  = 15 points (acceptable)
        0.20-0.50%  = 10 points (wide - be careful)
        > 0.50%     = 5 points  (very wide - high slippage risk)

    Args:
        spread_percent: Bid-ask spread as percentage of current price

    Returns:
        Tuple of (score, explanation)
    """
    if spread_percent < 0.05:
        return 25.0, f"Excellent spread ({spread_percent:.3f}%) - minimal slippage"
    elif spread_percent < 0.10:
        return 20.0, f"Good spread ({spread_percent:.3f}%) - acceptable for day trading"
    elif spread_percent < 0.20:
        return 15.0, f"Moderate spread ({spread_percent:.3f}%) - watch entry/exit carefully"
    elif spread_percent < 0.50:
        return 10.0, f"Wide spread ({spread_percent:.3f}%) - significant slippage risk"
    else:
        return 5.0, f"Very wide spread ({spread_percent:.3f}%) - high cost to trade"


def calculate_volatility_score(volatility_percent: float) -> Tuple[float, str]:
    """
    Calculate volatility score based on intraday price range as % of open.

    Ideal volatility: enough movement to profit, but not so much it's dangerous.

    Scoring:
        2-4%        = 25 points (ideal for day trading)
        1-2% or 4-6% = 20 points (good - workable range)
        0.5-1% or 6-8% = 15 points (moderate)
        < 0.5%      = 10 points (too slow - hard to profit)
        > 8%        = 5 points  (too volatile - high risk)

    Args:
        volatility_percent: (high - low) / open * 100

    Returns:
        Tuple of (score, explanation)
    """
    if 2.0 <= volatility_percent <= 4.0:
        return 25.0, f"Ideal volatility ({volatility_percent:.1f}%) - good movement for day trading"
    elif (1.0 <= volatility_percent < 2.0) or (4.0 < volatility_percent <= 6.0):
        return 20.0, f"Good volatility ({volatility_percent:.1f}%) - workable for day trading"
    elif (0.5 <= volatility_percent < 1.0) or (6.0 < volatility_percent <= 8.0):
        return 15.0, f"Moderate volatility ({volatility_percent:.1f}%) - proceed with caution"
    elif volatility_percent < 0.5:
        return 10.0, f"Low volatility ({volatility_percent:.1f}%) - limited profit potential"
    else:
        return 5.0, f"High volatility ({volatility_percent:.1f}%) - elevated risk"


def calculate_momentum_score(gap_percent: float) -> Tuple[float, str]:
    """
    Calculate momentum score based on gap from previous close.

    A gap indicates a catalyst (news, earnings, etc.) driving interest.

    Scoring:
        1-3% gap    = 25 points (ideal - clear catalyst, not overdone)
        0.5-1% or 3-5% = 20 points (good)
        < 0.5%      = 15 points (neutral - no clear catalyst)
        > 5%        = 10 points (extended - reversal risk)

    Args:
        gap_percent: (open - previous_close) / previous_close * 100 (absolute value)

    Returns:
        Tuple of (score, explanation)
    """
    abs_gap = abs(gap_percent)
    direction = "up" if gap_percent >= 0 else "down"

    if 1.0 <= abs_gap <= 3.0:
        return 25.0, f"Ideal gap ({gap_percent:+.1f}% {direction}) - clear catalyst, not overdone"
    elif (0.5 <= abs_gap < 1.0) or (3.0 < abs_gap <= 5.0):
        return 20.0, f"Good gap ({gap_percent:+.1f}% {direction}) - momentum present"
    elif abs_gap < 0.5:
        return 15.0, f"Small gap ({gap_percent:+.1f}%) - no clear catalyst today"
    else:
        return 10.0, f"Large gap ({gap_percent:+.1f}% {direction}) - may be extended, watch for reversal"


def calculate_day_trading_score(metrics: DayTradingMetrics) -> DayTradingScore:
    """
    Calculate a comprehensive day trading suitability score for a stock.

    Combines four factors:
    - Liquidity (volume ratio): 0-25 points
    - Spread (bid-ask tightness): 0-25 points
    - Volatility (intraday range): 0-25 points
    - Momentum (gap from close): 0-25 points

    Total: 0-100 points

    Score interpretation:
    - 80-100: Excellent day trading candidate
    - 60-79: Good candidate, proceed carefully
    - 40-59: Marginal, consider other options
    - 0-39: Not recommended for day trading

    Args:
        metrics: DayTradingMetrics with raw stock data

    Returns:
        DayTradingScore with all component scores and explanations
    """
    # Calculate each component score
    liquidity_score, liquidity_exp = calculate_liquidity_score(
        metrics.volume, metrics.avg_volume
    )
    spread_score, spread_exp = calculate_spread_score(metrics.spread_percent)
    volatility_score, volatility_exp = calculate_volatility_score(metrics.volatility)
    momentum_score, momentum_exp = calculate_momentum_score(metrics.gap_percent)

    # Calculate total
    total_score = liquidity_score + spread_score + volatility_score + momentum_score

    # Build explanation
    explanations = [
        f"Liquidity: {liquidity_exp}",
        f"Spread: {spread_exp}",
        f"Volatility: {volatility_exp}",
        f"Momentum: {momentum_exp}"
    ]

    # Overall assessment
    if total_score >= 80:
        overall = "Excellent day trading candidate"
    elif total_score >= 60:
        overall = "Good candidate with some caution"
    elif total_score >= 40:
        overall = "Marginal - consider other options"
    else:
        overall = "Not recommended for day trading"

    scoring_explanation = f"{overall}. " + " | ".join(explanations)

    return DayTradingScore(
        symbol=metrics.symbol,
        total_score=total_score,
        liquidity_score=liquidity_score,
        spread_score=spread_score,
        volatility_score=volatility_score,
        momentum_score=momentum_score,
        metrics=metrics,
        scoring_explanation=scoring_explanation
    )


def format_score_breakdown(score: DayTradingScore) -> str:
    """
    Format a score breakdown for display to the user.

    Args:
        score: DayTradingScore to format

    Returns:
        Formatted string with score breakdown
    """
    return f"""Day Trading Score: {score.total_score:.0f}/100
  - Liquidity:  {score.liquidity_score:.0f}/25 (volume {score.metrics.volume_ratio:.1f}x average)
  - Spread:     {score.spread_score:.0f}/25 ({score.metrics.spread_percent:.3f}% spread)
  - Volatility: {score.volatility_score:.0f}/25 ({score.metrics.volatility:.1f}% intraday range)
  - Momentum:   {score.momentum_score:.0f}/25 ({score.metrics.gap_percent:+.1f}% gap)"""
