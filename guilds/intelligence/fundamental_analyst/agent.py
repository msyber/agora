import logging
import re
from typing import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.tools import FunctionTool
from google.genai import types

from .tools import fetch_sec_filing_section

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _parse_filing_query(query: str) -> dict | None:
    """
    [CORRECTED] Parses a query for ticker, filing type, and section using a more robust regex.
    """
    # Example query: "Analyze Item 1A. Risk Factors from the 10-K for NVDA"
    pattern = re.compile(
        r".*(Item .*?) from the (\d+-[KQ]) for ([A-Z]+)", re.IGNORECASE
    )
    match = pattern.search(query)
    if not match:
        return None
    
    # Groups are indexed from 1
    section = match.group(1).strip()
    filing_type = match.group(2).upper()
    ticker = match.group(3).upper()
    return {"ticker": ticker, "filing_type": filing_type, "section": section}


class FundamentalAnalyst(BaseAgent):
    """
    A deterministic agent that extracts parameters from a query,
    fetches SEC filing data, and saves it as an artifact.
    """
    _filing_tool: FunctionTool

    def __init__(self, name: str):
        super().__init__(name=name)
        self._filing_tool = FunctionTool(func=fetch_sec_filing_section)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        user_query = ctx.user_content.parts[0].text
        logger.info(f"[{self.name}] Received request: '{user_query}'")

        parsed_args = _parse_filing_query(user_query)

        if not parsed_args:
            error_text = "Query did not match expected format for filing analysis."
            logger.error(f"[{self.name}] {error_text}")
            yield Event(author=self.name, content=types.Content(parts=[types.Part.from_text(error_text)]))
            return

        tool_result = self._filing_tool.func(**parsed_args)
        filing_content = tool_result.get("content", "")

        if filing_content and ctx.artifact_service:
            try:
                subject = parsed_args['ticker']
                artifact_filename = f"{subject}_10K_risks_raw.txt"
                
                # Use the robust `from_bytes` method for artifact creation.
                artifact_part = types.Part.from_bytes(
                    data=filing_content.encode('utf-8'),
                    mime_type="text/plain"
                )
                
                version = ctx.artifact_service.save_artifact(
                    app_name=ctx.app_name, user_id=ctx.user_id, session_id=ctx.session.id,
                    filename=artifact_filename, artifact=artifact_part)
                
                final_text = f"Fundamental-Analyst successfully stored '{artifact_filename}' (v{version})."
                logger.info(f"[{self.name}] {final_text}")
                yield Event(author=self.name, content=types.Content(parts=[types.Part.from_text(final_text)]))
            except Exception as e:
                logger.error(f"[{self.name}] Failed to save filing artifact: {e}")

root_agent = FundamentalAnalyst(name="fundamental_analyst")