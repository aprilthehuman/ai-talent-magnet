"""
模組 G：AI Orchestration Agent
models/agent_schemas.py — Agent 的 Request / Response Pydantic Schema

設計說明：
  - AgentRequest 為 Agent 的統一入口，整合所有模組所需的輸入欄位
  - company_profile 使用 dict[str, Any]，Adapter 轉換（dict → CompanyProfile）
    由 tools.py 的 _to_company_profile() 負責，保持 schema 層的彈性
  - v1.7：company_profile 改為選填，parse_input_node 會從 user_input 自動提取
  - company_profile 可額外夾帶 company_type / seniority_level / salary_min / salary_max，
    這些欄位不在 CompanyProfile schema 內，但 tools.py 會嘗試讀取並傳給對應模組
  - AgentResponse 的 steps_taken 記錄本次實際執行的模組，方便前端呈現執行路徑
  - v1.7 新增：clarification_needed、parsed_intent、branch_decision 供 eval 斷言使用
"""

from typing import Any

from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    user_input: str = Field(..., min_length=2, description="使用者的自然語言指令")
    job_title: str | None = Field(default=None, description="職稱")
    jd_text: str | None = Field(default=None, description="完整 JD 文字")
    company_profile: dict[str, Any] | None = Field(
        default=None,
        description=(
            "公司設定檔，結構對應 Module B 的 CompanyProfile。"
            "v1.7 改為選填：未提供時由 parse_input_node 從 user_input 自動提取。"
            "可額外夾帶 company_type / seniority_level / salary_min / salary_max，"
            "供 Module A / C 使用。"
        ),
    )

    # ── 已移除（v1.7）────────────────────────────────────────────────────
    # v1.6 的 model_validator：有 jd_text 時強制要求 company_profile。
    # v1.7 company_profile 改為選填，parse_input_node 從自然語言自動提取，
    # 資訊不足時由 clarify_node 主動補問，不在 schema 層拋 exception。


class AgentResponse(BaseModel):
    final_report: str = Field(..., description="Agent 整合後的最終報告，Markdown 格式")
    steps_taken: list[str] = Field(..., description="Agent 本次實際執行的模組名稱清單")
    error_messages: list[str] = Field(
        default_factory=list,
        description="執行過程中發生的模組錯誤訊息；空 list 代表全部成功",
    )

    # ── v1.7 新增：供 eval 斷言與前端透明度使用 ──────────────────────────
    clarification_needed: str | None = Field(
        default=None,
        description="clarify_node 產出的補問訊息；None 表示資訊充足，不需補問",
    )
    parsed_intent: list[str] = Field(
        default_factory=list,
        description="parse_input_node 提取的意圖清單（rewrite / salary / sourcing / hr_qa）",
    )
    branch_decision: str | None = Field(
        default=None,
        description="branch_node 的路由決策（none / salary / sourcing / both）",
    )