from fastapi import APIRouter, HTTPException
from app.models.copilot_schemas import CopilotRequest, CopilotResponse
from app.services.copilot_service import dispatch_query


router = APIRouter()

@router.post("/copilot/query", response_model=CopilotResponse)
def copilot_query_endpoint(request: CopilotRequest):
    
    """
    HR 知識助手查詢。
    呼叫 dispatch_query() 以規則判斷問題類型，分派至 RAG 查詢、員工資料查詢或假別計算，回傳結構化結果。
    """
    
    try:
        result = dispatch_query(request.question)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))