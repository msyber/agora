import json
import logging
from typing import AsyncGenerator

from google.adk.agents import BaseAgent, LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai import types

from .trade_critique import TradeCritique

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# The internal "critic" LLM, now using a Claude model hosted on Vertex AI.
# The ADK will handle this via the registered Claude wrapper.
critic_llm = LlmAgent(
    name="critic_llm",
    model="gemini-2.5-flash-lite",
    instruction="""
    You are a skeptical and highly analytical risk manager for a quantitative fund.
    Your sole purpose is to find flaws in the following trade proposal.
    Analyze the reasoning for logical fallacies, unstated assumptions, and unaccounted-for risks.
    Be ruthlessly objective. Your critique must be structured as a valid JSON object
    that conforms to the required schema.

    **Trade Proposal to Critique:**
    {proposal_content}
    """,
    output_schema=TradeCritique,
)

class DevilsAdvocate(BaseAgent):
    critic_llm: LlmAgent
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        logger.info(f"[{self.name}] Commencing adversarial review.")
        try:
            proposal_filename = ctx.session.state.get("last_proposal_file")
            if not proposal_filename or not ctx.artifact_service:
                raise ValueError("Proposal artifact or service not available.")

            proposal_artifact = await ctx.artifact_service.load_artifact(
                app_name=ctx.app_name, user_id=ctx.user_id,
                session_id=ctx.session.id, filename=proposal_filename)
            proposal_content = proposal_artifact.inline_data.data.decode('utf-8')
            
            ctx.session.state["proposal_content"] = proposal_content
            
            final_response_text = ""
            async for event in self.critic_llm.run_async(ctx):
                if event.is_final_response() and event.content:
                    final_response_text = event.content.parts[0].text
                yield event

            subject = proposal_filename.split('_')[0]
            critique_filename = f"{subject}_trade_critique.json"
            artifact_part = types.Part.from_bytes(
                data=final_response_text.encode("utf-8"), mime_type="application/json")
            
            version = await ctx.artifact_service.save_artifact(
                app_name=ctx.app_name, user_id=ctx.user_id, session_id=ctx.session.id,
                filename=critique_filename, artifact=artifact_part)
            
            ctx.session.state["last_critique_file"] = critique_filename
            
            final_text = f"Devil's Advocate created '{critique_filename}' (v{version})."
            logger.info(f"[{self.name}] {final_text}")

        except Exception as e:
            final_text = f"Devil's Advocate failed. Error: {e}"
            logger.error(f"[{self.name}] {final_text}", exc_info=True)
        
        yield Event(author=self.name, content=types.Content(parts=[types.Part(text=final_text)]))

root_agent = DevilsAdvocate(
    name="devils_advocate",
    critic_llm=critic_llm,
    sub_agents=[critic_llm]
)