# A simplified, mock representation of our current portfolio and risk limits.
# In a real system, this would be a live connection to a portfolio management database.

MOCK_PORTFOLIO = {
    "cash_usd": 500_000.00,
    "total_value_usd": 1_000_000.00,
    "positions": {
        "GOOGL": {"shares": 100, "notional_usd": 17_500.00, "sector": "TECHNOLOGY"},
        "JPM":   {"shares": 200, "notional_usd": 39_000.00, "sector": "FINANCIALS"}
    },
    "sector_exposure_percent": {
        "TECHNOLOGY": 0.45,  # 45%
        "FINANCIALS": 0.30,  # 30%
        "OTHER": 0.25,       # 25%
    }
}

RISK_LIMITS = {
    "max_position_size_usd": 100_000.00,
    "max_sector_exposure_percent": 0.60, # 60%
}