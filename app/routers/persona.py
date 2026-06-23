from fastapi import APIRouter, HTTPException
from app.models.persona_schemas import GeneratePersonaRequest, GeneratePersonaResponse
from app.services.persona_service import generate_persona


router = APIRouter()

@router.post("/generate-persona", response_model=GeneratePersonaResponse)
def generate_persona_endpoint(request: GeneratePersonaRequest):
    
    """
    根據選定的改寫 JD 與 Company Profile，反推理想候選人樣貌。
    呼叫 generate_persona() 進行 LLM 推論，回傳結構化 Persona。
    """
    
    try:
        return generate_persona(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))