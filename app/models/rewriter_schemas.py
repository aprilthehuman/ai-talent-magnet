"""
模組 B：JD Rewrite AI
輸入包含原始 JD 與巢狀的 CompanyProfile
（company_name、culture_keywords、vision、manager_style、
tone_preference、must_include、must_avoid、industry_context）
輸出三種風格的改寫版本（Startup 風、穩定企業風、高成長挑戰型）與改寫重點說明

設計重點：
  - CompanyProfile 為巢狀物件，讓改寫結果真正貼近公司個性而非通用模板
  - must_avoid 關鍵字由 service 層後處理驗證，確保禁用詞不出現在輸出中
  - must_include 注入 prompt，由 LLM 負責自然融入改寫結果
"""


from pydantic import BaseModel


class CompanyProfile(BaseModel):
    company_name: str
    culture_keywords: list[str]
    vision: str
    manager_style: str | None = None
    tone_preference: str | None = None
    must_include: list[str] = []
    must_avoid: list[str] = []
    industry_context: str | None = None


class RewriteJDRequest(BaseModel):
    original_jd: str
    company_profile: CompanyProfile
    target_candidate_focus: str | None = None


class RewriteJDResponse(BaseModel):
    startup_version: str
    stable_enterprise_version: str
    high_growth_version: str
    rewrite_notes: list[str]    # 3 條，每個版本一條說明
    profile_applied: dict       # 套用的 Profile 摘要，供驗證用
    