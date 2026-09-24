"""
Module G Evaluation Cases — v1.7 更新
定義 Agent 的測試情境，供 run_evals.py 執行與驗證。

評估面向：
  1. 路由正確性：branch_decision 是否符合預期
  2. steps_taken：實際執行的模組是否和預期一致
  3. error_messages：是否為空（無錯誤）
  4. final_report：是否包含關鍵字（基本品質檢查）
  5. parsed_intent：parse_input_node 提取的意圖是否正確（v1.7 新增）
  6. should_clarify：clarify_node 是否正確觸發補問（v1.7 新增）
  7. check_extracted_field：parse_input_node 是否正確提取欄位（v1.7 新增）

v1.7 變更說明：
  - C6 舊：model_validator 拋 ValueError（v1.7 company_profile 改選填，此 case 已不適用）
    C6 新：clarify_node 補問觸發（輸入資訊不足時應回覆補問訊息而非直接執行）
  - C7 舊：Module F 員工查詢
    C7 新：parse_input_node 欄位提取（從自然語言提取 company_profile 各欄位）
  - C8 舊：company_profile 夾帶 salary_min/max 傳遞給 Module C
    C8 新：parsed_intent 路由（使用者說「確認薪資競爭力」不含關鍵字，仍應 branch=salary）
"""

# 每個 case 結構：
#   id               : 測試編號
#   description      : 測試目的說明
#   input            : 傳給 run_agent() 的 AgentRequest dict
#   expected         : 預期結果（用於斷言）
#     steps_taken        : 預期執行的節點（set 比對）
#     report_contains    : final_report 應包含的關鍵字清單
#     branch_decision    : 預期的 branch_decision 值（選填）
#     parsed_intent      : 預期 parsed_intent 包含的字串（選填，v1.7）
#     should_clarify     : True 表示預期 clarification_needed=True（選填，v1.7）
#     extracted_field    : {欄位路徑: 預期值或 "非空"} 驗證提取結果（選填，v1.7）

EVAL_CASES = [

    # ── Case 1：Module F 路徑（無 JD，HR 知識問答）──────────────────
    {
        "id": "C1",
        "description": "無 JD，純 HR 知識問答 → 應走 Module F (copilot 路徑)",
        "input": {
            "user_input": "員工請特休需要提前幾天申請？",
        },
        "expected": {
            "steps_taken": ["copilot_query"],
            "report_contains": ["特休", "申請"],
        },
    },

    # ── Case 2：A→B→D only（不需要 C/E）────────────────────────────
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
            "branch_decision": "none",
            "report_contains": ["JD", "Persona", "候選人"],
        },
    },

    # ── Case 3：A→B→D→C（只需薪資分析）──────────────────────────────
    {
        "id": "C3",
        "description": "有 JD，要求薪資分析 → branch = salary，應執行 Module C",
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
            "branch_decision": "salary",
            "report_contains": ["薪資", "市場"],
        },
    },

    # ── Case 4：A→B→D→E（只需 Sourcing）──────────────────────────────
    {
        "id": "C4",
        "description": "有 JD，要求 Sourcing 策略 → branch = sourcing，應執行 Module E",
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
            "branch_decision": "sourcing",
            "report_contains": ["Sourcing", "渠道", "候選人"],
        },
    },

    # ── Case 5：A→B→D→C→E（both）──────────────────────────────────────
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
            "branch_decision": "both",
            "report_contains": ["薪資", "Sourcing", "候選人"],
        },
    },

    # ── Case 6（v1.7 更新）：clarify_node 補問觸發 ──────────────────
    # 舊 C6：model_validator 拋 ValueError（v1.7 已移除此驗證，company_profile 改為選填）
    # 新 C6：使用者只輸入極短文字，無法判斷意圖，clarify_node 應主動補問
    {
        "id": "C6",
        "description": "意圖無法判斷（user_input 極度簡短）→ clarify_node 應觸發補問，不直接執行",
        "input": {
            # 只給極短 user_input，parse_input_node 無法提取有效 intent
            "user_input": "幫我",
            "jd_text": "We are hiring.",
        },
        "expected": {
            # 預期 clarify_node 判斷需要補問，回傳補問訊息而非完整報告
            "should_clarify": True,
            # v1.7 clarify_node 回覆格式：intent 為空時回覆包含「不太確定」和「HR 知識問答」
            # JD 缺失時回覆包含「補充」和「繼續執行」
            # user_input="幫我" 預期 parse_input_node 抽不出有效 intent → 走 intent 為空分支
            "report_contains": ["不太確定", "HR"],
        },
    },

    # ── Case 7（v1.7 新增）：parse_input_node 欄位提取 ───────────────
    # 驗證 parse_input_node 能從自然語言中正確提取 company_profile 各欄位
    {
        "id": "C7",
        "description": "parse_input_node：從自然語言自動提取 company_name 與 culture_keywords",
        "input": {
            # 不手動傳 company_profile，讓 parse_input_node 從 user_input 提取
            "user_input": (
                "幫我分析這份後端工程師 JD，"
                "我們公司叫做測試科技，"
                "文化是研發驅動、扁平管理，"
                "薪資大概 70K-90K。"
            ),
            "jd_text": "尋找熟悉 Python 與 FastAPI 的後端工程師，3 年以上經驗。",
            # 故意不傳 company_profile，測試 parse_input_node 自動提取
        },
        "expected": {
            "steps_taken": ["analyze_jd", "rewrite_jd", "generate_persona"],
            # 驗證 parse_input_node 有正確提取欄位
            # extracted_field 的 key 為 response 中可驗證的欄位或 final_report 關鍵字
            "extracted_field": {
                "company_name_in_report": "測試科技",   # final_report 或摘要應提及公司名
                "salary_extracted": True,               # 70K-90K 應被提取為 salary_min/max
            },
            "report_contains": ["JD", "候選人"],
        },
    },

    # ── Case 8（v1.7 新增）：parsed_intent 路由辨識非關鍵字薪資意圖 ──
    # 驗證 parsed_intent 路由能辨識「不含『薪資』關鍵字」的薪資意圖
    # v1.6.1 關鍵字比對會 miss 這個 case（"薪資" 不在 user_input 中）
    {
        "id": "C8",
        "description": "parsed_intent 路由：使用者說「確認待遇有沒有競爭力」→ branch=salary（不含關鍵字）",
        "input": {
            "user_input": "幫我看一下這份 JD，並確認我們開出的待遇有沒有競爭力",
            # 注意：user_input 中不含「薪資」「薪水」等關鍵字
            # v1.6.1 關鍵字比對會 miss；v1.7 parsed_intent 應能正確辨識
            "job_title": "後端工程師",
            "jd_text": "尋找熟悉 Python 與 FastAPI 的後端工程師，3 年以上經驗。",
            "company_profile": {
                "company_name": "測試新創",
                "vision": "打造最好的 HR 工具",
                "culture_keywords": ["自驅", "透明"],
                "salary_min": 70000,
                "salary_max": 90000,
            },
        },
        "expected": {
            "branch_decision": "salary",   # 核心斷言：即使無「薪資」關鍵字也應路由到 salary
            "steps_taken": ["analyze_jd", "rewrite_jd", "generate_persona", "check_salary"],
            "parsed_intent": "salary",     # ← 修正：actual intent key 是 "salary"，不是 "check_salary"
            "report_contains": ["競爭", "市場"],
        },
    },
]