"""
Functional test for the final execution pipeline (Risk & Execution Guilds).

This script verifies the sequential execution of the final two agents in the
AGORA framework:
1.  `RiskGuardian` (Risk Management Guild)
2.  `ExecutionAgent` (Execution Guild)

The test simulates a scenario where a trade proposal has already been debated
and approved by the `AuditorAgent`. It works by:
1.  Using a `setup_prerequisites` helper function to create mock "approved"
    audit and trade proposal artifacts.
2.  Initializing the agent session with state pointing to these mock artifacts.
3.  Running the `execution_pipeline` which first checks the proposal against
    risk limits and then "executes" it via a mock broker API.
4.  Verifying that the final `_trade_confirmation.json` artifact was
    successfully created.

This demonstrates the final handoff from risk management to trade execution.

Usage:
    python run_execution_test.py
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

from guilds.risk_management.risk_guardian.agent import root_agent as risk_guardian_agent
from guilds.execution.execution_agent.agent import root_agent as execution_agent

# For this test, we run the final two-agent pipeline
execution_pipeline = SequentialAgent(
    name="execution_pipeline",
    sub_agents=[risk_guardian_agent, execution_agent]
)

async def setup_prerequisites(runner, session_info, query) -> dict:
    """Creates mock prerequisite artifacts and returns the required initial state."""
    print("[SETUP] Creating mock prerequisite artifacts...")
    
    # Mock an APPROVED audit verdict
    audit_data = {"decision": "APPROVE", "reasoning": "Mocked for execution test."}
    audit_filename = f"{query}_trade_audit.json"
    audit_part = Part.from_bytes(data=json.dumps(audit_data).encode('utf-8'), mime_type="application/json")
    runner.artifact_service.save_artifact(**session_info, filename=audit_filename, artifact=audit_part)
    
    # Mock a trade proposal
    proposal_data = {"ticker": query, "action": "BUY", "confidence_score": 0.9}
    proposal_filename = f"{query}_trade_proposal.json"
    proposal_part = Part.from_bytes(data=json.dumps(proposal_data).encode('utf-8'), mime_type="application/json")
    runner.artifact_service.save_artifact(**session_info, filename=proposal_filename, artifact=proposal_part)
    
    print("[SETUP] Mock artifacts created successfully.")
    
    return {
        "last_audit_file": audit_filename,
        "last_proposal_file": proposal_filename
    }

async def main():
    print("--- AGORA: Execution Pipeline Test ---")
    
    app_name = "agora_execution"
    runner = Runner(
        agent=execution_pipeline, app_name=app_name,
        session_service=InMemorySessionService(), artifact_service=InMemoryArtifactService()
    )
    session_info = {"app_name": app_name, "user_id": "test_user", "session_id": "session_exec"}
    query = "MSFT"
    
    initial_state = await setup_prerequisites(runner, session_info, query)
    
    # Create_session is a synchronous call.
    runner.session_service.create_session(**session_info, state=initial_state)
    
    user_message = Content(parts=[Part(text=f"Execute approved trade for {query}")])
    
    print(f"\n[RUNNER] Initiating execution pipeline for query: '{query}'")
    async for event in runner.run_async(
        user_id=session_info["user_id"],
        session_id=session_info["session_id"],
        new_message=user_message
    ):
        if event.content and event.content.parts and event.content.parts[0].text:
            print(f"[EVENT] from '{event.author}': {event.content.parts[0].text.strip()}")
            
    final_artifact_name = f"{query}_trade_confirmation.json"
    print(f"\n[VERIFICATION] Loading final artifact '{final_artifact_name}'...")
    loaded_artifact = runner.artifact_service.load_artifact(
        **session_info, filename=final_artifact_name)
    if loaded_artifact:
        print(f"  -> SUCCESS! Loaded final trade confirmation artifact.")
        confirm_data = json.loads(loaded_artifact.inline_data.data.decode('utf-8'))
        print("  -> Execution Confirmation Content:")
        print(json.dumps(confirm_data, indent=2))
    else:
        print(f"  -> FAILURE! Could not load the final trade confirmation artifact.")
    print("\n--- Test Complete ---")

if __name__ == "__main__":
    asyncio.run(main())