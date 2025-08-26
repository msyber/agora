import json
import logging
from typing import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.tools import FunctionTool
from google.genai import types

from .tools import run_causal_discovery

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CausalAnalyst(BaseAgent):
    """
    Analyzes structured insights to build a causal graph of market drivers.
    """
    _causal_tool: FunctionTool

    def __init__(self, name: str):
        super().__init__(name=name)
        self._causal_tool = FunctionTool(func=run_causal_discovery)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        
        logger.info(f"[{self.name}] Commencing causal analysis.")
        final_text = ""
        try:
            insights_filename = ctx.session.state.get("last_insight_file")
            if not insights_filename or not ctx.artifact_service:
                raise ValueError("Insights artifact or service not available in state.")
            
            insights_artifact = ctx.artifact_service.load_artifact(
                app_name=ctx.app_name, user_id=ctx.user_id,
                session_id=ctx.session.id, filename=insights_filename
            )
            if not insights_artifact:
                raise ValueError(f"Failed to load artifact: {insights_filename}")

            insights_data = json.loads(insights_artifact.inline_data.data.decode('utf-8'))
            
            causal_result = self._causal_tool.func(insights_data=insights_data.get("insights", []))
            
            graph_json = json.dumps(causal_result, indent=2)
            artifact_part = types.Part.from_bytes(
                data=graph_json.encode("utf-8"), mime_type="application/json")
            
            graph_filename = insights_filename.replace("_insights.json", "_causal_graph.json")
            
            version = ctx.artifact_service.save_artifact(
                app_name=ctx.app_name, user_id=ctx.user_id, session_id=ctx.session.id,
                filename=graph_filename, artifact=artifact_part)
            
            ctx.session.state["last_causal_graph_file"] = graph_filename
            
            final_text = f"Causal-Analyst successfully generated and stored '{graph_filename}' (v{version})."
            logger.info(f"[{self.name}] {final_text}")
            
        except Exception as e:
            final_text = f"Causal-Analyst failed. Error: {e}"
            logger.error(f"[{self.name}] {final_text}", exc_info=True)

        # Use the direct Part constructor.
        yield Event(author=self.name, content=types.Content(parts=[types.Part(text=final_text)]))

root_agent = CausalAnalyst(name="causal_analyst")