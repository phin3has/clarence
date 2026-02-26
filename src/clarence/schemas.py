from pydantic import BaseModel, Field
from typing import List, Optional


class Task(BaseModel):
    id: int = Field(..., description="Unique identifier for the task.")
    description: str = Field(..., description="The description of the task.")
    done: bool = Field(False, description="Whether the task is completed.")


class TaskList(BaseModel):
    tasks: List[Task] = Field(..., description="The list of tasks.")


class UserProfile(BaseModel):
    user_id: str
    name: Optional[str] = None
    risk_appetite: str = "medium"
    created_at: str = ""
    updated_at: str = ""
    session_count: int = 0


class DayTradingMetrics(BaseModel):
    symbol: str
    current_price: float
    bid_price: float
    ask_price: float
    spread: float
    spread_percent: float
    volume: int
    avg_volume: int = 0
    volume_ratio: float = 1.0
    volatility: float = 0.0
    gap_percent: float = 0.0


class DayTradingScore(BaseModel):
    symbol: str
    total_score: float
    liquidity_score: float
    spread_score: float
    volatility_score: float
    momentum_score: float
    metrics: DayTradingMetrics
    scoring_explanation: str


class TradeRecommendation(BaseModel):
    symbol: str
    action: str
    quantity: int
    order_type: str = "limit"
    limit_price: Optional[float] = None
    estimated_cost: float
    reasoning: str
    risk_factors: List[str] = Field(default_factory=list)
    score: DayTradingScore


class TradeApproval(BaseModel):
    approved: bool
    symbol: str
    original_quantity: int
    original_price: Optional[float] = None
    modified_quantity: Optional[int] = None
    modified_price: Optional[float] = None

    @property
    def final_quantity(self) -> int:
        return self.modified_quantity if self.modified_quantity is not None else self.original_quantity

    @property
    def final_price(self) -> Optional[float]:
        return self.modified_price if self.modified_price is not None else self.original_price


class OrderResult(BaseModel):
    success: bool
    order_id: Optional[str] = None
    symbol: str
    quantity: int
    side: str
    order_type: str
    status: str
    error: Optional[str] = None
