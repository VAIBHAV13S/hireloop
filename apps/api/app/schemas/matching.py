# Pydantic Schemas for Matching and Explanations

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class MatchExplanation(BaseModel):
    job_id: str = Field(..., description="Target job UUID")
    fit_reasons: List[str] = Field(default_factory=list, description="Specific alignment points between profile and job")
    gaps: List[str] = Field(default_factory=list, description="Missing requirements or recommended skill additions")
    score_adjustment: float = Field(default=0.0, description="LLM re-ranking calibration delta (-0.2 to +0.2)")
    summary: str = Field(..., description="Short executive summary of fit")

class MatchResponseItem(BaseModel):
    job_id: str
    title: Optional[str] = None
    company_name: Optional[str] = None
    location: Optional[str] = None
    remote_type: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    score: float
    dense_score: Optional[float] = None
    sparse_score: Optional[float] = None
    fit_reasons: Optional[List[str]] = None
    gaps: Optional[List[str]] = None

class MatchFeedbackRequest(BaseModel):
    job_id: str = Field(..., description="Target job UUID")
    signal: str = Field(..., description="User action signal: viewed | saved | dismissed | applied")
