import asyncio
import json
import logging
from typing import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai.types import Part

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MarketMicrostructureAnalyst(BaseAgent):
    """
    A streaming agent that analyzes real-time Level 2 order book data
    to detect anomalies like wide bid-ask spreads.
    """
    # This method MUST be named _run_live_impl to work with runner.run_live()
    async def _run_live_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """
        Continuously processes incoming data from the live_request_queue.
        """
        logger.info(f"[{self.name}] Live analysis stream started. Waiting for data...")
        
        while True:
            try:
                live_req = await ctx.live_request_queue.get()

                if live_req.blob:
                    order_book = json.loads(live_req.blob.data)
                    
                    best_bid = order_book["bids"][0]["price"]
                    best_ask = order_book["asks"][0]["price"]
                    spread = best_ask - best_bid
                    
                    logger.info(
                        f"[{self.name}] Tick received for {order_book['ticker']}: "
                        f"Spread = {spread:.2f}"
                    )

                    if spread > 0.15:
                        alert_message = (
                            f"ALERT: Wide spread detected for {order_book['ticker']}: "
                            f"{spread:.2f} at {order_book['timestamp_utc']}"
                        )
                        logger.warning(f"[{self.name}] {alert_message}")
                        yield Event(
                            author=self.name,
                            content={"parts": [Part(text=alert_message)]}
                        )

            except asyncio.CancelledError:
                logger.info(f"[{self.name}] Live stream cancelled. Shutting down.")
                break
            except Exception as e:
                logger.error(f"[{self.name}] Error in live stream: {e}")

root_agent = MarketMicrostructureAnalyst(name="market_microstructure_analyst")