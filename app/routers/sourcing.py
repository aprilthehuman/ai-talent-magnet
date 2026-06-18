from fastapi import APIRouter, HTTPException
from app.models.sourcing_schemas import SourcingRequest, SourcingResult
from app.services.sourcing_service import generate_sourcing_result


"""
模組 E：AI Sourcing Assistant — Router 層
接收 HTTP POST 請求，呼叫 service 層處理，回傳結果。
不包含任何商業邏輯，只負責請求的接收與回傳。
"""


router = APIRouter()


@router.post("/generate-sourcing", response_model=SourcingResult)
def sourcing_endpoint(request: SourcingRequest):
    try:
        return generate_sourcing_result(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))