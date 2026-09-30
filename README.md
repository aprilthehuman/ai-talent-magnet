# AI Talent Magnet — 人才吸引引擎

> 一個幫企業提升招募吸引力的 AI 系統，從被動等履歷轉為主動提升職缺競爭力。

**版本：** v1.7 | **作者：** April | **更新：** 2026-09

---

## 專案背景

傳統招募工具多半聚焦「履歷篩選」，但台灣中小企業的真實痛點是在履歷投遞**前**就流失候選人。本專案從招募前端切入，協助企業在候選人決定是否投遞之前，先提升職缺本身的吸引力。

本專案結合 HR domain knowledge + AI 工程技術，展示人資背景轉型 AI Application Engineer 的實務能力。

---

## 功能模組總覽

| 模組 | 名稱 | 核心功能 |
|------|------|----------|
| A | JD Attraction Analyzer | 分析 JD 吸引力，找出降低投遞意願的問題 |
| B | JD Rewrite AI | 根據 Company Profile 自動產出三種風格改寫版本 |
| C | Salary Competitiveness Detector | 比對官方薪資統計，給出競爭力判斷與建議 |
| D | Candidate Persona Generator | 反推理想候選人樣貌、動機、顧慮、溝通偏好 |
| E | AI Sourcing Assistant | 生成 Boolean search string、Outreach 訊息、Sourcing 建議 |
| F | HR Knowledge Copilot | 自然語言查詢勞動法規、公司制度與員工個人資料 |
| G | AI Orchestration Agent | LangGraph Structured Workflow，一句話觸發完整流程 |

---

## 核心使用流程

```
JD 輸入
  ↓
[模組 A] 吸引力分析
  ↓
[模組 B] JD 改寫（三種風格）→ HR 選定版本
  ↓
[模組 D] 候選人 Persona 生成
  ↓        ↓
[模組 C]  [模組 E]        ← 平行分支，順序不拘
薪資競爭力  Sourcing 語法

[模組 F] HR 知識助手 ← 隨時獨立使用
[模組 G] AI Agent    ← 以上所有流程的自然語言入口
```

---

## 技術架構

### 技術選型

| 層 | 技術 | 說明 |
|----|------|------|
| 前端 | Streamlit | 快速開發、適合 demo |
| 後端 | FastAPI | 自動產生 API 文件、Pydantic 整合 |
| AI 模型 | OpenAI GPT-4o-mini | 便宜、快、夠用 |
| Embedding | OpenAI text-embedding-3-small | 用於 RAG 向量化 |
| Vector DB | ChromaDB | 輕量、本地持久化 |
| LLM 框架 | LangChain + LangGraph | Tool-calling + StateGraph |
| Agent 追蹤 | LangSmith | LLM 追蹤與 Workflow 除錯 |
| 資料處理 | pandas | 官方資料 ETL + 員工 CSV 查詢 |
| 部署 | Docker + Railway | 簡單、免費額度夠用 |

### 四層架構

```
展示層        Streamlit（7 個模組操作頁 + 1 個 Agent 對話頁）
               ↕ HTTP
Orchestration  LangGraph Structured Workflow + Orchestration Tools
層             （模組 G 使用；模組 A–F 的 Streamlit 頁面繼續走 HTTP）
               ↕ 直接呼叫 Service 函數
服務層         FastAPI（7 個 API endpoints）+ ChromaDB（RAG）
               ↕
資料層         官方薪資 CSV × 3、員工模擬 CSV × 3、knowledge/ 文件 × 3
```

---

## 專案結構

```
app/
├── config.py                      # 全域設定（API 金鑰、ChromaDB 路徑、chunk 參數）
├── main.py                        # FastAPI 主程式，掛載所有 router
├── core/
│   ├── keyword_dicts.py           # 職稱同義詞字典、負面詞彙、模糊用語
│   └── prompts/
│       └── sourcing_prompts.py    # 模組 E 的 Prompt 模板
├── models/                        # Pydantic v2 Schema（Request / Response）
│   ├── analyzer_schemas.py
│   ├── rewriter_schemas.py
│   ├── persona_schemas.py
│   ├── salary_schemas.py
│   ├── sourcing_schemas.py
│   ├── copilot_schemas.py
│   └── agent_schemas.py
├── routers/                       # HTTP 路由層（Streamlit 呼叫用）
│   ├── analyzer.py
│   ├── rewriter.py
│   ├── persona.py
│   ├── salary.py
│   ├── sourcing.py
│   ├── copilot.py                 # 模組 F
│   └── agent.py                   # 模組 G
├── services/                      # 業務邏輯層
│   ├── analyzer_service.py
│   ├── rewriter_service.py
│   ├── persona_service.py
│   ├── salary_service.py
│   ├── sourcing_service.py
│   └── copilot_service.py         # RAG / 員工查詢 / 特休計算三個工具
├── orchestration/                 # Orchestration Layer（模組 G 專用）
│   ├── agent_state.py             # AgentState TypedDict
│   ├── agent_service.py           # LangGraph Structured Workflow 主邏輯
│   ├── tools.py                   # 適配器層（包裝 Service 函數供 Workflow 呼叫）
│   └── evaluations/
│       ├── eval_cases.py          # 8 個測試案例（涵蓋所有路由路徑）
│       └── run_evals.py           # 評估執行器
├── knowledge/                     # 模組 F RAG 知識庫文件
│   ├── labor_law.md               # 勞基法重點條文
│   ├── leave_policy.md            # 公司請假制度
│   └── recruitment_policy.md     # 公司招募制度
├── data/                          # 靜態資料
│   ├── mol_occupation.csv         # 勞動部職類別薪資（ETL 輸出）
│   ├── dgbas_education.csv        # 主計總處表1：產業×學歷薪資（ETL 輸出）
│   ├── dgbas_company_size.csv     # 主計總處表3：產業×規模薪資（ETL 輸出）
│   └── employees/                 # 模組 F 員工模擬資料
│       ├── employees.csv          # 20 筆員工基本資料
│       ├── leave_records.csv      # 78 筆請假紀錄
│       └── salary_records.csv     # 160 筆薪資紀錄
└── vector_store/                  # ChromaDB 持久化儲存（模組 F）

frontend/                          # Streamlit 前端
├── 🏠_首頁.py                     # 首頁與導覽
└── pages/
    ├── ❶_ JD 吸引力分析.py        # 模組 A
    ├── ❷_ JD改寫.py               # 模組 B
    ├── ❸_ 候選人 Persona.py        # 模組 D
    ├── ❹_ 薪資競爭力分析.py        # 模組 C
    ├── ❺_ Sourcing助手.py         # 模組 E
    ├── ❻_ HR知識助手.py            # 模組 F
    └── ❼_ AI招募助手.py            # 模組 G

scripts/
├── prepare_data.py                # 官方薪資 Excel → 標準化 CSV（模組 C ETL）
└── build_vector_store.py          # 知識庫文件向量化並存入 ChromaDB（模組 F）

data_raw/                          # 原始政府統計 Excel（不進版控）
├── 勞動部職類別薪資調查.xlsx
├── 表1-各業受僱員工全年總薪資統計－按性別及教育程度分.xlsx
└── 表3-各業受僱員工全年總薪資統計－按員工規模別分.xlsx
```

---

## 各模組詳細說明

### 模組 A：JD Attraction Analyzer

**輸入**

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `job_title` | string | ✅ | 職稱 |
| `job_description_text` | string | ✅ | 完整 JD 文字 |
| `company_type` | string | — | startup / SME / enterprise |
| `industry` | string | — | 例：SaaS / 電商 / 金融 |
| `seniority_level` | string | — | junior / mid / senior |
| `salary_min` | int | — | JD 薪資下限（月薪，元）|
| `salary_max` | int | — | JD 薪資上限（月薪，元）|

**輸出**

| 欄位 | 類型 | 說明 |
|------|------|------|
| `attraction_score` | int (0–100) | 綜合吸引力分數 |
| `score_label` | string | 優良 / 普通 / 偏低 / 危險 |
| `tone_analysis` | string | 80–100 字語氣分析 |
| `negative_keywords_detected` | array | 偵測到的負面詞彙 |
| `vague_phrases_detected` | array | 偵測到的模糊用語 |
| `missing_elements` | array | 缺失的重要資訊（含扣分數）|
| `improvement_suggestions` | array | 3 條改善建議 |

**分數邏輯：** 規則層（最高 60 分）+ AI 層（最高 40 分）混合評分。

---

### 模組 B：JD Rewrite AI

根據 Company Profile 產出三種風格改寫版本（Startup 風 / 穩定企業風 / 高成長挑戰型）。

**v1.7 更新：** `company_profile` 改為選填；三個子欄位（`company_name`、`culture_keywords`、`vision`）未填時以「（未提供）」代替，改寫仍可執行。

**輸入**

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `original_jd` | string | ✅ | 原始 JD 文字 |
| `company_profile` | object | — | 公司設定檔（見下） |
| `target_candidate_focus` | string | — | 想吸引的候選人特質 |

**Company Profile 欄位**

| 欄位 | 說明 |
|------|------|
| `company_name` | 公司名稱 |
| `culture_keywords` | 企業文化關鍵字，例：`["透明", "扁平"]` |
| `vision` | 公司願景 |
| `manager_style` | 主管風格 |
| `tone_preference` | 語氣偏好：formal / casual / energetic / professional |
| `must_include` | 必須帶到的訊息清單 |
| `must_avoid` | 絕對不能出現的詞清單 |
| `industry_context` | 產業背景補充 |

**輸出**

| 欄位 | 類型 | 說明 |
|------|------|------|
| `startup_version` | string | 新創風改寫版本 |
| `stable_enterprise_version` | string | 穩定企業風改寫版本 |
| `high_growth_version` | string | 高成長挑戰型改寫版本 |
| `rewrite_notes` | array | 改寫重點說明（3 條，每個版本一條）|
| `profile_applied` | object | 實際套用的 Profile 摘要（供驗證用）|

---

### 模組 C：Salary Competitiveness Detector

**資料來源（官方開放資料，v1.5.4 改版）**

| 資料集 | 來源 | 統計方式 | 用途 |
|--------|------|----------|------|
| 勞動部職類別薪資調查（114 年）| 勞動部 | 平均數 | 職類別月薪基準 |
| 主計總處表 1（按性別及教育程度）| 主計總處 | 中位數 | 產業 × 學歷修正 |
| 主計總處表 3（按員工規模別）| 主計總處 | 中位數 | 產業 × 規模修正 |

ETL 腳本：`scripts/prepare_data.py` → 輸出 `app/data/` 底下三份標準化 CSV。

**設計決策：官方資料 + LLM 語意映射**

職稱（如 "Python Backend Engineer"）與官方職類分類之間沒有直接對照表，故讓 LLM 做語意映射，Python 只負責把完整官方分類清單整理成參考文字餵給 LLM。

**三層評估架構**

1. **Python 規則層：** `extract_jd_salary()` 用正規表示式從 JD 解析已揭露薪資
2. **Python 查詢層：** `build_salary_context()` 從三份官方資料撈出參考數字
3. **LLM 推估層：** 職稱/產業語意映射 + 推估 P25/中位數/P75 + 競爭力等級

**輸出欄位**

| 欄位 | 類型 | 說明 |
|------|------|------|
| `market_salary_range` | object | 市場薪資區間，含 `p25_monthly`、`median_monthly`、`p75_monthly`（月薪，元）|
| `competitiveness_level` | string | 高度競爭 / 具競爭力 / 普通 / 偏低 / 明顯偏低 |
| `competitiveness_reason` | string | 60–100 字判斷理由 |
| `salary_suggestion` | string | 60–100 字具體建議 |
| `data_sources` | string | 實際引用的資料來源說明 |
| `confidence_level` | string | high / medium / low |
| `confidence_reason` | string | 40–60 字可信度說明 |
| `disclaimer` | string | 資料限制與使用提醒 |

---

### 模組 D：Candidate Persona Generator
根據模組 B 選定的改寫 JD 與 Company Profile，反推理想候選人樣貌。

**v1.7 更新：** `company_profile` 改為選填；未提供時 service 層以 `CompanyProfile()` 空物件 fallback，LLM 用通用語氣生成 Persona。

**Output（`GeneratePersonaResponse`）：**
- `job_title`：職稱（從模組 A 帶入）
- `persona`（`CandidatePersona`）：
  - `ideal_seniority`：理想年資區間，例：3–5 年
  - `likely_background`：可能的職涯背景（`list[str]`）
  - `key_skills`：核心技能清單（`list[str]`）
  - `candidate_motivators`：在意的面向，例：技術自主性、WLB（`list[str]`）
  - `likely_concerns`：可能的顧慮，例：公司穩定性（`list[str]`）
  - `preferred_message_style`：建議 HR 與此類候選人溝通的語氣風格
  - `likely_channels`：可能出現的平台，例：LinkedIn、CakeResume（`list[str]`）
- `education_preference`：原樣帶出 HR 填寫的學歷條件，供模組 E 直接接收（選填）

---

### 模組 E：AI Sourcing Assistant

**核心功能：** 職稱同義展開、多平台 Boolean search string、Outreach 訊息模板、Sourcing 建議。

**Boolean Search 涵蓋平台**

| 欄位 | 說明 |
|------|------|
| `boolean_string_linkedin` | LinkedIn 內建搜尋語法 |
| `boolean_string_google_linkedin` | Google X-Ray 搜尋 LinkedIn 公開頁面 |
| `boolean_string_cake` | CakeResume 內建搜尋語法 |
| `boolean_string_google_cake` | Google X-Ray 搜尋 CakeResume 公開履歷 |
| `boolean_string_google_104` | Google X-Ray 搜尋 104 公開頁面 |

**其他輸出**

| 欄位 | 型別 | 說明 |
|------|------|------|
| `expanded_titles` | `list[str]` | 職稱同義展開結果 |
| `outreach_message_template` | `str` | AI 生成破冰聯繫訊息（100 字以內，結尾開放式問句）|
| `sourcing_tips` | `list[str]` | AI 生成 Sourcing 建議 |

**實作亮點：** 四層職稱展開機制（反向索引 → 正向完整比對 → 部分比對 → LLM 即時 fallback）；字典四層皆查無結果時才呼叫 LLM，兼顧速度與準確率。

---

### 模組 F：HR Knowledge Copilot

讓 HR 用自然語言查詢三類問題：勞動法規/公司制度（RAG）、員工個人資料（結構化查詢）、以及假別餘額計算（確定性 Python 計算）。

**dispatch 設計：Rule-based（不呼叫 LLM 做意圖判斷）**

```
有員工編號（5位數）＋假別關鍵字 → calculate_leave
有假別關鍵字＋jieba 萃取到人名 → calculate_leave
有員工關鍵字（員工/職稱/部門/薪資等）→ lookup_employee
其餘 → rag_search
```

此路由完全由 regex + 關鍵字集合比對完成，不消耗 API 費用，行為確定。

**三個工具**

| Tool | 功能 | 底層實作 |
|------|------|----------|
| `rag_search(query)` | 搜尋法規與公司制度 | ChromaDB 向量搜尋 |
| `lookup_employee(identifier)` | 查詢員工基本資料 | Pandas CSV 查詢 |
| `calculate_leave(identifier)` | 計算各假別使用情況與剩餘天數 | Python 確定性計算 |

**關鍵設計原則：計算不交給 LLM，只交給 Python。**
特休天數、薪資加總等數值計算由 Python 函數完成後，LLM 只負責組合自然語言回答。

**知識庫（非結構化 → ChromaDB）**

| 檔案 | 內容 | 切片策略 |
|------|------|----------|
| `labor_law.md` | 勞基法重點條文（特休第 38 條、試用期、各類假別）| chunk=500, overlap=50 |
| `leave_policy.md` | 公司請假制度 | chunk=500, overlap=50 |
| `recruitment_policy.md` | 公司招募制度 | chunk=500, overlap=50 |

**員工資料（結構化 → CSV）**

| 檔案 | 說明 |
|------|------|
| `employees.csv` | 20 位員工（employee_id、姓名、部門、職稱、到職日、月薪）|
| `leave_records.csv` | 78 筆請假紀錄（特休、事假、病假）|
| `salary_records.csv` | 160 筆薪資紀錄（2026 年 1–8 月，底薪、獎金、加班費）|

**API**

```
POST /api/v1/copilot/query

Request: { "question": "工號10001王大明還剩幾天特休？" }
Response: { "answer": "...", "tool_used": "calculate_leave" }
```

`tool_used` 值：`rag_search` / `lookup_employee` / `calculate_leave` / `none`

---

### 模組 G：AI Orchestration Agent（v1.7 架構升級）

LangGraph Structured Workflow，讓 HR 用一句自然語言觸發完整 JD 優化流程。

**v1.7 vs v1.6.1 升級對照**

| 面向 | v1.6.1 | v1.7 |
|------|--------|------|
| 路由機制 | branch_node 關鍵字硬比對 | `parse_input_node` 提取 `parsed_intent`，LLM 語意理解後 branch_node 讀取結果路由 |
| Company Profile | 前端手動填寫（必填）| `parse_input_node` 從自然語言自動提取（選填）|
| 補問機制 | 無（直接執行，可能低品質）| `clarify_node` 在必要資訊不足時主動補問 |
| AgentState 新增 | — | `parsed_intent: list[str]`、`clarification_needed: str \| None` |

**Workflow 執行流程（v1.7）**

```
START
  |
  v
parse_input_node
(LLM 提取結構化欄位 + parsed_intent)
  |
  v
clarify_node
(判斷資訊是否充足)
  |
  +--- 資訊缺失 ---> end_with_clarify_node ---> END
  |                  (包裝提問為 final_report)
  |
  +--- 資訊完整
          |
          +--- 有 jd_text ---> analyze_node
          |                        |
          |                        v
          |                   rewrite_node
          |                        |
          |                        v
          |                   persona_node
          |                        |
          |                        v
          |                   branch_node (讀取 parsed_intent)
          |                        |
          |           +------------+------------+------------+
          |          none        salary      sourcing      both
          |           |            |            |            |
          |           |            v            v            v
          |           |       salary_node  sourcing_node  salary_node
          |           |            |            |            |
          |           |            |            |            v
          |           |            |            |       sourcing_node
          |           +------------+------------+------------+
          |                                     |
          |                                     v
          |                             synthesize_node ---> END
          |
          +--- 無 jd_text ---> copilot_node ---> synthesize_node ---> END
```

**AgentState（v1.7）**

```python
class AgentState(TypedDict):
    # LangGraph 必填：對話訊息串（自動累積，不覆蓋）
    messages: Annotated[list[BaseMessage], add_messages]

    # 使用者輸入（從 AgentRequest 帶入）
    user_input: str
    job_title: NotRequired[str | None]
    jd_text: NotRequired[str | None]
    company_profile: NotRequired[dict[str, Any] | None]

    # 各模組執行結果（由各 Node 寫入，使用 Pydantic Response Schema）
    analysis_result: NotRequired[AnalyzeJDResponse]       # 模組 A
    rewrite_result: NotRequired[RewriteJDResponse]        # 模組 B
    salary_result: NotRequired[SalaryCheckResponse]       # 模組 C
    persona_result: NotRequired[GeneratePersonaResponse]  # 模組 D
    sourcing_result: NotRequired[SourcingResult]          # 模組 E
    copilot_result: NotRequired[CopilotResponse]          # 模組 F

    # 路由控制
    branch_decision: NotRequired[str]   # salary / sourcing / both / none

    # 輸出
    final_report: NotRequired[str]
    error_messages: Annotated[list[str], operator.add]
```

> `parsed_intent` 與 `clarification_needed` 由 `parse_input_node` / `clarify_node` 動態寫入 state，
> 並由 `run_agent()` 讀取後包進 `AgentResponse` 回傳前端，不定義在 TypedDict 靜態欄位中。

**各節點說明**

| 節點 | 對應模組 | 觸發條件 |
|------|----------|----------|
| `parse_input_node` | — | 每次執行必執行（v1.7 新增）|
| `clarify_node` | — | parse_input 完成後（v1.7 新增）|
| `end_with_clarify_node` | — | 資訊缺失時，包裝提問為 final_report 後結束 |
| `analyze_node` | 模組 A | 有 jd_text 時必執行 |
| `rewrite_node` | 模組 B | analyze 完成後必執行 |
| `persona_node` | 模組 D | rewrite 完成後必執行 |
| `branch_node` | — | 讀取 `parsed_intent` 決定路由 |
| `salary_node` | 模組 C | branch_decision 含 "salary" |
| `sourcing_node` | 模組 E | branch_decision 含 "sourcing" |
| `copilot_node` | 模組 F | 無 jd_text（純諮詢路徑）|
| `synthesize_node` | — | 所有分支的終點 |

**評估系統（8 個 Eval Cases，8/8 PASS）**

| Case | 說明 | 預期路由 |
|------|------|----------|
| C1 | 無 JD，純 HR 知識問答（法規）| copilot → synthesize |
| C2 | 有 JD，只分析與 Persona（不含薪資/Sourcing）| branch=none |
| C3 | 有 JD，薪資分析需求 | branch=salary |
| C4 | 有 JD，Sourcing 需求 | branch=sourcing |
| C5 | 有 JD，薪資 + Sourcing 雙需求 | branch=both |
| C6 | 意圖不明確（「幫我」）| `clarification_needed` 不為 None |
| C7 | parse_input_node 欄位提取驗證 | 正確提取 company_profile 與 salary 欄位 |
| C8 | parsed_intent 語意路由（不含「薪資」字串）| branch=salary |

執行評估：
```bash
python -m app.orchestration.evaluations.run_evals
```

**API**

```
POST /api/v1/run-agent

Request:
{
  "user_input": "幫我分析這份JD，用Startup風改寫，並確認薪資75K是否有競爭力",
  "job_title": "Python Backend Engineer",
  "jd_text": "..."
}
```

---

## API Endpoints 總覽

| 方法 | 路徑 | 功能 |
|------|------|------|
| POST | `/api/v1/analyze-jd` | 分析 JD 吸引力（模組 A）|
| POST | `/api/v1/rewrite-jd` | 改寫 JD（模組 B）|
| POST | `/api/v1/generate-persona` | 生成候選人 Persona（模組 D）|
| POST | `/api/v1/check-salary` | 薪資競爭力檢查（模組 C）|
| POST | `/api/v1/generate-sourcing` | 生成 Sourcing 查詢（模組 E）|
| POST | `/api/v1/copilot/query` | HR 知識助手查詢（模組 F）|
| POST | `/api/v1/run-agent` | Structured Workflow 執行入口（模組 G）|

---

## 開發環境設置

### 安裝依賴

```bash
conda activate ai-talent-magnet
pip install -r requirements.txt
```

### 資料 ETL（模組 C 使用，首次執行）

```bash
# 將 data_raw/ 底下的三份原始 Excel 清理為標準化 CSV
python scripts/prepare_data.py
```

### 建立向量索引（模組 F 使用，首次執行）

```bash
python scripts/build_vector_store.py
```

### 啟動服務

```bash
# FastAPI 後端
uvicorn app.main:app --reload

# Streamlit 前端（另開 terminal）
streamlit run 🏠_首頁.py
```

### 環境變數

```bash
OPENAI_API_KEY=sk-...
LANGSMITH_API_KEY=...   # 選填，用於 LangSmith 追蹤
```

---

## 開發階段

| 階段 | 目標 | 狀態 |
|------|------|------|
| Phase 1 | 核心 MVP（模組 A、B、D + Streamlit）| ✅ 已完成 |
| Phase 2 | 商業完整（模組 C、E + GitHub + README）| ✅ 已完成 |
| Phase 3 | 技術深度（模組 F、G + 評估系統）| ✅ 已完成 |
| Phase 4 | 產品化（Docker + 部署 + Demo 影片）| 🔲 規劃中 |

---

## 技術決策亮點

**1. 官方資料 ETL + LLM 語意映射（模組 C）**
放棄手動整理 50–100 筆 mock 對照資料，改採政府公開統計資料（勞動部 + 主計總處）做一次性 ETL。職稱/產業自由文字與官方分類之間的落差，交由 LLM 語意映射，而非在 Python 層寫死規則。

**2. Structured Workflow 取代 ReAct Agent（模組 G）**
JD 優化流程步驟固定，Structured Workflow 比 ReAct 更可預測、可測試，且避免不必要的 LLM 路由成本。eval 8/8 穩定通過。

**3. LLM 路由取代關鍵字比對（模組 G v1.7）**
`parse_input_node` 必然執行一次 LLM 呼叫提取結構化欄位，同一次呼叫同時輸出 `parsed_intent`，邊際成本為零，且能理解「確認待遇有沒有競爭力」等不含精確關鍵字的表達。

**4. Rule-based dispatch（模組 F）**
HR 知識助手的意圖判斷採 regex + 關鍵字比對，不呼叫 LLM。行為確定、零 API 費用；未來升級為 LangGraph Agent 時，Router 介面不需更動。

**5. 確定性計算設計（模組 F）**
特休天數等數值計算由 Python 函數完成（年資查表 → 已請加總 → 剩餘計算），LLM 只負責組合自然語言回答，確保數字 100% 正確。

**6. Orchestration Layer 分層解耦（模組 G）**
`app/orchestration/tools.py` 作為 Workflow 與 Service 之間的適配器層，兩者互不直接 import。Streamlit 前端繼續走 HTTP，Agent 對話介面是新增入口，兩種介面並存不互相干擾。


