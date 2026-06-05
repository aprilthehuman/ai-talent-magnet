from pydantic import BaseModel
from app.models.rewriter_schemas import CompanyProfile


"""
模組 D: Candidate Persona Generator
輸入整合模組 A (job_title、company_type、industry、seniority_level)
與模組 B (job_description_text 選定版本、company_profile、target_candidate_focus)
輸出採固定 schema, 讓前端可以做卡片式呈現, 並讓下游模組(Sourcing Assistant)直接接收
"""


class GeneratePersonaRequest(BaseModel):
    # 從模組 A 帶入
    job_title: str
    company_type: str | None = None
    industry: str | None = None
    seniority_level: str | None = None

    # 從模組 B 帶入
    job_description_text: str
    company_profile: CompanyProfile
    target_candidate_focus: str | None = None


class CandidatePersona(BaseModel):
    ideal_seniority: str
    likely_background: list[str]
    key_skills: list[str]
    candidate_motivators: list[str]
    likely_concerns: list[str]
    preferred_message_style: str
    likely_channels: list[str]


class GeneratePersonaResponse(BaseModel):
    job_title: str
    persona: CandidatePersona