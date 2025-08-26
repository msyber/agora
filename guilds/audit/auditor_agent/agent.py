import json
import logging
from typing import AsyncGenerator

from google.adk.agents import BaseAgent, LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai import types

from .trade_audit import TradeAudit

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

auditor_llm = LlmAgent(
    name="auditor_llm",
    model="gemini-2.5-flash-lite",
    instruction="""
    You are a master logician and impartial referee in a debate between two AI agents.
    Your task is NOT to have an opinion on the trade, but to evaluate the logical integrity of the debate itself.
    Review the Trade Proposal and the Devil's Advocate's Critique.

    **Trade Proposal:**
    {proposal_content}

    **Adversarial Critique:**
    {critique_content}

    **Your Task:**
    1. Assess if the critique's points (identified risks, logical fallacies) are valid and directly address the proposal's reasoning.
    2. If the critique successfully identifies significant, unaddressed flaws in the proposal's logic or evidence, your decision must be 'VETO'.
    3. If the proposal's reasoning is sound and the critique's points are minor or have been implicitly addressed, your decision is 'APPROVE'.
    4. Formulate your reasoning based purely on the quality of the debate.
    5. Respond ONLY with a valid JSON object conforming to the `TradeAudit` schema.
    """,
    output_schema=TradeAudit,
)

class AuditorAgent(BaseAgent):
    auditor_llm: LlmAgent
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        logger.info(f"[{self.name}] Commencing audit of trade debate.")
        try:
            proposal_filename = ctx.session.state.get("last_proposal_file")
            critique_filename = ctx.session.state.get("last_critique_file")

            if not all([proposal_filename, critique_filename, ctx.artifact_service]):
                raise ValueError("Prerequisite proposal and critique artifacts not found.")

            # Call load_artifact with explicit, correct keyword arguments.
            proposal_artifact = ctx.artifact_service.load_artifact(
                app_name=ctx.app_name, user_id=ctx.user_id,
                session_id=ctx.session.id, filename=proposal_filename)
            critique_artifact = ctx.artifact_service.load_artifact(
                app_name=ctx.app_name, user_id=ctx.user_id,
                session_id=ctx.session.id, filename=critique_filename)
            
            proposal_content = proposal_artifact.inline_data.data.decode('utf-8')
            critique_content = critique_artifact.inline_data.data.decode('utf-8')

            ctx.session.state["proposal_content"] = proposal_content
            ctx.session.state["critique_content"] = critique_content
            
            final_response_text = ""
            async for event in self.auditor_llm.run_async(ctx):
                if event.is_final_response() and event.content:
                    final_response_text = event.content.parts[0].text
                yield event

            subject = proposal_filename.split('_')[0]
            audit_filename = f"{subject}_trade_audit.json"
            
            audit_data = json.loads(final_response_text)
            audit_data['proposal_id'] = proposal_filename
            audit_json = json.dumps(audit_data, indent=2)

            artifact_part = types.Part.from_bytes(
                data=audit_json.encode("utf-8"), mime_type="application/json")
            
            version = ctx.artifact_service.save_artifact(
                app_name=ctx.app_name, user_id=ctx.user_id, session_id=ctx.session.id,
                filename=audit_filename, artifact=artifact_part)
            
            # Pass the filename to the RiskGuardian agent.
            ctx.session.state["last_audit_file"] = audit_filename

            final_text = f"AuditorAgent created '{audit_filename}' (v{version})."
            logger.info(f"[{self.name}] {final_text}")

        except Exception as e:
            final_text = f"AuditorAgent failed. Error: {e}"
            logger.error(f"[{self.name}] {final_text}", exc_info=True)
        
        yield Event(author=self.name, content=types.Content(parts=[types.Part(text=final_text)]))

root_agent = AuditorAgent(
    name="auditor_agent",
    auditor_llm=auditor_llm,
    sub_agents=[auditor_llm]
)