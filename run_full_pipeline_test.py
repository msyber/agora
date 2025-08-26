"""
End-to-end functional test for the core data processing pipeline.

This script verifies the sequential execution of the first three agents that
form the data analysis backbone of Agora:
1.  `DataHarvester` (Intelligence Guild)
2.  `InsightMiner` (Intelligence Guild)
3.  `CausalAnalyst` (Causality Guild)

The test simulates a user query for a stock ticker ("MSFT") and runs the full
pipeline to transform raw data into a structured causal graph. It then verifies
that the final artifact, `MSFT_news_causal_graph.json`, was successfully
created and prints its contents to the console.

This demonstrates the core artifact-passing and state management mechanisms
between agents in a sequential workflow.

Usage:
    python run_full_pipeline_test.py
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

# Import all agents for the full pipeline
from guilds.intelligence.data_harvester.agent import root_agent as data_harvester_agent
from guilds.intelligence.insight_miner.agent import root_agent as insight_miner_agent
from guilds.causality.causal_analyst.agent import root_agent as causal_analyst_agent

# The root_agent for this test is a sequence of all three agents
full_pipeline = SequentialAgent(
    name="full_agora_pipeline",
    sub_agents=[
        data_harvester_agent,
        insight_miner_agent,
        causal_analyst_agent,
    ]
)

async def main():
    print("--- AGORA: Full End-to-End Pipeline Test ---")
    
    app_name = "agora_e2e"
    runner = Runner(
        agent=full_pipeline,
        app_name=app_name,
        session_service=InMemorySessionService(),
        artifact_service=InMemoryArtifactService(),
    )

    session_info = {"app_name": app_name, "user_id": "test_user", "session_id": "session_full"}
    # [CORRECTED] create_session is a synchronous call.
    runner.session_service.create_session(**session_info)

    query = "MSFT"
    user_message = Content(parts=[Part(text=query)])
    
    print(f"\n[RUNNER] Initiating full pipeline for query: '{query}'")
    
    async for event in runner.run_async(
        user_id=session_info["user_id"],
        session_id=session_info["session_id"],
        new_message=user_message
    ):
        if event.content and event.content.parts and event.content.parts[0].text:
            print(f"[EVENT] from '{event.author}': {event.content.parts[0].text.strip()}")
            
    # Verification
    final_artifact_name = f"{query}_news_causal_graph.json"
    print(f"\n[VERIFICATION] Loading final artifact '{final_artifact_name}'...")
    # [CORRECTED] load_artifact is a synchronous call in this context.
    loaded_artifact = runner.artifact_service.load_artifact(
        **session_info, filename=final_artifact_name
    )

    if loaded_artifact:
        print(f"  -> SUCCESS! Loaded final causal graph artifact.")
        graph_data = json.loads(loaded_artifact.inline_data.data.decode('utf-8'))
        print("  -> Causal Graph Content:")
        print(json.dumps(graph_data, indent=2))
    else:
        print(f"  -> FAILURE! Could not load the final causal graph artifact.")

    print("\n--- Test Complete ---")

if __name__ == "__main__":
    asyncio.run(main())