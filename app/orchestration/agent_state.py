"""
模組 G：AI Orchestration Agent
定義 LangGraph AgentState —— Agent 執行過程中各 Node 共用的狀態容器。

設計說明：
  - AgentState 使用 TypedDict，而非 Pydantic BaseModel，
    因為 LangGraph StateGraph 要求 state 型別為 TypedDict 或 dataclass。
  - messages 欄位使用 Annotated + add_messages，
    讓 LangGraph 自動累積對話紀錄，而非每次覆蓋。
  - 各模組的結果欄位直接使用各模組的 Response Pydantic Schema（而非 dict），
    讓 synthesize_node 存取時享有型別提示與 IDE 自動補全。
  - 選填欄位使用 NotRequired，語意為「此欄位在某些 workflow 中不存在」，
    而非「存在但值為 None」，更貼近 LangGraph partial state update 的概念。
  - error_messages 使用 operator.add 作為 reducer，
    讓多個 Node / Tool 的錯誤訊息正確累積，避免互相覆蓋。
  - company_profile 沿用 AgentRequest 的 dict[str, Any]，
    Adapter 轉換（dict → CompanyProfile）由 tools.py 負責。

v1.7 新增欄位：
  - parsed_intent    : parse_input_node 抽取出的使用者意圖清單
                       合法值：["rewrite", "salary", "sourcing", "hr_qa"] 的子集
                       branch_node 讀取此欄位取代原本的關鍵字硬比對
  - clarification_needed : clarify_node 判斷資訊缺失時寫入的提問文字
                           非空時 workflow 會在回傳給前端前中止執行
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, NotRequired, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from app.models.analyzer_schemas import AnalyzeJDResponse
from app.models.rewriter_schemas import RewriteJDResponse
from app.models.persona_schemas import GeneratePersonaResponse
from app.models.salary_schemas import SalaryCheckResponse
from app.models.sourcing_schemas import SourcingResult
from app.models.copilot_schemas import CopilotResponse


class AgentState(TypedDict):
    # LangGraph 必填：對話訊息串（自動累積，不覆蓋）
    messages: Annotated[list[BaseMessage], add_messages]

    # 使用者輸入（從 AgentRequest 帶入）
    user_input: str
    job_title: NotRequired[str | None]
    jd_text: NotRequired[str | None]
    company_profile: NotRequired[dict[str, Any] | None]

    # 各模組執行結果（由各 Node 寫入，使用 Pydantic Response Schema）
    analysis_result: NotRequired[AnalyzeJDResponse]       # 模組 A
    rewrite_result: NotRequired[RewriteJDResponse]        # 模組 B
    salary_result: NotRequired[SalaryCheckResponse]       # 模組 C
    persona_result: NotRequired[GeneratePersonaResponse]  # 模組 D
    sourcing_result: NotRequired[SourcingResult]          # 模組 E
    copilot_result: NotRequired[CopilotResponse]          # 模組 F

    # 控制欄位
    parsed_intent: NotRequired[list[str]]           # parse_input_node 寫入：rewrite / salary / sourcing / hr_qa 的子集
    clarification_needed: NotRequired[str | None]   # clarify_node 寫入：資訊不足時的補問文字
    branch_decision: NotRequired[str]               # salary / sourcing / both / none

    # 輸出
    final_report: NotRequired[str]
    error_messages: Annotated[list[str], operator.add]