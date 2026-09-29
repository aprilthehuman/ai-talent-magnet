"""
模組 G：AI Orchestration Agent
routers/agent.py — FastAPI Router

職責：
  - 定義 /run-agent POST endpoint
  - 接收 AgentRequest，呼叫 run_agent()，回傳 AgentResponse
  - 錯誤處理：捕捉 ValueError（輸入驗證錯誤）
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

    - parse_input_node 提取結構化欄位與 parsed_intent
    - clarify_node 判斷資訊是否充足，不足時回傳補問訊息
    - parsed_intent = hr_qa：執行 copilot → synthesize
    - parsed_intent = rewrite/salary/sourcing：執行 analyze→rewrite→persona→branch→[salary/sourcing]→synthesize
    """
    try:
        return run_agent(request)
    except ValueError as e:
        # AgentRequest 輸入驗證錯誤
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent 執行失敗：{e}")