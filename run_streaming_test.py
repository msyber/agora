"""
Functional test for the real-time streaming agent (`MarketMicrostructureAnalyst`).

This script simulates a live market data environment to test the agent's ability
to process a continuous stream of information and generate alerts for anomalies.

It orchestrates two concurrent asynchronous tasks:
1.  `produce_market_data`: Simulates a Level 2 order book feed, sending new
    JSON data to the agent every second. It occasionally introduces a wide
    bid-ask spread to trigger an alert.
2.  `consume_agent_events`: Listens for events coming from the agent and prints
    any alerts to the console.

The test runs for a fixed duration (10 seconds) and then gracefully shuts down
the producer and consumer tasks.

Usage:
    python run_streaming_test.py
"""
import asyncio
import json

from google.adk.agents import LiveRequestQueue
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Blob

# Import the agent and the mock data feed
from guilds.microstructure.market_microstructure_analyst.agent import root_agent
from guilds.microstructure.market_microstructure_analyst.data_feed import mock_l2_feed


async def consume_agent_events(live_events):
    """Async task to listen for and print events from the agent."""
    print("[CONSUMER] Started listening for agent alerts.")
    async for event in live_events:
        if event.content and event.content.parts and event.content.parts[0].text:
            print(f"\n>>> AGENT ALERT RECEIVED: {event.content.parts[0].text}\n")
    print("[CONSUMER] Event stream closed.")


async def produce_market_data(live_request_queue):
    """Async task to generate and send market data to the agent."""
    print("[PRODUCER] Started generating real-time market data.")
    async for order_book_json in mock_l2_feed(ticker="AGORA"):
        data_blob = Blob(
            data=order_book_json.encode("utf-8"), mime_type="application/json"
        )
        live_request_queue.send_realtime(data_blob)
    print("[PRODUCER] Data feed stopped.")


async def main():
    print("--- AGORA: Microstructure Guild Streaming Test ---")

    runner = Runner(
        agent=root_agent,
        app_name="agora_microstructure",
        session_service=InMemorySessionService(),
    )
    session = runner.session_service.create_session(
        app_name="agora_microstructure", user_id="test_user", session_id="live_session_1"
    )
    
    live_request_queue = LiveRequestQueue()
    run_config = RunConfig(streaming_mode=StreamingMode.BIDI)

    # [CORRECTED] The run_live method requires the 'session' object directly.
    live_events = runner.run_live(
        session=session,
        live_request_queue=live_request_queue,
        run_config=run_config
    )

    consumer_task = asyncio.create_task(consume_agent_events(live_events))
    producer_task = asyncio.create_task(produce_market_data(live_request_queue))
    
    run_duration = 10
    print(f"\n[RUNNER] Running streaming simulation for {run_duration} seconds...")
    await asyncio.sleep(run_duration)

    print("\n[RUNNER] Stopping simulation...")
    producer_task.cancel()
    live_request_queue.close()
    
    await asyncio.gather(consumer_task, producer_task, return_exceptions=True)
    
    print("\n--- Test Complete ---")


if __name__ == "__main__":
    asyncio.run(main())