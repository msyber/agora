import asyncio
import datetime
import uuid
from typing import Dict

async def submit_order(trade_order: Dict) -> Dict:
    """
    Mocks the submission of a trade order to a brokerage API.
    
    In a real system, this would involve network requests, authentication,
    and error handling with a real broker like Interactive Brokers or Alpaca.
    """
    ticker = trade_order.get('ticker')
    action = trade_order.get('action')
    quantity = trade_order.get('quantity')
    
    print(f"BROKER API: Submitting order to market -> {action} {quantity} shares of {ticker}.")
    
    # Simulate a successful execution.
    await asyncio.sleep(0.5) # Mock network latency
    
    confirmation = {
        "status": "FILLED",
        "execution_id": str(uuid.uuid4()),
        "timestamp_utc": datetime.datetime.utcnow().isoformat(),
        "filled_quantity": quantity,
        "notes": "Order successfully executed via mock broker API."
    }
    print(f"BROKER API: Received confirmation ID {confirmation['execution_id']}.")
    return confirmation