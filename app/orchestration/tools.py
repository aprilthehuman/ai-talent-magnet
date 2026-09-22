"""
模組 G：AI Orchestration Agent
orchestration/tools.py — Node 呼叫層（Service Adapter）

職責：
  - 將 AgentState 的欄位組裝成各模組的 Request schema
  - 執行 Adapter 轉換：company_profile dict → CompanyProfile Pydantic 物件
    （Module B / D 需要完整物件；Module A / C / E 只用 dict 的部分欄位）
  - 呼叫各模組 Service 函式
  - 回傳 partial state dict，供 LangGraph Node 更新 State

設計原則：
  - 函式簽名統一為 (state: AgentState) -> dict，方便 agent_service.py 統一呼叫
  - 不使用 @tool decorator（本架構是 Structured Workflow，不是 ReAct Agent）
  - AgentRequest 的 model_validator 已確保有 jd_text 時 company_profile 必存在，
    因此 run_rewrite_jd / run_generate_persona 可直接存取，不需再做防呆
  - Module B 改寫後，Agent 自動選取 startup_version 作為後續流程的基底 JD
    （Streamlit 互動版本才需要 HR 手動選版本）
  - 各函式內部的 try / except 將錯誤寫入 error_messages，
    讓後續 Node 可以繼續執行，不因單一模組失敗而中斷整個 workflow

company_profile dict 欄位對應說明：
  Agent 收到的 company_profile 對應 Module B 的 CompanyProfile schema：
    company_name, culture_keywords, vision, manager_style,
    tone_preference, must_include, must_avoid, industry_context
  HR 可額外夾帶以下欄位，tools.py 嘗試讀取並傳給對應模組；沒有時傳 None：
    company_type    → Module A / C / D
    seniority_level → Module A / C / D
    salary_min      → Module C
    salary_max      → Module C
"""

from typing import Any

from langchain_openai import ChatOpenAI

from app.models.analyzer_schemas import AnalyzeJDRequest
from app.models.rewriter_schemas import CompanyProfile, RewriteJDRequest
from app.models.persona_schemas import GeneratePersonaRequest
from app.models.salary_schemas import SalaryCheckRequest
from app.models.sourcing_schemas import SourcingRequest
from app.models.copilot_schemas import CopilotResponse
from app.services.analyzer_service import analyze_jd
from app.services.rewriter_service import rewrite_jd
from app.services.persona_service import generate_persona
from app.services.salary_service import check_salary
from app.services.sourcing_service import generate_sourcing_result
from app.services.copilot_service import rag_search, lookup_employee, calculate_leave
from app.orchestration.agent_state import AgentState


# ── Adapter：dict → CompanyProfile ───────────────────────────

def _to_company_profile(profile_dict: dict[str, Any]) -> CompanyProfile:
    """
    Adapter：將 AgentRequest 帶來的 company_profile dict
    轉換成 Module B / D 使用的 CompanyProfile Pydantic 物件。
    model_validate() 自動對應欄位，dict 中多餘的 key
    （如 company_type / salary_min）會被忽略，不影響驗證。
    """
    return CompanyProfile.model_validate(profile_dict)


# ── Node 函式：Module A（JD 吸引力分析）──────────────────────

def run_analyze_jd(state: AgentState) -> dict:
    """
    呼叫 Module A（JD 吸引力分析）。
    從 company_profile dict 嘗試取得背景欄位（company_type / industry_context /
    seniority_level），這些欄位為選填，沒有時傳 None，Module A 仍可正常執行。
    """
    try:
        profile = state.get("company_profile") or {}

        request = AnalyzeJDRequest(
            job_title=state.get("job_title") or "",
            job_description_text=state.get("jd_text") or "",
            # company_type / seniority_level 為 HR 額外夾帶的欄位，CompanyProfile 沒有
            company_type=profile.get("company_type"),
            # industry_context 是 CompanyProfile 的欄位，對應 Module A 的 industry 參數
            industry=profile.get("industry_context"),
            seniority_level=profile.get("seniority_level"),
        )

        result = analyze_jd(request)
        return {"analysis_result": result}

    except Exception as e:
        return {"error_messages": [f"analyze_node 失敗：{e}"]}


# ── Node 函式：Module B（JD 改寫）────────────────────────────

def run_rewrite_jd(state: AgentState) -> dict:
    """
    呼叫 Module B（JD 改寫）。
    前提：AgentRequest 的 model_validator 已確保有 jd_text 時 company_profile 必存在，
    因此直接存取 state["company_profile"]，不需要額外防呆。
    改寫成功後，Agent 自動選用 startup_version 作為後續流程的基底 JD。
    """
    try:
        request = RewriteJDRequest(
            original_jd=state.get("jd_text") or "",
            company_profile=_to_company_profile(state["company_profile"]),
        )

        result = rewrite_jd(request)
        return {"rewrite_result": result}

    except Exception as e:
        return {"error_messages": [f"rewrite_node 失敗：{e}"]}


# ── Node 函式：Module D（候選人 Persona）─────────────────────

def run_generate_persona(state: AgentState) -> dict:
    """
    呼叫 Module D（候選人 Persona 生成）。
    前提：A→B→D 為固定管線，執行到此時 rewrite_result 必定存在。
    直接使用 Module B 改寫後的 startup_version 作為 JD 輸入。
    """
    try:
        profile_dict = state["company_profile"]
        rewrite_result = state["rewrite_result"]

        request = GeneratePersonaRequest(
            job_title=state.get("job_title") or "",
            company_type=profile_dict.get("company_type"),
            industry=profile_dict.get("industry_context"),
            seniority_level=profile_dict.get("seniority_level"),
            # 使用 Module B 改寫後的 startup_version，而非原始 jd_text
            job_description_text=rewrite_result.startup_version,
            company_profile=_to_company_profile(profile_dict),
        )

        result = generate_persona(request)
        return {"persona_result": result}

    except Exception as e:
        return {"error_messages": [f"persona_node 失敗：{e}"]}


# ── Node 函式：Module C（薪資競爭力）─────────────────────────

def run_check_salary(state: AgentState) -> dict:
    """
    呼叫 Module C（薪資競爭力分析）。
    education_level 從 Module D 的 persona_result 取得。
    salary_min / salary_max 為選填，HR 可額外夾帶於 company_profile dict 中；
    未提供時 Module C 會嘗試從 jd_text 解析，若兩者皆無則只輸出市場區間。
    """
    try:
        profile = state.get("company_profile") or {}

        # 從 Module D 結果取得學歷條件
        education_level = None
        persona_result = state.get("persona_result")
        if persona_result and persona_result.education_preference:
            education_level = persona_result.education_preference.level

        request = SalaryCheckRequest(
            job_title=state.get("job_title") or "",
            company_type=profile.get("company_type"),
            industry=profile.get("industry_context"),
            seniority_level=profile.get("seniority_level"),
            # salary_min / salary_max 為 HR 額外夾帶欄位，CompanyProfile 沒有定義
            salary_min=profile.get("salary_min"),
            salary_max=profile.get("salary_max"),
            job_description_text=state.get("jd_text") or "",
            education_level=education_level,
        )

        result = check_salary(request)
        return {"salary_result": result}

    except Exception as e:
        return {"error_messages": [f"salary_node 失敗：{e}"]}


# ── Node 函式：Module E（Sourcing 助手）──────────────────────

def run_generate_sourcing(state: AgentState) -> dict:
    """
    呼叫 Module E（AI Sourcing 助手）。
    所有輸入欄位來自 Module D 的 persona_result；
    若 Module D 未執行（例外狀況），記錄錯誤後讓 workflow 繼續。
    """
    try:
        persona_result = state.get("persona_result")
        if not persona_result:
            return {"error_messages": ["sourcing_node 跳過：缺少 Persona 資料（Module D 需先執行）"]}

        persona = persona_result.persona

        request = SourcingRequest(
            job_title=state.get("job_title") or persona_result.job_title,
            # 以下欄位全部來自 Module D 的 CandidatePersona
            key_skills=persona.key_skills,
            ideal_seniority=persona.ideal_seniority,
            likely_channels=persona.likely_channels,
            likely_background=persona.likely_background,
            candidate_motivators=persona.candidate_motivators,
            likely_concerns=persona.likely_concerns,
            preferred_message_style=persona.preferred_message_style,
            # education_preference 原樣帶出（Module D 已處理格式）
            education_preference=persona_result.education_preference,
        )

        result = generate_sourcing_result(request)
        return {"sourcing_result": result}

    except Exception as e:
        return {"error_messages": [f"sourcing_node 失敗：{e}"]}


# ── Node 函式：Module F（HR 知識助手）────────────────────────

def run_copilot_query(state: AgentState) -> dict:
    """
    呼叫 Module F（HR 知識助手）。
    使用兩輪 LLM tool calling：
      第一輪：LLM 判斷要呼叫哪個 Tool
      第二輪：LLM 整合 Tool 結果，生成最終回答
    可用 Tool：
      - rag_search      : 查詢勞動法規 / 公司政策知識庫
      - lookup_employee : 查詢員工基本資料
      - calculate_leave : 計算特休餘額
    此路徑僅在 user_input 為 HR 知識類問題（無 jd_text）時才會進入。
    """
    try:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        tools = [rag_search, lookup_employee, calculate_leave]
        llm_with_tools = llm.bind_tools(tools)

        # 建立 tool name → function 的 mapping，供手動執行 tool call 使用
        tool_map = {t.name: t for t in tools}

        user_question = state.get("user_input", "")
        messages = [{"role": "user", "content": user_question}]

        # 第一輪：LLM 決定要呼叫哪個 Tool
        ai_message = llm_with_tools.invoke(messages)
        tool_used = "none"
        answer = ""

        if ai_message.tool_calls:
            # 取第一個 tool call（HR 知識問題通常只需呼叫一個 Tool）
            tool_call = ai_message.tool_calls[0]
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_used = tool_name

            # 執行 Tool 並取得結果
            tool_result = tool_map[tool_name].invoke(tool_args)

            # 第二輪：LLM 整合 Tool 結果，生成最終回答
            messages += [
                ai_message,
                {"role": "tool", "tool_call_id": tool_call["id"], "content": str(tool_result)},
            ]
            final_response = llm_with_tools.invoke(messages)
            answer = final_response.content
        else:
            # LLM 直接回答，不需要呼叫 Tool
            answer = ai_message.content

        copilot_response = CopilotResponse(answer=answer, tool_used=tool_used)
        return {"copilot_result": copilot_response}

    except Exception as e:
        return {"error_messages": [f"copilot_node 失敗：{e}"]}