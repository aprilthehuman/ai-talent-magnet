# 🧲 AI Talent Magnet

> 一個幫企業提升招募吸引力的 AI 系統，從被動等履歷轉為主動提升職缺競爭力。

**作者：** April ｜ **版本：** v1.4.0 ｜ **開發狀態：** Phase 1 進行中（Module A、B、D 已完成）

---

## 專案背景

傳統招募工具多聚焦在「履歷篩選」，但台灣中小企業的真實痛點是在候選人決定是否投遞之前就已流失人才。AI Talent Magnet 從招募前端切入，協助企業在發布職缺前就提升 JD 吸引力、理解候選人視角，並透過 AI 自動化串聯整個優化流程。

本專案結合 **HR domain knowledge + AI 工程技術**，展示人資背景轉型 AI Application Engineer 的實務能力。

---

## 模組架構（v1.4.0，共 7 個模組）

| 模組 | 功能 | 狀態 |
|------|------|------|
| **A** JD Attraction Analyzer | 分析 JD 吸引力，找出降低投遞率的問題 | ✅ 已完成 |
| **B** JD Rewrite AI | 根據 Company Profile 產出三種風格的改寫版本 | ✅ 已完成 |
| **C** Salary Competitiveness Detector | AI 混合模式評估薪資市場競爭力 | 📋 Phase 2 |
| **D** Candidate Persona Generator | 反推理想候選人樣貌、動機與溝通方式 | ✅ 已完成 |
| **E** AI Sourcing Assistant | 生成 Boolean search string，降低主動 sourcing 門檻 | 📋 Phase 2 |
| **F** HR Knowledge Copilot | RAG 技術建立招募知識庫，自然語言查詢歷史 JD | 📋 Phase 3 |
| **G** AI Orchestration Agent | 自然語言一句話觸發完整流程，LangChain Agent 串聯所有模組 | 📋 Phase 3 |

---

## 技術架構

```
前端    Streamlit（MVP）
後端    FastAPI + Uvicorn
AI 模型  OpenAI GPT-4o-mini
框架    LangChain + LangGraph（Module G）
向量庫  ChromaDB（Module F）
資料驗證 Pydantic v2
語言    Python 3.11
```

---

## 專案結構

```
portfolio/
├── main.py                         # FastAPI 主程式，掛載所有 Router
├── .env                            # API Key（不納入版控）
├── .gitignore
├── requirements.txt
├── frontend/
│   └── app_ui.py                   # Streamlit 前端（開發中）
└── app/
    ├── core/
    │   ├── prompts/                # Prompt templates（各模組）
    │   └── keyword_dicts.py        # Module A 負面詞彙與模糊用語字典
    ├── data/                       # 參考資料集（Module C 薪資對照，Phase 2 使用）
    ├── routers/
    │   ├── analyzer.py             # Module A Router
    │   ├── rewriter.py             # Module B Router
    │   └── persona.py              # Module D Router
    ├── models/
    │   ├── analyzer_schemas.py     # Module A Schemas
    │   ├── rewriter_schemas.py     # Module B Schemas（含 CompanyProfile）
    │   └── persona_schemas.py      # Module D Schemas（import CompanyProfile）
    └── services/
        ├── analyzer_service.py     # Module A 商業邏輯
        ├── rewriter_service.py     # Module B 商業邏輯
        └── persona_service.py      # Module D 商業邏輯
```

---

## 安裝與執行

### 環境需求

- Python 3.11
- Conda（建議使用 Miniconda）

### 安裝步驟

```bash
# 1. Clone 專案
git clone https://github.com/<your-username>/ai-talent-magnet.git
cd ai-talent-magnet

# 2. 建立 conda 環境
conda create -n talent-magnet python=3.11
conda activate talent-magnet

# 3. 安裝套件
pip install -r requirements.txt

# 4. 設定 API Key
cp .env.example .env
# 在 .env 填入你的 OPENAI_API_KEY
```

### 啟動後端

```bash
uvicorn main:app --reload
```

API 文件：http://localhost:8000/docs

### 啟動前端（開發中）

```bash
streamlit run frontend/app_ui.py
```

---

## Module A — JD Attraction Analyzer

**功能：** 分析 JD 吸引力，找出降低候選人投遞意願的問題。

**API：** `POST /api/v1/analyze`

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

**API：** `POST /api/v1/rewrite`

**請求範例：**
```json
{
  "original_jd": "原始 JD 文字...",
  "company_profile": {
    "company_name": "Acme SaaS",
    "culture_keywords": ["透明", "扁平", "快速迭代"],
    "vision": "打造亞洲最好的 B2B SaaS 平台",
    "manager_style": "重視自主性、鼓勵實驗",
    "tone_preference": "casual",
    "must_include": ["技術決策權", "彈性工時"],
    "must_avoid": ["抗壓", "配合加班"],
    "industry_context": "B2B SaaS 新創、A 輪階段"
  },
  "target_candidate_focus": "重視技術成長與工作自主性的工程師"
}
```

**三種改寫風格：**

| 風格 | 適合對象 | 強調訴求 |
|------|----------|----------|
| Startup 風 | 新創、快速成長團隊 | Ownership、影響力、彈性 |
| 穩定企業風 | 中大型企業、傳產數位化 | 制度、福利、穩定發展 |
| 高成長挑戰型 | SaaS、AI 公司 | 技術深度、學習、快速升級 |

**Guardrail 機制：** 檢查輸出是否包含 `must_avoid` 詞彙，並驗證 `must_include` 訊息是否有帶到，保護輸出品質。

---

## Module D — Candidate Persona Generator

**功能：** 整合 Module A 與 Module B 的輸出，反推理想候選人樣貌，幫助 HR 理解在吸引什麼樣的人、怎麼跟他們溝通。

**API：** `POST /api/v1/generate-persona`

**設計說明：** Module D 不接受原始未改寫的 JD，而是要求帶入 Module B 選定的改寫版本與 Company Profile，確保 Persona 反映公司真正的文化與期待。所有欄位可從 Module A 或 Module B 帶入，使用者無需重複填寫。

**請求範例：**
```json
{
  "job_title": "Python Backend Engineer",
  "job_description_text": "（Module B 選定的改寫版本）",
  "company_profile": { "...": "（沿用 Module B 的 CompanyProfile）" },
  "target_candidate_focus": "重視技術成長的工程師",
  "company_type": "startup",
  "industry": "SaaS",
  "seniority_level": "mid"
}
```

**回應欄位：**

| 欄位 | 類型 | 說明 |
|------|------|------|
| `ideal_seniority` | string | 理想年資區間，例：3–5 年 |
| `likely_background` | array | 可能的職涯背景 |
| `key_skills` | array | 核心技能清單 |
| `candidate_motivators` | array | 在意的面向（成長、薪資、WLB 等） |
| `likely_concerns` | array | 可能的顧慮 |
| `preferred_message_style` | string | 建議 HR 的溝通語氣 |
| `likely_channels` | array | 這類人常出現的平台 |

**模組資料流：** Module A（job_title、company_type、industry、seniority_level）→ Module B（company_profile、target_candidate_focus、改寫 JD）→ Module D

---

## 開發說明

### 技術決策亮點

- **Python 3.10+ union syntax** — 全程使用 `str | None` 取代 `Optional[str]`
- **結構化輸出** — 全模組使用 `response_format={"type": "json_object"}` 確保 LLM 輸出可解析
- **Schema 複用** — Module D 直接 import `CompanyProfile` from `rewriter_schemas.py`，Module A schema 獨立於 `analyzer_schemas.py`，不重複定義
- **Guardrail 設計** — Module B 實作 `must_avoid` 後處理驗證，violation 標記為 warning（MVP 不自動 retry）
- **AI 混合評分** — Module A 採用規則層 + AI 層，避免完全依賴 LLM 造成不穩定

### 開發階段規劃

```
Phase 1（當前）：Module A、B、D + Streamlit 前端
Phase 2：Module C（薪資競爭力）、Module E（Sourcing 助手）
Phase 3：Module F（RAG 知識庫）、Module G（AI Agent 串聯）
```

---

## 資料誠信聲明

本專案在所有涉及資料輸出的地方，都標註 confidence level 並提供 disclaimer，不假裝擁有完整資料集。Module C 的薪資參考資料為手動整理的 demo 資料集，來源透明（104 薪資情報公開頁、比薪水平台），不使用爬蟲。

---

## 相關連結

- 📄 [企劃書 v1.4.0]（附於 repo 中）
- 🔗 API 文件：啟動後端後至 `http://localhost:8000/docs` 查看

---

*本專案為 AI Application Engineer 求職作品集，展示 HR domain knowledge 結合 AI 工程技術的實務能力。*
