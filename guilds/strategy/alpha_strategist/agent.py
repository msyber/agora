import json
import logging
from typing import AsyncGenerator

from google.adk.agents import BaseAgent, LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai import types

from .trade_proposal import TradeProposal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

strategist_llm = LlmAgent(
    name="strategist_llm",
    model="gemini-2.5-flash-lite",
    instruction="""
    You are a brilliant and cautious Alpha Strategist for a quantitative fund.
    Your task is to analyze the provided News Insights and Causal Graph to formulate a single, high-conviction trade proposal.

    **News Insights JSON:**
    {insights_content}

    **Causal Graph JSON:**
    {causal_graph_content}

    Based *only* on the evidence provided, generate a single `TradeProposal` JSON object. Your reasoning must explicitly reference the sentiment from the news insights and the links from the causal graph. If the evidence is weak, contradictory, or insufficient, state that in your reasoning and assign a low confidence score.
    """,
    output_schema=TradeProposal,
)

class AlphaStrategist(BaseAgent):
    """
    Orchestrates the creation of a trade proposal by synthesizing evidence
    from the Intelligence and Causality guilds.
    """
    strategist_llm: LlmAgent

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        logger.info(f"[{self.name}] Commencing strategy formulation.")
        try:
            insights_filename = ctx.session.state.get("last_insight_file")
            causal_graph_filename = ctx.session.state.get("last_causal_graph_file")

            if not all([insights_filename, causal_graph_filename, ctx.artifact_service]):
                raise ValueError("Missing prerequisite artifacts or artifact service.")

            # Call load_artifact with explicit keyword arguments.
            insights_artifact = ctx.artifact_service.load_artifact(
                app_name=ctx.app_name,
                user_id=ctx.user_id,
                session_id=ctx.session.id,
                filename=insights_filename
            )
            causal_artifact = ctx.artifact_service.load_artifact(
                app_name=ctx.app_name,
                user_id=ctx.user_id,
                session_id=ctx.session.id,
                filename=causal_graph_filename
            )
            
            insights_content = insights_artifact.inline_data.data.decode('utf-8')
            causal_graph_content = causal_artifact.inline_data.data.decode('utf-8')

            ctx.session.state["insights_content"] = insights_content
            ctx.session.state["causal_graph_content"] = causal_graph_content

            final_response_text = ""
            async for event in self.strategist_llm.run_async(ctx):
                if event.is_final_response() and event.content:
                    final_response_text = event.content.parts[0].text
                yield event

            proposal = TradeProposal.model_validate_json(final_response_text)
            proposal.evidence_artifacts = [insights_filename, causal_graph_filename]
            proposal_json = proposal.model_dump_json(indent=2)
            
            subject = insights_filename.split('_')[0]
            proposal_filename = f"{subject}_trade_proposal.json"

            artifact_part = types.Part.from_bytes(
                data=proposal_json.encode("utf-8"), mime_type="application/json")
            
            version = ctx.artifact_service.save_artifact(
                app_name=ctx.app_name, user_id=ctx.user_id, session_id=ctx.session.id,
                filename=proposal_filename, artifact=artifact_part)
            
            # Pass the filename to the Devil's Advocate
            ctx.session.state["last_proposal_file"] = proposal_filename
            
            final_text = f"Alpha-Strategist created '{proposal_filename}' (v{version})."
            logger.info(f"[{self.name}] {final_text}")

        except Exception as e:
            final_text = f"Alpha-Strategist failed. Error: {e}"
            logger.error(f"[{self.name}] {final_text}", exc_info=True)
        
        yield Event(author=self.name, content=types.Content(parts=[types.Part(text=final_text)]))

root_agent = AlphaStrategist(
    name="alpha_strategist",
    strategist_llm=strategist_llm,
    sub_agents=[strategist_llm]
)