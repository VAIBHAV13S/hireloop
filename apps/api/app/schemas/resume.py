# Pydantic Schemas for Resume Extraction and Profile Representation

from typing import List, Optional
from pydantic import BaseModel, Field

class ExtractedSkill(BaseModel):
    name: str = Field(..., description="Canonical or raw name of the skill")
    level: Optional[int] = Field(default=3, ge=1, le=5, description="Estimated proficiency level from 1 to 5")
    years: Optional[float] = Field(default=1.0, ge=0.0, description="Estimated years of experience with this skill")

class WorkRole(BaseModel):
    title: str = Field(..., description="Job title or role")
    company: Optional[str] = Field(None, description="Company or organization name")
    start_date: Optional[str] = Field(None, description="Start date (e.g. '2021-01' or '2021')")
    end_date: Optional[str] = Field(None, description="End date (e.g. '2023-05' or 'Present')")
    description: Optional[str] = Field(None, description="Key accomplishments or bullet points")

class EducationItem(BaseModel):
    degree: Optional[str] = Field(None, description="Degree or certificate name (e.g. 'B.S. in Computer Science')")
    institution: Optional[str] = Field(None, description="University or institution name")
    graduation_year: Optional[int] = Field(None, description="Graduation year")

class ProjectItem(BaseModel):
    name: str = Field(..., description="Project name")
    description: Optional[str] = Field(None, description="Summary of the project and technologies used")
    url: Optional[str] = Field(None, description="Repository or live URL")

class CandidateParsedProfile(BaseModel):
    name: Optional[str] = Field(None, description="Candidate's full name")
    headline: Optional[str] = Field(None, description="Professional headline or title (e.g. 'Senior Backend Engineer')")
    location: Optional[str] = Field(None, description="Current city/state/country")
    years_experience: Optional[float] = Field(default=0.0, ge=0.0, description="Total years of professional experience")
    summary: Optional[str] = Field(None, description="Professional summary or bio")
    skills: List[ExtractedSkill] = Field(default_factory=list, description="Extracted technical and domain skills")
    roles: List[WorkRole] = Field(default_factory=list, description="Work experience history")
    education: List[EducationItem] = Field(default_factory=list, description="Educational background")
    projects: List[ProjectItem] = Field(default_factory=list, description="Notable projects")
