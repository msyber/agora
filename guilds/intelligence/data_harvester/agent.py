import json
import logging
import re
from typing import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.tools import FunctionTool
from google.genai import types

from .tools import fetch_news_articles

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _extract_subject_from_query(query: str) -> str:
    """A simple helper to extract a ticker or subject from a query."""
    matches = re.findall(r'\b[A-Z]{2,}\b', query)
    return matches[-1] if matches else "UNKNOWN_SUBJECT"

class DataHarvester(BaseAgent):
    _news_tool: FunctionTool
    def __init__(self, name: str):
        super().__init__(name=name)
        self._news_tool = FunctionTool(func=fetch_news_articles)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        user_query = ctx.user_content.parts[0].text
        subject = _extract_subject_from_query(user_query)
        logger.info(f"[{self.name}] Received harvest request for: '{subject}'")

        tool_result = self._news_tool.func(query=subject, limit=10)
        articles_json = json.dumps(tool_result, indent=2)
        artifact_part = types.Part.from_bytes(
            data=articles_json.encode("utf-8"), mime_type="application/json"
        )
        artifact_filename = f"{subject}_news_raw.json"
        try:
            # Call the artifact_service directly from the context,
            # which is the required pattern for a CustomAgent.
            if ctx.artifact_service:
                version = ctx.artifact_service.save_artifact(
                    app_name=ctx.app_name,
                    user_id=ctx.user_id,
                    session_id=ctx.session.id,
                    filename=artifact_filename,
                    artifact=artifact_part,
                )
                final_text = f"Data-Harvester successfully stored '{artifact_filename}' (v{version})."
                state_delta = { "status": "harvest_success", "last_harvested_file": artifact_filename }
            else:
                raise ValueError("ArtifactService is not configured in the Runner.")
                
        except (ValueError, AttributeError) as e:
            logger.error(f"[{self.name}] Artifact save error: {e}.")
            final_text = "Data-Harvester failed during artifact save."
            state_delta = {"status": "harvest_failed"}
            
        yield Event(
            author=self.name,
            content=types.Content(parts=[types.Part(text=final_text)]),
            actions=EventActions(state_delta=state_delta),
        )

root_agent = DataHarvester(name="data_harvester")