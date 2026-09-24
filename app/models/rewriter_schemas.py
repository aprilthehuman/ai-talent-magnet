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

v1.7 變更：
  - company_name、culture_keywords、vision 改為選填（原為必填）
    原因：Module G 透過 parse_input_node 從自然語言 Prompt 抽取資料，
    不保證三個欄位都能抽取到，改選填可避免 Pydantic 驗證失敗。
    rewriter_service.build_prompt() 已加入 fallback，LLM 端不受影響。
  - company_profile 本身改為選填（| None = None）
    原因：使用者在模組 B 頁面若完全不填 Company Profile，
    前端會傳 null，schema 必須允許 None 否則 422。
    service 層以 CompanyProfile() 空物件作 fallback。
"""


from pydantic import BaseModel


class CompanyProfile(BaseModel):
    # v1.7：改為選填，Module G 走 parse_input_node 時不一定能抽取到這三個欄位
    company_name: str | None = None
    culture_keywords: list[str] = []
    vision: str | None = None
    # 以下維持原本的選填設定
    manager_style: str | None = None
    tone_preference: str | None = None
    must_include: list[str] = []
    must_avoid: list[str] = []
    industry_context: str | None = None


class RewriteJDRequest(BaseModel):
    original_jd: str
    # v1.7：company_profile 改為選填（None = 使用者未填任何公司資訊）
    # service 層以 CompanyProfile() 空物件作 fallback，LLM 用通用語氣改寫
    company_profile: CompanyProfile | None = None
    target_candidate_focus: str | None = None


class RewriteJDResponse(BaseModel):
    startup_version: str
    stable_enterprise_version: str
    high_growth_version: str
    rewrite_notes: list[str]    # 3 條，每個版本一條說明
    profile_applied: dict       # 套用的 Profile 摘要，供驗證用