from fastapi import APIRouter, HTTPException
from app.models.rewriter_schemas import RewriteJDRequest, RewriteJDResponse
from app.services.rewriter_service import rewrite_jd


router = APIRouter()

@router.post("/rewrite-jd", response_model=RewriteJDResponse)
def rewrite_jd_endpoint(request: RewriteJDRequest):
    
    """
    根據 Company Profile 與原始 JD，產出三種風格的改寫版本。
    呼叫 rewrite_jd() 進行 prompt 組裝與 LLM 生成，回傳結構化結果。
    """
    
    try:
        return rewrite_jd(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))