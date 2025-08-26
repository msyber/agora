from pydantic import BaseModel, Field

class TradeOrder(BaseModel):
    """
    A final, risk-checked order ready for execution.
    """
    ticker: str
    action: str = Field(description="BUY or SELL")
    quantity: int = Field(description="Number of shares")
    order_type: str = Field(description="e.g., MARKET, LIMIT", default="MARKET")
    notional_value_usd: float 