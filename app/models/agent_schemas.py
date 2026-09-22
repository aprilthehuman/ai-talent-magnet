"""
模組 G：AI Orchestration Agent
models/agent_schemas.py — Agent 的 Request / Response Pydantic Schema

設計說明：
  - AgentRequest 為 Agent 的統一入口，整合所有模組所需的輸入欄位
  - company_profile 使用 dict[str, Any]，Adapter 轉換（dict → CompanyProfile）
    由 tools.py 的 _to_company_profile() 負責，保持 schema 層的彈性
  - 有 jd_text 時強制要求 company_profile（model_validator 驗證），
    確保 Module B 一定有足夠的輸入可以執行
  - company_profile 可額外夾帶 company_type / seniority_level / salary_min / salary_max，
    這些欄位不在 CompanyProfile schema 內，但 tools.py 會嘗試讀取並傳給對應模組
  - AgentResponse 的 steps_taken 記錄本次實際執行的模組，方便前端呈現執行路徑
"""

from typing import Any

from pydantic import BaseModel, Field, model_validator


class AgentRequest(BaseModel):
    user_input: str = Field(..., min_length=2, description="使用者的自然語言指令")
    job_title: str | None = Field(default=None, description="職稱")
    jd_text: str | None = Field(default=None, description="完整 JD 文字")
    company_profile: dict[str, Any] | None = Field(
        default=None,
        description=(
            "公司設定檔，結構對應 Module B 的 CompanyProfile。"
            "提供 jd_text 時必填。"
            "可額外夾帶 company_type / seniority_level / salary_min / salary_max，"
            "供 Module A / C 使用。"
        ),
    )

    @model_validator(mode="after")
    def require_profile_when_jd_provided(self) -> "AgentRequest":
        """
        有 JD 就必須有 company_profile，確保 A→B→D 固定管線中 Module B 可以執行。
        無 jd_text 時（純 HR 知識問答），company_profile 可不填。
        """
        if self.jd_text and not self.company_profile:
            raise ValueError("提供 jd_text 時，company_profile 為必填")
        return self


class AgentResponse(BaseModel):
    final_report: str = Field(..., description="Agent 整合後的最終報告，Markdown 格式")
    steps_taken: list[str] = Field(..., description="Agent 本次實際執行的模組名稱清單")
    error_messages: list[str] = Field(
        default_factory=list,
        description="執行過程中發生的模組錯誤訊息；空 list 代表全部成功",
    )