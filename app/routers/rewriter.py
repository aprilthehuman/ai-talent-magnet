from fastapi import APIRouter
from app.models.rewriter_schemas import RewriteJDRequest, RewriteJDResponse
from app.services.rewriter_service import rewrite_jd

"""
1. 匯入 FastAPI 的 APIRouter，建立模組 B 專屬的路由器
2. 匯入模組 B 的 Request / Response schema
3. 匯入模組 B 的服務層函式 rewrite_jd()
4. 定義 POST /rewrite-jd endpoint，接收請求、呼叫服務層、回傳改寫結果
"""

router = APIRouter()

@router.post("/rewrite-jd", response_model=RewriteJDResponse)
async def rewrite_jd_endpoint(request: RewriteJDRequest):
    """
    優化 JD 內容
    """
    return rewrite_jd(request)