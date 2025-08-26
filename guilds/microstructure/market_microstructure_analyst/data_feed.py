import asyncio
import datetime
import json
import random
from typing import AsyncGenerator

async def mock_l2_feed(ticker: str) -> AsyncGenerator[str, None]:
    """
    An asynchronous generator that simulates a real-time Level 2 market data feed.
    It yields a new JSON-formatted order book snapshot every second.
    """
    base_price = 150.00
    while True:
        # Simulate slight price fluctuations
        bid_price = base_price - random.uniform(0.01, 0.05)
        ask_price = base_price + random.uniform(0.01, 0.05)
        
        # Introduce an occasional anomaly (wide spread)
        if random.random() < 0.1: # 10% chance of an anomaly
            ask_price += 0.20 

        order_book_snapshot = {
            "ticker": ticker,
            "timestamp_utc": datetime.datetime.utcnow().isoformat(),
            "bids": [
                {"price": round(bid_price, 2), "size": random.randint(10, 50)},
                {"price": round(bid_price - 0.01, 2), "size": random.randint(50, 100)},
            ],
            "asks": [
                {"price": round(ask_price, 2), "size": random.randint(10, 50)},
                {"price": round(ask_price + 0.01, 2), "size": random.randint(50, 100)},
            ],
        }
        yield json.dumps(order_book_snapshot)
        await asyncio.sleep(1) # Wait 1 second before the next update