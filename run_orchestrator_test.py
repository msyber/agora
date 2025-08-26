"""
Functional test for the Intelligence Orchestrator agent.

This script verifies the routing logic of the `IntelligenceOrchestrator`,
which is designed to delegate tasks to different sub-pipelines based on
the content of a user's query.

The test executes two distinct scenarios in isolated sessions:
1.  **News Pipeline Test:** Sends a query containing "news" and "sentiment"
    to ensure the orchestrator routes the request to the `news_pipeline`
    (DataHarvester -> InsightMiner) and successfully generates a
    `_news_insights.json` artifact.
2.  **Filing Pipeline Test:** Sends a query to analyze a "10-K" filing
    to ensure the orchestrator routes the request to the `filing_pipeline`
    (FundamentalAnalyst) and successfully generates a `_raw.txt` artifact.

The script uses a helper function, `run_and_verify`, to encapsulate the
logic of sending a query and checking for the creation of the final expected
artifact, which determines if a test path has passed or failed.

Usage:
    python run_orchestrator_test.py
"""
import asyncio
import json

from google.adk.artifacts import InMemoryArtifactService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.agents import SequentialAgent
from google.genai.types import Content, Part
from dotenv import load_dotenv

load_dotenv()

# Import the orchestrator agent
from guilds.intelligence.orchestrator import root_agent

async def run_and_verify(runner: Runner, session_info: dict, query: str, expected_artifact: str):
    """Helper function to run a query and verify the result."""
    print(f"\n{'='*20}\n[RUNNER] Sending query: '{query}'\n{'='*20}")
    user_message = Content(parts=[Part(text=query)])
    
    # run_async is asynchronous
    async for event in runner.run_async(
        user_id=session_info["user_id"],
        session_id=session_info["session_id"],
        new_message=user_message
    ):
        if event.content and event.content.parts and event.content.parts[0].text:
            print(f"[EVENT] from '{event.author}': {event.content.parts[0].text.strip()}")

    print(f"\n[VERIFICATION] Loading final artifact '{expected_artifact}'...")
    # load_artifact from the service is synchronous in this context
    loaded_artifact = runner.artifact_service.load_artifact(
        app_name=session_info["app_name"],
        user_id=session_info["user_id"],
        session_id=session_info["session_id"],
        filename=expected_artifact
    )

    if loaded_artifact:
        print(f"  -> SUCCESS! Loaded '{expected_artifact}'. Test path PASSED.")
    else:
        print(f"  -> FAILURE! Could not load '{expected_artifact}'. Test path FAILED.")

async def main():
    print("--- AGORA: Intelligence Orchestrator Functional Test ---")
    
    app_name = "agora_intelligence"
    runner = Runner(
        agent=root_agent,
        app_name=app_name,
        session_service=InMemorySessionService(),
        artifact_service=InMemoryArtifactService(),
    )

    # Test Case 1: News Pipeline
    session1_info = {"app_name": app_name, "user_id": "test_user_1", "session_id": "session_news"}
    # [CORRECTED] create_session is synchronous
    runner.session_service.create_session(**session1_info)
    await run_and_verify(
        runner, session1_info, 
        query="Get the latest news and sentiment for MSFT",
        expected_artifact="MSFT_news_insights.json"
    )

    # Test Case 2: Fundamental Analyst Pipeline
    session2_info = {"app_name": app_name, "user_id": "test_user_2", "session_id": "session_filing"}
    # create_session is synchronous
    runner.session_service.create_session(**session2_info)
    await run_and_verify(
        runner, session2_info,
        query="Analyze Item 1A. Risk Factors from the 10-K for NVDA",
        expected_artifact="NVDA_10K_risks_raw.txt"
    )

    print("\n--- Test Complete ---")

if __name__ == "__main__":
    asyncio.run(main())