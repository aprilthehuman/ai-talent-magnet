"""
模組 G：AI Orchestration Agent
routers/agent.py — FastAPI Router

職責：
  - 定義 /run-agent POST endpoint
  - 接收 AgentRequest，呼叫 run_agent()，回傳 AgentResponse
  - 錯誤處理：捕捉 ValueError（來自 AgentRequest model_validator）
    與非預期例外，回傳對應的 HTTP 狀態碼
"""

from fastapi import APIRouter, HTTPException

from app.models.agent_schemas import AgentRequest, AgentResponse
from app.orchestration.agent_service import run_agent


router = APIRouter()


@router.post("/run-agent", response_model=AgentResponse)
def run_agent_endpoint(request: AgentRequest):
    """
    Agent 執行端點。

    - 有 jd_text：執行 A→B→D，依 user_input 決定是否加跑 C / E，最終整合報告
    - 無 jd_text：執行 Module F（HR 知識問答），最終整合報告
    """
    try:
        return run_agent(request)
    except ValueError as e:
        # AgentRequest model_validator 拋出的驗證錯誤
        # 例：有 jd_text 但缺少 company_profile
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent 執行失敗：{e}")