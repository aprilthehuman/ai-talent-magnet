"""
Module G Evaluation Cases
定義 Agent 的測試情境，供 run_evals.py 執行與驗證。

評估面向：
  1. 路由正確性：branch_decision 是否符合預期
  2. steps_taken：實際執行的模組是否和預期一致
  3. error_messages：是否為空（無錯誤）
  4. final_report：是否包含關鍵字（基本品質檢查）
"""

# 每個 case 結構：
#   id          : 測試編號
#   description : 測試目的說明
#   input       : 傳給 run_agent() 的 AgentRequest dict
#   expected    : 預期結果（用於斷言）
#     steps_taken     : 預期執行的模組（順序不限）
#     report_contains : final_report 應包含的關鍵字清單

EVAL_CASES = [

    # ── Case 1：Module F 路徑（無 JD，HR 知識問答）──────────────
    {
        "id": "C1",
        "description": "無 JD，純 HR 知識問答 → 應走 Module F",
        "input": {
            "user_input": "員工請特休需要提前幾天申請？",
        },
        "expected": {
            "steps_taken": ["copilot_query"],
            "report_contains": ["特休", "申請"],
        },
    },

    # ── Case 2：A→B→D only（不需要 C/E）────────────────────────
    {
        "id": "C2",
        "description": "有 JD，只要求分析與 Persona → 應走 A→B→D，branch = none",
        "input": {
            "user_input": "幫我分析這份 JD 並生成候選人 Persona",
            "job_title": "後端工程師",
            "jd_text": "尋找熟悉 Python 與 FastAPI 的後端工程師，3 年以上經驗。",
            "company_profile": {
                "company_name": "測試新創",
                "vision": "打造最好的 HR 工具",
                "culture_keywords": ["自驅", "透明"],
                "industry_context": "HR SaaS",
            },
        },
        "expected": {
            "steps_taken": ["analyze_jd", "rewrite_jd", "generate_persona"],
            "report_contains": ["JD", "Persona", "候選人"],
        },
    },

    # ── Case 3：A→B→D→C（只需薪資分析）────────────────────────
    {
        "id": "C3",
        "description": "有 JD，要求薪資分析 → branch = salary，應執行 C",
        "input": {
            "user_input": "幫我分析這份 JD 並檢查薪資競爭力",
            "job_title": "後端工程師",
            "jd_text": "尋找熟悉 Python 與 FastAPI 的後端工程師，3 年以上經驗。",
            "company_profile": {
                "company_name": "測試新創",
                "vision": "打造最好的 HR 工具",
                "culture_keywords": ["自驅", "透明"],
                "industry_context": "HR SaaS",
            },
        },
        "expected": {
            "steps_taken": ["analyze_jd", "rewrite_jd", "generate_persona", "check_salary"],
            "report_contains": ["薪資", "市場"],
        },
    },

    # ── Case 4：A→B→D→E（只需 Sourcing）────────────────────────
    {
        "id": "C4",
        "description": "有 JD，要求 Sourcing 策略 → branch = sourcing，應執行 E",
        "input": {
            "user_input": "幫我生成候選人 Persona 和 Sourcing 策略",
            "job_title": "後端工程師",
            "jd_text": "尋找熟悉 Python 與 FastAPI 的後端工程師，3 年以上經驗。",
            "company_profile": {
                "company_name": "測試新創",
                "vision": "打造最好的 HR 工具",
                "culture_keywords": ["自驅", "透明"],
                "industry_context": "HR SaaS",
            },
        },
        "expected": {
            "steps_taken": ["analyze_jd", "rewrite_jd", "generate_persona", "generate_sourcing"],
            "report_contains": ["Sourcing", "渠道", "候選人"],
        },
    },

    # ── Case 5：A→B→D→C→E（both）───────────────────────────────
    {
        "id": "C5",
        "description": "有 JD，要求薪資 + Sourcing → branch = both，應執行 C 和 E",
        "input": {
            "user_input": "幫我分析 JD、生成 Persona，並分析薪資競爭力和 Sourcing 策略",
            "job_title": "後端工程師",
            "jd_text": "尋找熟悉 Python 與 FastAPI 的後端工程師，3 年以上經驗。",
            "company_profile": {
                "company_name": "測試新創",
                "vision": "打造最好的 HR 工具",
                "culture_keywords": ["自驅", "透明"],
                "industry_context": "HR SaaS",
            },
        },
        "expected": {
            "steps_taken": ["analyze_jd", "rewrite_jd", "generate_persona", "check_salary", "generate_sourcing"],
            "report_contains": ["薪資", "Sourcing", "候選人"],
        },
    },

    # ── Case 6：驗證 model_validator（有 JD 但無 company_profile）
    {
        "id": "C6",
        "description": "有 JD 但缺少 company_profile → AgentRequest 應拋出 ValueError",
        "input": {
            "user_input": "幫我分析這份 JD",
            "jd_text": "尋找熟悉 Python 的後端工程師。",
            # 故意不填 company_profile
        },
        "expected": {
            "should_raise": ValueError,  # 預期拋出例外，不進入 Agent
        },
    },

    # ── Case 7：Module F，員工查詢類問題────────────────────────
    {
        "id": "C7",
        "description": "查詢特定員工資料 → 應走 Module F，tool_used = lookup_employee",
        "input": {
            "user_input": "請問員工 E001 的基本資料是什麼？",
        },
        "expected": {
            "steps_taken": ["copilot_query"],
            "report_contains": ["員工"],
        },
    },

    # ── Case 8：完整情境，含額外欄位（salary_min/max）──────────
    {
        "id": "C8",
        "description": "company_profile 夾帶 salary_min/max → Module C 應使用該數值",
        "input": {
            "user_input": "幫我分析 JD 並檢查薪資是否有競爭力",
            "job_title": "後端工程師",
            "jd_text": "尋找熟悉 Python 與 FastAPI 的後端工程師，3 年以上經驗。",
            "company_profile": {
                "company_name": "測試新創",
                "vision": "打造最好的 HR 工具",
                "culture_keywords": ["自驅", "透明"],
                "industry_context": "HR SaaS",
                "salary_min": 70000,   # 額外夾帶，供 Module C 使用
                "salary_max": 100000,
            },
        },
        "expected": {
            "steps_taken": ["analyze_jd", "rewrite_jd", "generate_persona", "check_salary"],
            "report_contains": ["薪資", "市場"],
        },
    },
]