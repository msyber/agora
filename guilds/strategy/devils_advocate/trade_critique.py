from typing import List, Optional
from pydantic import BaseModel, Field

class TradeCritique(BaseModel):
    """
    A structured critique of a trade proposal.
    """
    proposal_is_sound: bool = Field(description="Whether the proposal is logically sound and evidence-backed.")
    identified_risks: List[str] = Field(description="A list of potential risks or weaknesses not addressed in the proposal's reasoning.")
    logical_fallacies: Optional[List[str]] = Field(description="A list of any logical fallacies detected in the reasoning.")
    critique_summary: str = Field(description="A concise summary of the critique.")