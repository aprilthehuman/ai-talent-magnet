from fastapi import APIRouter, HTTPException
from app.models.analyzer_schemas import AnalyzeJDRequest, AnalyzeJDResponse
from app.services.analyzer_service import analyze_jd

router = APIRouter()

@router.post(
    "/analyze-jd", 
    response_model=AnalyzeJDResponse,
)

def analyze_jd_endpoint(request: AnalyzeJDRequest):
    """
    分析 JD 吸引力
    """
    try:
        result = analyze_jd(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))