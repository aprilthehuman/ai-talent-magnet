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

初始值說明：
  各模組結果欄位執行前不存在於 State，Tool 成功後才寫入。
  agent_service.py 建立 graph 時需提供完整的 initial_state dict，
  包含 analysis_result=None 等明確初始值。
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
    """
    LangGraph AgentState —— 整個 Agent 執行過程的共用狀態。

    欄位分四類：
      1. messages        : LangGraph 必填，累積 LLM / Tool 的對話訊息
      2. 使用者輸入      : 從 AgentRequest 帶入，各 Tool 依需取用
      3. 各模組執行結果  : 每個 Tool 執行後寫入，synthesize_node 整合輸出
      4. 控制欄位        : 最終報告與錯誤訊息

    AgentState 是 orchestration state，不是 domain data store。
    原則：只保存「下一個 Node 為了完成 workflow 需要知道的資訊」。
    """

    # ── 1. LangGraph 必填：對話訊息串 ─────────────────────
    # Annotated + add_messages：新訊息自動 append，而非覆蓋整個 list
    messages: Annotated[list[BaseMessage], add_messages]

    # ── 2. 使用者輸入（從 AgentRequest 帶入）────────────────
    # user_input 為必填；其餘為選填（無 JD 時 Agent 僅呼叫 Module F）
    user_input: str
    job_title: NotRequired[str | None]
    jd_text: NotRequired[str | None]
    # company_profile 保持 dict，Adapter 轉換由 tools.py 負責
    company_profile: NotRequired[dict[str, Any] | None]

    # ── 3. 各模組執行結果（由各 Tool 寫入）──────────────────
    # 執行前不存在於 State；Tool 成功後寫入對應的 Pydantic Response schema
    analysis_result: NotRequired[AnalyzeJDResponse]    # Module A：JD 吸引力分析
    rewrite_result: NotRequired[RewriteJDResponse]     # Module B：JD 改寫
    salary_result: NotRequired[SalaryCheckResponse]    # Module C：薪資競爭力
    persona_result: NotRequired[GeneratePersonaResponse]  # Module D：候選人 Persona
    sourcing_result: NotRequired[SourcingResult]       # Module E：Sourcing 助手
    copilot_result: NotRequired[CopilotResponse]       # Module F：HR 知識助手

    # ── 4. 控制欄位 ────────────────────────────────────────
    # branch_decision：persona_node 完成後，由 LLM 根據 user_input 判斷
    # 合法值："salary" / "sourcing" / "both"
    # agent_service.py 的 conditional edge 讀取此欄位決定下一個 Node
    branch_decision: NotRequired[str]

    # final_report：synthesize_node 整合所有工具輸出後生成
    final_report: NotRequired[str]

    # error_messages 使用 operator.add 作為 reducer：
    # 每個 Node 回傳 {"error_messages": ["..."]}，LangGraph 自動合併成一個 list
    error_messages: Annotated[list[str], operator.add]