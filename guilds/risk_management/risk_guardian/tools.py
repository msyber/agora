from typing import Dict
from .portfolio_state import MOCK_PORTFOLIO, RISK_LIMITS

def get_current_price(ticker: str) -> float:
    """Mocks fetching the current market price for a ticker."""
    # In a real system, this would call a live market data API.
    price_map = {"MSFT": 350.00, "GOOGL": 175.00, "NVDA": 900.00}
    return price_map.get(ticker, 200.00) # Default price for simplicity

def check_position_size(notional_value: float) -> Dict:
    """Checks if a proposed trade's value exceeds the max position size."""
    print(f"TOOL EXECUTING: check_position_size(notional_value={notional_value})")
    limit = RISK_LIMITS["max_position_size_usd"]
    if notional_value > limit:
        return {"pass": False, "reason": f"Trade value ${notional_value:,.2f} exceeds max position limit of ${limit:,.2f}."}
    return {"pass": True}

def check_sector_exposure(ticker: str, notional_value: float) -> Dict:
    """Checks if adding the proposed trade would breach sector concentration limits."""
    print(f"TOOL EXECUTING: check_sector_exposure(ticker={ticker})")
    # Mock sector lookup
    sector_map = {"MSFT": "TECHNOLOGY", "GOOGL": "TECHNOLOGY", "NVDA": "TECHNOLOGY"}
    sector = sector_map.get(ticker, "OTHER")
    
    current_sector_value = MOCK_PORTFOLIO["sector_exposure_percent"].get(sector, 0.0) * MOCK_PORTFOLIO["total_value_usd"]
    new_total_value = MOCK_PORTFOLIO["total_value_usd"] + notional_value
    new_sector_exposure = (current_sector_value + notional_value) / new_total_value
    
    limit = RISK_LIMITS["max_sector_exposure_percent"]
    if new_sector_exposure > limit:
        return {"pass": False, "reason": f"Proposed trade increases {sector} exposure to {new_sector_exposure:.2%} which exceeds the limit of {limit:.2%}"}
    return {"pass": True}