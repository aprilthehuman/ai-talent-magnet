from fastapi import APIRouter
from app.models.persona_schemas import GeneratePersonaRequest, GeneratePersonaResponse
from app.services.persona_service import generate_persona


"""
模組 D：Candidate Persona Generator 路由
接收請求 → 呼叫 generate_persona() → 回傳結構化 Persona
本身不處理邏輯，只負責接收與轉發
"""

router = APIRouter()


@router.post("/generate-persona", response_model=GeneratePersonaResponse)
async def generate_persona_endpoint(request: GeneratePersonaRequest):
    return generate_persona(request)