import asyncio
import json
import logging
from typing import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai import types

from .broker_api import submit_order

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExecutionAgent(BaseAgent):
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        logger.info(f"[{self.name}] Commencing trade execution.")
        try:
            order_filename = ctx.session.state.get("last_order_file")
            if not order_filename: raise ValueError("Trade order artifact not found in state.")

            order_artifact = ctx.artifact_service.load_artifact(
                app_name=ctx.app_name, user_id=ctx.user_id,
                session_id=ctx.session.id, filename=order_filename)
            trade_order = json.loads(order_artifact.inline_data.data.decode('utf-8'))

            # Call the external (mocked) broker API
            confirmation = await submit_order(trade_order)
            
            # Create the final confirmation artifact
            confirmation_json = json.dumps(confirmation, indent=2)
            subject = trade_order['ticker']
            confirmation_filename = f"{subject}_trade_confirmation.json"
            
            artifact_part = types.Part.from_bytes(
                data=confirmation_json.encode("utf-8"), mime_type="application/json")
            version = ctx.artifact_service.save_artifact(
                app_name=ctx.app_name, user_id=ctx.user_id, session_id=ctx.session.id,
                filename=confirmation_filename, artifact=artifact_part)
            
            final_text = f"Execution successful. Confirmation artifact '{confirmation_filename}' (v{version}) created."
            logger.info(f"[{self.name}] {final_text}")
                
        except Exception as e:
            final_text = f"Execution-Agent failed. Error: {e}"
            logger.error(f"[{self.name}] {final_text}", exc_info=True)
        
        yield Event(author=self.name, content=types.Content(parts=[types.Part(text=final_text)]))

# This line is crucial for the agent to be discoverable.
root_agent = ExecutionAgent(name="execution_agent")