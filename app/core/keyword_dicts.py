"""
關鍵字字典模組
集中管理所有模組使用的靜態字典資料，避免散落在各個 service 檔案裡。

各字典用途：
  - NEGATIVE_KEYWORDS   → 模組 A：負面詞彙偵測與改寫建議
  - VAGUE_PHRASES       → 模組 A：模糊用語偵測
  - MISSING_CHECKLIST   → 模組 A：缺失項目檢查
  - MISSING_PENALTY     → 模組 A：缺失項目扣分與說明
  - TITLE_SYNONYMS      → 模組 E：職稱同義展開（正向查詢）
  - TITLE_SYNONYMS_REVERSE → 模組 E：職稱同義展開（反向查詢，自動產生）
"""


# ── 模組 A：JD 分析用字典 ────────────────────────────────

# 負面詞彙：出現這些詞會讓候選人不想投
NEGATIVE_KEYWORDS = {
    "抗壓性高": "建議改為『能在快步調環境工作』",
    "配合加班": "建議改為『專案期間可能需要彈性工時』",
    "責任制": "建議具體說明工時期待",
    "獨當一面": "建議改為『能獨立推動專案』",
    "主管交辦事項": "過於模糊，建議具體列出職責",
    "配合度高": "建議改為『重視團隊合作』",
    "抗壓": "建議改為『適應快速變化的環境』",
    "加班": "建議具體說明加班情況",
    "聽話": "這個詞讓人感覺沒有自主空間",
    "服從": "這個詞讓人感覺沒有自主空間",
}

# 模糊用語：這些詞讓人看不懂工作內容
VAGUE_PHRASES = [
    "其他交辦事項",
    "相關工作內容",
    "臨時交辦",
    "視情況調整",
    "協助主管",
    "處理雜務",
    "其他相關業務",
]

# 缺失項目檢查：JD 應該要有但常常沒有的東西
# 格式：(項目代碼, 用來偵測是否存在的關鍵字清單)
MISSING_CHECKLIST = [
    ("salary",  ["薪資", "月薪", "年薪", "K", "待遇", "salary"]),
    ("growth",  ["成長", "學習", "發展", "培訓", "mentor", "training"]),
    ("culture", ["團隊", "文化", "氛圍", "夥伴", "culture"]),
    ("content", ["負責", "工作內容", "職責", "你將會", "你將負責"]),
    ("impact",  ["影響", "貢獻", "ownership", "專案", "impact"]),
]

# 缺失項目對應的扣分與說明
# key 與 MISSING_CHECKLIST 的項目代碼對應
MISSING_PENALTY = {
    "salary":  {"score": 10, "label": "未提供薪資範圍"},
    "growth":  {"score": 8,  "label": "未提及成長機會"},
    "culture": {"score": 5,  "label": "未描述團隊文化"},
    "content": {"score": 10, "label": "未說明具體工作內容"},
    "impact":  {"score": 5,  "label": "未說明工作影響力"},
}


# ── 模組 E：職稱同義詞字典 ───────────────────────────────

# 正向字典：key 為標準化職稱（小寫），value 為台灣市場常用同義詞清單（含中英文）
# 維護原則：
#   1. key 一律小寫，方便 service 層做大小寫不敏感的查詢
#   2. value 保留原始大小寫，因為會直接顯示給 HR 或放進 Boolean string
#   3. 有歧義的詞（如「軟體工程師」可對應多個職稱）不放進 value，
#      避免反向索引產生錯誤對應
TITLE_SYNONYMS: dict[str, list[str]] = {
    "backend engineer": [
        "Backend Engineer",
        "後端工程師",
        "Python Developer",
        "API Engineer",
        "Server-side Engineer",
    ],
    "frontend engineer": [
        "Frontend Engineer",
        "前端工程師",
        "UI Engineer",
        "Web Developer",
        "React Developer",
        "Vue Developer",
    ],
    "fullstack engineer": [
        "Full Stack Engineer",
        "全端工程師",
        "Fullstack Developer",
        "Web Engineer",
    ],
    "data engineer": [
        "Data Engineer",
        "資料工程師",
        "ETL Engineer",
        "Data Pipeline Engineer",
        "Analytics Engineer",
    ],
    "data scientist": [
        "Data Scientist",
        "資料科學家",
        "ML Engineer",
        "Machine Learning Engineer",
        "AI Engineer",
        "AI 工程師",
    ],
    "devops engineer": [
        "DevOps Engineer",
        "DevOps 工程師",
        "SRE",
        "Site Reliability Engineer",
        "Infrastructure Engineer",
        "雲端工程師",
    ],
    "product manager": [
        "Product Manager",
        "產品經理",
        "PM",
        "Product Owner",
        "PO",
    ],
    "ux designer": [
        "UX Designer",
        "UI/UX Designer",
        "使用者體驗設計師",
        "Product Designer",
        "互動設計師",
        "介面設計師",
    ],
    "hr": [
        "HR",
        "人資",
        "人力資源專員",
        "Recruiter",
        "招募專員",
        "Talent Acquisition",
        "TA",
        "HRBP",
    ],
    "marketing": [
        "Marketing",
        "行銷",
        "行銷專員",
        "Digital Marketer",
        "Growth Hacker",
        "成長駭客",
        "行銷企劃",
    ],
}

# 反向索引：讓同義詞也能當查詢入口
# 例如輸入「人資」或「Recruiter」都能找到 "hr" 對應的完整同義詞清單
# 自動從 TITLE_SYNONYMS 產生，不需要手動維護
# 遇到歧義詞（同一個詞出現在多個 value 裡）保留先出現的對應，跳過後面的
TITLE_SYNONYMS_REVERSE: dict[str, str] = {}
for _key, _synonyms in TITLE_SYNONYMS.items():
    for _synonym in _synonyms:
        _synonym_lower = _synonym.lower()
        if _synonym_lower not in TITLE_SYNONYMS_REVERSE:
            TITLE_SYNONYMS_REVERSE[_synonym_lower] = _key