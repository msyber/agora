import logging
from typing import AsyncGenerator

from google.adk.agents import BaseAgent, SequentialAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai import types

# Import the pipelines
from .data_harvester.agent import root_agent as data_harvester_agent
from .insight_miner.agent import root_agent as insight_miner_agent
from .fundamental_analyst.agent import root_agent as fundamental_analyst_agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the pipelines as before
news_pipeline = SequentialAgent(
    name="news_pipeline",
    sub_agents=[data_harvester_agent, insight_miner_agent],
)

filing_pipeline = SequentialAgent(
    name="filing_pipeline",
    sub_agents=[fundamental_analyst_agent]
)

# [CORRECTED] The orchestrator now follows a standard Pydantic model structure.
class IntelligenceOrchestrator(BaseAgent):
    """
    A deterministic router that delegates tasks to specialized pipelines
    based on keywords in the user's query.
    """
    # Declare sub-agents as Pydantic fields.
    news_pipeline: SequentialAgent
    filing_pipeline: SequentialAgent

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """
        Inspects the user query and routes to the correct pipeline.
        """
        user_query = ctx.user_content.parts[0].text.lower()
        logger.info(f"[{self.name}] Routing query: '{user_query}'")

        # Deterministic routing logic using the instance attributes.
        if any(keyword in user_query for keyword in ["news", "articles", "sentiment"]):
            logger.info(f"[{self.name}] Delegating to news_pipeline.")
            async for event in self.news_pipeline.run_async(ctx):
                yield event
        elif any(keyword in user_query for keyword in ["filing", "10-k", "10-q", "risk factors"]):
            logger.info(f"[{self.name}] Delegating to filing_pipeline.")
            async for event in self.filing_pipeline.run_async(ctx):
                yield event
        else:
            logger.warning(f"[{self.name}] No pipeline matched. Responding with help message.")
            yield Event(
                author=self.name,
                content=types.Content(
                    parts=[types.Part(text="Could not determine the required task. Please specify 'news' or 'filing'.")]
                )
            )

# Instantiate the orchestrator, passing the pipelines as arguments.
# Pydantic will automatically handle initialization.
root_agent = IntelligenceOrchestrator(
    name="intelligence_orchestrator",
    news_pipeline=news_pipeline,
    filing_pipeline=filing_pipeline,
    # The framework still needs to know about the hierarchy for context.
    sub_agents=[news_pipeline, filing_pipeline]
)