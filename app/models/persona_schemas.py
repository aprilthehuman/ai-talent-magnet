# app/models/persona_schemas.py

from pydantic import BaseModel, Field
from typing import Literal
from app.models.rewriter_schemas import CompanyProfile

"""
模組 D：Candidate Persona Generator
輸入整合模組 A（job_title、company_type、industry、seniority_level）
與模組 B（job_description_text 選定版本、company_profile、target_candidate_focus）
輸出採固定 schema，讓前端可以做卡片式呈現，並讓下游模組（Sourcing Assistant）直接接收

新增：
  - EducationPreference：HR 填寫的學歷參考條件，影響 Persona 描述與下游 Sourcing 策略
  - education_preference 原樣帶出至 GeneratePersonaResponse，讓模組 E 直接接收
"""

# ── 學歷等級合法選項 ──────────────────────────────────────
# 用 Literal 限制，避免 HR 填入不合法的值
EducationLevel = Literal["不限", "大學", "碩士", "博士"]


# ── 子結構 ────────────────────────────────────────────────

class EducationPreference(BaseModel):
    """
    HR 填寫的學歷參考條件。
    作為參考條件（非硬性篩選），傳入 LLM 影響 Persona 描述與 Sourcing 策略。
    """
    level: EducationLevel = Field(default="不限", description="學歷要求等級")
    notes: str | None = Field(default=None, description="補充說明，例：台清交成優先、國外碩士加分")


# ── 輸入 Schema ───────────────────────────────────────────

class GeneratePersonaRequest(BaseModel):
    """
    模組 D 的輸入資料結構。
    所有欄位來源分三類：
      - 模組 A 帶入：job_title、company_type、industry、seniority_level
      - 模組 B 帶入：job_description_text、company_profile、target_candidate_focus
      - HR 選填補充：education_preference
    """
    # 從模組 A 帶入
    job_title: str = Field(..., description="職稱，沿用模組 A")
    company_type: str | None = Field(default=None, description="公司類型，例：startup / SME / enterprise")
    industry: str | None = Field(default=None, description="產業，例：SaaS / 電商 / 金融")
    seniority_level: str | None = Field(default=None, description="年資層級，例：junior / mid / senior")

    # 從模組 B 帶入
    job_description_text: str = Field(..., description="模組 B 選定的改寫版本")
    company_profile: CompanyProfile = Field(..., description="直接沿用模組 B 的 CompanyProfile schema")
    target_candidate_focus: str | None = Field(default=None, description="直接沿用模組 B 填寫的內容")

    # HR 選填補充
    education_preference: EducationPreference | None = Field(
        default=None,
        description="HR 填寫的學歷參考條件，影響 Persona 描述與下游 Sourcing 策略"
    )


# ── 輸出子結構 ────────────────────────────────────────────

class CandidatePersona(BaseModel):
    """
    LLM 推斷的候選人樣貌。
    採固定 schema 讓前端用卡片式呈現，並讓模組 E 直接接收各欄位。
    """
    ideal_seniority: str = Field(..., description="理想年資區間，例：3–5 年")
    likely_background: list[str] = Field(..., description="可能的職涯背景（參考 education_preference 生成）")
    key_skills: list[str] = Field(..., description="核心技能清單")
    candidate_motivators: list[str] = Field(..., description="在意的面向，例：技術自主性、WLB、薪資成長")
    likely_concerns: list[str] = Field(..., description="可能的顧慮，例：公司穩定性、技術棧是否夠新")
    preferred_message_style: str = Field(..., description="建議 HR 和這類候選人溝通時的語氣風格")
    likely_channels: list[str] = Field(..., description="可能出現的平台，例：LinkedIn、CakeResume、PTT")


# ── 輸出 Schema ───────────────────────────────────────────

class GeneratePersonaResponse(BaseModel):
    """
    模組 D 的輸出資料結構。
    education_preference 原樣帶出，讓模組 E 直接接收，不需要 HR 重複填寫。
    """
    job_title: str = Field(..., description="職稱")
    persona: CandidatePersona = Field(..., description="結構化候選人 Persona")
    education_preference: EducationPreference | None = Field(
        default=None,
        description="原樣帶出 HR 填寫的學歷條件，供模組 E 接收"
    )