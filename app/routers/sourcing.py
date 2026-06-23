from fastapi import APIRouter, HTTPException
from app.models.sourcing_schemas import SourcingRequest, SourcingResult
from app.services.sourcing_service import generate_sourcing_result


router = APIRouter()

@router.post("/generate-sourcing", response_model=SourcingResult)
def sourcing_endpoint(request: SourcingRequest):
    
    """
    根據候選人 Persona 與職稱，生成 Boolean search string、平台推薦與外展訊息。
    呼叫 generate_sourcing_result() 進行字串組裝與 LLM 生成，回傳結構化結果。
    """
    
    try:
        return generate_sourcing_result(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))