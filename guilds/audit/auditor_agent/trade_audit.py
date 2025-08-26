from typing import List, Optional
from pydantic import BaseModel, Field

class TradeAudit(BaseModel):
    """
    The final verdict from the AuditorAgent, evaluating the logical soundness
    of a trade proposal and its critique.
    """
    proposal_id: str = Field(description="A unique identifier for the trade being audited.")
    decision: str = Field(description="The final verdict, either 'APPROVE' or 'VETO'.")
    reasoning: str = Field(
        description="Explanation for the decision, focusing on the logical integrity of the debate process."
    )
    unresolved_flaws: Optional[List[str]] = Field(
        description="A list of critical flaws from the critique that were not adequately addressed."
    )