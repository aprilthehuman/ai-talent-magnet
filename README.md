# 🧲 AI Talent Magnet

> 一個幫企業提升招募吸引力的 AI 系統，從被動等履歷轉為主動提升職缺競爭力。

**作者：** April ｜ **版本：** v1.6.1 ｜ **開發狀態：** Phase 3 ✅ 完成（全部 7 個模組實作完畢）

---

## 專案背景

傳統招募工具多聚焦在「履歷篩選」，但台灣中小企業的真實痛點是在候選人決定是否投遞之前就已流失人才。AI Talent Magnet 從招募前端切入，協助企業在發布職缺前就提升 JD 吸引力、理解候選人視角，並透過 AI 自動化串聯整個優化流程。

本專案結合 **HR domain knowledge + AI 工程技術**，展示人資背景轉型 AI Application Engineer 的實務能力。

---

## 模組架構（v1.6.1，共 7 個模組）

| 模組 | 功能 | 狀態 |
|------|------|------|
| **A** JD Attraction Analyzer | 分析 JD 吸引力，找出降低投遞率的問題 | ✅ 已完成 |
| **B** JD Rewrite AI | 根據 Company Profile 產出三種風格的改寫版本 | ✅ 已完成 |
| **C** Salary Competitiveness Detector | AI 混合模式評估薪資市場競爭力 | ✅ 已完成 |
| **D** Candidate Persona Generator | 反推理想候選人樣貌、動機與溝通方式 | ✅ 已完成 |
| **E** AI Sourcing Assistant | 生成五種平台 Boolean search string 與通用破冰訊息，降低主動 sourcing 門檻 | ✅ 已完成 |
| **F** HR Knowledge Copilot | RAG + Rule-based dispatch，自然語言查詢勞基法、員工資料與假別餘額 | ✅ 已完成 |
| **G** AI Orchestration Agent | LangGraph Structured Workflow，一句話自動觸發完整 JD 優化流程 | ✅ 已完成 |

---

## 技術架構

```
前端    Streamlit（MVP）
後端    FastAPI + Uvicorn
AI 模型  OpenAI GPT-4o-mini
框架    LangChain + LangGraph（Module F、G）
向量庫  ChromaDB（Module F）
資料驗證 Pydantic v2
語言    Python 3.11
```

---

## 專案結構

```
portfolio/
├── requirements.txt
├── .env                             # API Key（不納入版控）
├── .env.example                     # API Key 範本
├── data_raw/                        # 政府開放資料原始檔（Module C ETL 用）
│   ├── 勞動部職類別薪資調查.xlsx
│   ├── 表1-各業受僱員工全年總薪資統計－按性別及教育程度分.xlsx
│   └── 表3-各業受僱員工全年總薪資統計－按員工規模別分.xlsx
├── scripts/
│   ├── prepare_data.py              # Module C ETL：將 xlsx 轉為 CSV 查詢表
│   └── build_vector_store.py        # 建立 ChromaDB 向量資料庫（Module F 初始化用）
├── frontend/
│   ├── 🏠_首頁.py                   # Streamlit 首頁
│   └── pages/
│       ├── ❶_ JD 吸引力分析.py      # Module A 介面
│       ├── ❷_ JD改寫.py             # Module B 介面
│       ├── ❸_ 候選人 Persona.py     # Module D 介面
│       ├── ❹_ 薪資競爭力分析.py     # Module C 介面
│       ├── ❺_ Sourcing助手.py       # Module E 介面
│       ├── ❻_ HR知識助手.py         # Module F 介面
│       └── ❼_ AI招募助手.py         # Module G 介面
└── app/
    ├── main.py                      # FastAPI 主程式，掛載所有 Router
    ├── config.py                    # 路徑與向量庫設定
    ├── data/                        # ETL 產出的 CSV 查詢表（Module C）
    │   ├── mol_occupation.csv
    │   ├── dgbas_education.csv
    │   ├── dgbas_company_size.csv
    │   └── employees/               # 模擬員工資料（Module F）
    │       ├── employees.csv
    │       ├── leave_records.csv
    │       └── salary_records.csv
    ├── knowledge/                   # RAG 知識庫來源文件（Module F）
    │   ├── labor_law.md
    │   ├── leave_policy.md
    │   └── recruitment_policy.md
    ├── vector_store/                # ChromaDB 向量資料庫（自動產生，不納入版控）
    ├── core/
    │   ├── keyword_dicts.py         # 負面詞彙、模糊用語字典（A）+ 職稱同義詞字典（E）
    │   └── prompts/
    │       └── sourcing_prompts.py  # Module E Prompt templates
    ├── routers/
    │   ├── analyzer.py              # Module A
    │   ├── rewriter.py              # Module B
    │   ├── salary.py                # Module C
    │   ├── persona.py               # Module D
    │   ├── sourcing.py              # Module E
    │   ├── copilot.py               # Module F
    │   └── agent.py                 # Module G
    ├── models/
    │   ├── analyzer_schemas.py      # Module A
    │   ├── rewriter_schemas.py      # Module B（含 CompanyProfile）
    │   ├── salary_schemas.py        # Module C
    │   ├── persona_schemas.py       # Module D（含 EducationPreference）
    │   ├── sourcing_schemas.py      # Module E
    │   ├── copilot_schemas.py       # Module F
    │   └── agent_schemas.py         # Module G（AgentRequest / AgentResponse）
    ├── services/
    │   ├── analyzer_service.py      # Module A 商業邏輯
    │   ├── rewriter_service.py      # Module B 商業邏輯
    │   ├── salary_service.py        # Module C 商業邏輯
    │   ├── persona_service.py       # Module D 商業邏輯
    │   ├── sourcing_service.py      # Module E 商業邏輯
    │   └── copilot_service.py       # Module F（RAG / 員工查詢 / 假別計算）
    └── orchestration/               # Module G：LangGraph Structured Workflow
        ├── agent_state.py           # AgentState TypedDict
        ├── agent_service.py         # Workflow 主邏輯（節點定義 + StateGraph）
        ├── tools.py                 # Orchestration Layer（包裝 Service 函數）
        └── evaluations/
            ├── eval_cases.py        # 8 個測試案例（涵蓋所有路由路徑）
            └── run_evals.py         # Eval 執行器
```

---

## 安裝與執行

### 環境需求

- Python 3.11
- Conda（建議使用 Miniconda）

### 安裝步驟

```bash
# 1. Clone 專案
git clone https://github.com/aprilthehuman/ai-talent-magnet.git
cd ai-talent-magnet

# 2. 建立 conda 環境
conda create -n talent-magnet python=3.11
conda activate talent-magnet

# 3. 安裝套件
pip install -r requirements.txt

# 4. 設定 API Key
cp .env.example .env
# 在 .env 填入你的 OPENAI_API_KEY

# 5. 初始化 Module C 薪資資料（首次執行需要）
python scripts/prepare_data.py

# 6. 初始化 Module F 知識庫（首次執行需要）
python scripts/build_vector_store.py
```

### 選填：啟用 LangSmith 追蹤（Module G）

在 `.env` 加入以下設定可追蹤 Module G 的 Workflow 執行記錄：

```
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_api_key
LANGCHAIN_PROJECT=ai-talent-magnet
```

### 啟動後端

```bash
uvicorn app.main:app --reload
```

API 文件：http://localhost:8000/docs

### 啟動前端

```bash
streamlit run frontend/🏠_首頁.py
```

前端介面：http://localhost:8501

---

## Module A — JD Attraction Analyzer

**功能：** 分析 JD 吸引力，找出降低候選人投遞意願的問題。

**API：** `POST /api/v1/analyze-jd`

**請求範例：**
```json
{
  "job_title": "Python Backend Engineer",
  "job_description_text": "職缺描述全文...",
  "company_type": "startup",
  "industry": "SaaS",
  "seniority_level": "mid"
}
```

**回應欄位：**

| 欄位 | 類型 | 說明 |
|------|------|------|
| `attraction_score` | int (0–100) | 綜合吸引力分數 |
| `score_label` | string | 優良 / 普通 / 偏低 / 危險 |
| `tone_analysis` | string | 80–100 字語氣分析 |
| `negative_keywords_detected` | array | 偵測到的負面詞彙 |
| `vague_phrases_detected` | array | 偵測到的模糊用語 |
| `missing_elements` | array | JD 缺失的重要資訊 |
| `improvement_suggestions` | array | 3 條改善建議（【問題】→【原因】→【建議】格式） |

**評分邏輯：** 規則層（0–60 分）+ AI 層（0–40 分）混合評分。規則層依負面詞彙、模糊用語、缺失項目扣分；AI 層評估語氣整體感受與候選人視角。

---

## Module B — JD Rewrite AI

**功能：** 根據 Company Profile 與原始 JD，產出 3 種風格的改寫版本，HR 選定後帶入 Module D。

**API：** `POST /api/v1/rewrite-jd`

**三種改寫風格：**

| 風格 | 適合對象 | 強調訴求 |
|------|----------|----------|
| Startup 風 | 新創、快速成長團隊 | Ownership、影響力、彈性 |
| 穩定企業風 | 中大型企業、傳產數位化 | 制度、福利、穩定發展 |
| 高成長挑戰型 | SaaS、AI 公司 | 技術深度、學習、快速升級 |

**Guardrail 機制：** 輸出後掃描 `must_avoid` 詞彙，若出現則在文末附上警告提示；`must_include` 注入 prompt，由 LLM 負責自然融入改寫結果。

---

## Module C — Salary Competitiveness Detector

**功能：** 比對政府開放薪資資料，評估職缺薪資的市場競爭力。

**API：** `POST /api/v1/check-salary`

**資料來源：**
- 勞動部職類別薪資調查（114 年，均值）
- 主計總處表 1（113 年，按性別及教育程度，中位數）
- 主計總處表 3（113 年，按員工規模別，中位數）

**回應欄位：**

| 欄位 | 類型 | 說明 |
|------|------|------|
| `market_salary_range` | object | P25 / median / P75 三值 |
| `competitiveness_level` | string | 五級中文評級 |
| `confidence_level` | string | high / medium / low |
| `reasoning` | string | 評估說明 |
| `suggestions` | array | 薪資調整建議 |
| `data_sources` | string | 引用的資料來源說明 |

---

## Module D — Candidate Persona Generator

**功能：** 整合 Module A 與 Module B 的輸出，反推理想候選人樣貌，幫助 HR 理解在吸引什麼樣的人、怎麼跟他們溝通。

**API：** `POST /api/v1/generate-persona`

**設計說明：** Module D 要求帶入 Module B 選定的改寫版本與 Company Profile，確保 Persona 反映公司真正的文化與期待。HR 可選填學歷參考條件（`education_preference`），系統原樣帶出至 Module E。

**模組資料流：** A（job_title、company_type、industry、seniority_level）→ B（company_profile、改寫 JD）→ D（education_preference）→ E

---

## Module E — AI Sourcing Assistant

**功能：** 將 Module D 的候選人 Persona 轉換為可執行的 sourcing 工具，包含五種平台 Boolean search string 與通用破冰聯繫訊息。

**API：** `POST /api/v1/generate-sourcing`

**設計說明：** Boolean string 由純 Python 邏輯組裝（不呼叫 LLM），outreach 訊息與 sourcing_tips 由 LLM 生成。職稱同義詞字典採雙層查詢：正向字典 + 反向索引，查無時 fallback 至 LLM 即時展開。

**回應欄位：**

| 欄位 | 說明 |
|------|------|
| `boolean_string_linkedin` | LinkedIn 內建搜尋語法 |
| `boolean_string_google_linkedin` | Google X-Ray 搜尋 LinkedIn（免費） |
| `boolean_string_cake` | CakeResume 內建搜尋語法 |
| `boolean_string_google_cake` | Google X-Ray 搜尋 CakeResume（免費） |
| `boolean_string_google_104` | Google X-Ray 搜尋 104 |
| `outreach_message_template` | 通用破冰聯繫訊息（100 字以內） |
| `sourcing_tips` | 針對此職缺的實戰 sourcing 建議 |

---

## Module F — HR Knowledge Copilot

**功能：** 自然語言查詢 HR 知識庫，支援勞基法規定、公司政策、員工基本資料與假別餘額三種查詢情境。

**API：** `POST /api/v1/copilot/query`

**三個 LangChain Tool：**

| Tool | 觸發條件 | 說明 |
|------|----------|------|
| `rag_search` | 勞基法、請假流程、公司政策等問題 | 查詢 ChromaDB 向量資料庫，LLM 合成結論 |
| `lookup_employee` | 含員工姓名或工號 + 員工相關關鍵字 | 查詢 employees.csv，回傳部門、薪資、到職日等 |
| `calculate_leave` | 含員工姓名或工號 + 假別相關關鍵字 | 查詢 leave_records.csv，依勞基法第 38 條計算特休餘額 |

**dispatch 設計：** Rule-based dispatch（不呼叫 LLM 做意圖判斷），jieba 中文斷詞萃取人名（Layer 1）+ regex lookahead fallback（Layer 2）。

**初始化知識庫：**
```bash
python scripts/build_vector_store.py
```

---

## Module G — AI Orchestration Agent

**功能：** 以自然語言一句話觸發完整 JD 優化流程，LangGraph Structured Workflow 自動串聯各模組並整合輸出報告。

**API：** `POST /api/v1/run-agent`

**架構：** LangGraph Structured Workflow（固定節點 + 條件邊），非 ReAct Agent。選擇 Structured Workflow 的原因：JD 優化流程步驟固定、可寫 eval 驗證、無不必要的 LLM 推理成本。

**執行流程：**

```
有 JD 輸入：
analyze_node → rewrite_node → persona_node → branch_node
                                                ↙     ↓     ↓     ↘
                                           salary sourcing both  none
                                                ↘     ↓     ↓     ↙
                                                  synthesize_node

無 JD 輸入（純諮詢）：
copilot_node → synthesize_node
```

**branch_node 設計：** 關鍵字比對決定後續分支（薪資 / sourcing / both / none），取代 LLM 判斷，確保路由行為確定性。

**model_validator：** 提供 `jd_text` 時，`company_profile` 為必填，在資料進入系統前攔截錯誤。

**評估系統：** 8 個 eval cases 涵蓋所有路由路徑，執行結果 **8/8 PASS**。

```bash
# 執行評估
python -m app.orchestration.evaluations.run_evals
```

**請求範例：**
```json
{
  "user_input": "幫我分析這份JD，並確認薪資75K是否有競爭力",
  "job_title": "Python Backend Engineer",
  "jd_text": "...",
  "company_profile": {
    "company_name": "Acme SaaS",
    "culture_keywords": ["透明", "扁平", "快速迭代"]
  }
}
```

---

## 開發說明

### 技術決策亮點

- **混合評分架構** — Module A 採規則層 + AI 層，避免完全依賴 LLM 造成不穩定
- **Pydantic v2 跨欄位驗證** — Module G 使用 `model_validator(mode="after")`，在 API 入口攔截不合法的參數組合
- **Structured Workflow 取代 ReAct** — 流程固定的場景用 Structured Workflow，可預測、可測試、無額外 LLM 推理成本
- **關鍵字路由取代 LLM 路由** — branch_node 用關鍵字比對，零 API 成本，行為確定性高
- **Orchestration Layer 分層解耦** — tools.py 作為適配器層，Service 層不知道 Workflow 存在，Workflow 不直接 import Service
- **Prompt 層分離** — Module E 的 prompt 獨立於 `sourcing_prompts.py`，service 層只負責組裝與呼叫
- **Rule-based dispatch** — Module F 不用 LLM 做意圖判斷，jieba NER + regex fallback，兼顧效能與準確率
- **RAG 相關性門檻過濾** — Module F 低於 0.5 的文件不顯示於參考資料，避免雜訊干擾
- **Schema 複用** — Module D import `CompanyProfile`；Module E import `EducationPreference`，避免重複定義
- **同步函式統一** — 所有 router endpoint 使用 `def`，避免阻塞事件迴圈

### 開發階段規劃

```
Phase 1（✅ 完成）：Module A、B、D + Streamlit 前端
Phase 2（✅ 完成）：Module C、E + Streamlit 前端
Phase 3（✅ 完成）：Module F（Hybrid RAG）、Module G（LangGraph Structured Workflow）
Phase 4（待啟動）：Docker 容器化 + Railway 部署
```

---

## 資料誠信聲明

本專案在所有涉及資料輸出的地方，都標註 confidence level 並提供 disclaimer，不假裝擁有完整資料集。Module C 的薪資參考資料來自政府開放資料（勞動部、主計總處），不使用爬蟲。Module F 使用的員工資料（employees.csv、leave_records.csv）為模擬資料，不含真實個資。

---

## 相關連結

- 📄 [企劃書 v1.6.1]（附於 repo 中）
- 🔗 API 文件：啟動後端後至 `http://localhost:8000/docs` 查看

---

*本專案為 AI Application Engineer 求職作品集，展示 HR domain knowledge 結合 AI 工程技術的實務能力。*
