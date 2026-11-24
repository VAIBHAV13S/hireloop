# Pydantic Schemas for Job Postings and Search

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class JobCreateRequest(BaseModel):
    title: str = Field(..., description="Job title")
    description: str = Field(..., description="Full job description")
    company_name: Optional[str] = Field(None, description="Company name")
    location: Optional[str] = Field(None, description="Location (e.g. 'San Francisco, CA' or 'Remote')")
    remote_type: Optional[str] = Field("remote", description="onsite | hybrid | remote")
    min_years: Optional[float] = Field(0.0, ge=0.0, description="Minimum years of experience required")
    salary_min: Optional[int] = Field(None, ge=0, description="Minimum base salary in USD")
    salary_max: Optional[int] = Field(None, ge=0, description="Maximum base salary in USD")
    required_skills: List[str] = Field(default_factory=list, description="List of essential skills")
    preferred_skills: List[str] = Field(default_factory=list, description="List of nice-to-have skills")

class JobResponse(BaseModel):
    id: str
    title: str
    description: str
    company_name: Optional[str] = None
    location: Optional[str] = None
    remote_type: Optional[str] = None
    min_years: Optional[float] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    status: str
    created_at: Optional[datetime] = None

class CandidateMatchItem(BaseModel):
    user_id: str
    full_name: Optional[str] = None
    headline: Optional[str] = None
    location: Optional[str] = None
    years_exp: Optional[float] = None
    summary: Optional[str] = None
    fit_score: float
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    fit_explanation: str
