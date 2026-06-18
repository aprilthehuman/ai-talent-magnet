from fastapi import FastAPI
from app.routers import analyzer, rewriter, persona, sourcing  # 加入 sourcing

"""
1. 建立 API 主程式(app)
2. 把不同功能模組接進來(router)
3. 定義一個測試用 endpoint(/)
"""

app = FastAPI(
    title="AI Talent Magnet",
    description="幫企業提升招募吸引力的 AI 系統",
    version="1.0"
)

# 模組 A：JD Attraction Analyzer
app.include_router(analyzer.router, prefix="/api/v1", tags=["Module A - JD Analyzer"])

# 模組 B：JD Rewrite AI
app.include_router(rewriter.router, prefix="/api/v1", tags=["Module B - JD Rewriter"])

# 模組 D：Candidate Persona Generator
app.include_router(persona.router, prefix="/api/v1", tags=["Module D - Persona Generator"])

# 模組 E：AI Sourcing Assistant
app.include_router(sourcing.router, prefix="/api/v1", tags=["Module E - Sourcing Assistant"])


@app.get("/")
def root():
    return {"message": "AI Talent Magnet API is running!"}