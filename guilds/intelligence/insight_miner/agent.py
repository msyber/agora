import json
import logging
from typing import AsyncGenerator, Any, Dict, List

from google.adk.agents import BaseAgent, LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai import types
from google.genai.types import GenerationConfig
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ArticleInsight(BaseModel):
    headline: str = Field(description="The original headline of the article.")
    sentiment: str = Field(description="Sentiment of the article, must be 'Positive', 'Negative', or 'Neutral'.")
    summary: str = Field(description="A concise, one-sentence summary of the article.")

class AnalysisResult(BaseModel):
    insights: List[ArticleInsight] = Field(description="A list of insights for each article.")

analyst_llm = LlmAgent(
    name="analyst_llm",
    model="gemini-2.5-flash-lite",
    instruction="""
    You are an expert financial analyst. Analyze the following JSON of news articles.
    For each article, extract the headline, sentiment (Positive, Negative, Neutral),
    and a one-sentence summary. Respond ONLY with a valid JSON object matching the required schema.

    JSON Content:
    {news_content}
    """,
    output_schema=AnalysisResult,
)

class InsightMiner(BaseAgent):
    analyst_llm: LlmAgent
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        final_response_text = ""
        try:
            artifact_filename = ctx.session.state.get("last_harvested_file")
            if not artifact_filename or not ctx.artifact_service:
                raise ValueError("Artifact filename or service not available.")
            
            artifact_part = ctx.artifact_service.load_artifact(
                app_name=ctx.app_name, user_id=ctx.user_id,
                session_id=ctx.session.id, filename=artifact_filename)
            
            if not artifact_part:
                raise ValueError(f"Failed to load artifact: {artifact_filename}")
            news_content = artifact_part.inline_data.data.decode('utf-8')
            logger.info(f"[{self.name}] Successfully loaded artifact '{artifact_filename}'.")
            
            ctx.session.state["news_content"] = news_content
            
            async for event in self.analyst_llm.run_async(ctx):
                if event.is_final_response() and event.content and event.content.parts:
                    final_response_text = event.content.parts[0].text
                yield event

            new_artifact_name = artifact_filename.replace("_raw.json", "_insights.json")
            new_artifact_part = types.Part.from_bytes(
                data=final_response_text.encode("utf-8"), mime_type="application/json")
            
            # [CORRECTED] Removed 'await'
            ctx.artifact_service.save_artifact(
                app_name=ctx.app_name, user_id=ctx.user_id, session_id=ctx.session.id,
                filename=new_artifact_name, artifact=new_artifact_part)
            
            ctx.session.state["last_insight_file"] = new_artifact_name
            logger.info(f"[{self.name}] Saved insights to artifact '{new_artifact_name}'.")
        except Exception as e:
            logger.error(f"[{self.name}] An error occurred during insight mining: {e}")

root_agent = InsightMiner(
    name="insight_miner",
    analyst_llm=analyst_llm,
    sub_agents=[analyst_llm]
)