from fastapi import APIRouter, HTTPException
from app.models.salary_schemas import SalaryCheckRequest, SalaryCheckResponse
from app.services.salary_service import check_salary


router = APIRouter()


@router.post("/check-salary", response_model=SalaryCheckResponse)
def salary_endpoint(request: SalaryCheckRequest):
    """
    根據職稱、產業、公司規模、年資、學歷與 JD 文字，
    推估市場薪資區間並判斷薪資競爭力。
    所有輸入欄位來自上游模組 session_state，HR 不需額外填寫。
    """
    try:
        return check_salary(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))