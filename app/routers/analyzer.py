from fastapi import APIRouter, HTTPException
from app.models.analyzer_schemas import AnalyzeJDRequest, AnalyzeJDResponse
from app.services.analyzer_service import analyze_jd


router = APIRouter()

@router.post("/analyze-jd", response_model=AnalyzeJDResponse)
def analyze_jd_endpoint(request: AnalyzeJDRequest):
    
    """
    分析 JD 吸引力。
    呼叫 analyze_jd() 進行規則層 + AI 層混合評分，回傳結構化結果。
    """
    
    try:
        result = analyze_jd(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))