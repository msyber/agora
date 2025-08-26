import json
import logging
from typing import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai import types

from .tools import get_current_price, check_position_size, check_sector_exposure
from .trade_order import TradeOrder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RiskGuardian(BaseAgent):
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        logger.info(f"[{self.name}] Commencing risk assessment.")
        try:
            # Step 1: Check the audit verdict.
            audit_filename = ctx.session.state.get("last_audit_file")
            audit_artifact = ctx.artifact_service.load_artifact(
                app_name=ctx.app_name, user_id=ctx.user_id,
                session_id=ctx.session.id, filename=audit_filename)
            audit_data = json.loads(audit_artifact.inline_data.data.decode('utf-8'))

            if audit_data.get("decision") == "VETO":
                final_text = "Risk assessment halted. Trade was VETOED by AuditorAgent."
                logger.warning(f"[{self.name}] {final_text}")
                yield Event(author=self.name, content=types.Content(parts=[types.Part(text=final_text)]))
                return

            # Step 2: Load the approved proposal and run risk checks.
            proposal_filename = ctx.session.state.get("last_proposal_file")
            proposal_artifact = ctx.artifact_service.load_artifact(
                app_name=ctx.app_name, user_id=ctx.user_id,
                session_id=ctx.session.id, filename=proposal_filename)
            proposal = json.loads(proposal_artifact.inline_data.data.decode('utf-8'))

            ticker = proposal["ticker"]
            current_price = get_current_price(ticker)
            # For simplicity, we'll trade a fixed notional value.
            notional_value = 50_000.00
            quantity = int(notional_value / current_price)
            
            checks = [
                check_position_size(notional_value),
                check_sector_exposure(ticker, notional_value)
            ]

            failed_checks = [c["reason"] for c in checks if not c["pass"]]

            # Step 3: Create a TradeOrder or reject the proposal.
            if failed_checks:
                final_text = f"Trade REJECTED by Risk-Guardian. Violations: {'; '.join(failed_checks)}"
                logger.error(f"[{self.name}] {final_text}")
            else:
                order = TradeOrder(
                    ticker=ticker,
                    action=proposal["action"],
                    quantity=quantity,
                    notional_value_usd=notional_value
                )
                order_json = order.model_dump_json(indent=2)
                order_filename = f"{ticker}_trade_order.json"
                artifact_part = types.Part.from_bytes(
                    data=order_json.encode("utf-8"), mime_type="application/json")
                version = ctx.artifact_service.save_artifact(
                    app_name=ctx.app_name, user_id=ctx.user_id, session_id=ctx.session.id,
                    filename=order_filename, artifact=artifact_part)
                
                # Store the order filename in session state for execution agent.
                ctx.session.state["last_order_file"] = order_filename
                
                final_text = f"Trade PASSED risk assessment. Created '{order_filename}' (v{version})."
                logger.info(f"[{self.name}] {final_text}")
                
        except Exception as e:
            final_text = f"Risk-Guardian failed. Error: {e}"
            logger.error(f"[{self.name}] {final_text}", exc_info=True)
        
        yield Event(author=self.name, content=types.Content(parts=[types.Part(text=final_text)]))

# This line is important for the agent to be discoverable.
root_agent = RiskGuardian(name="risk_guardian")