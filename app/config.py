# app/config.py
"""
全域設定檔：集中管理各模組共用的常數。
所有 service、scripts 均從此 import，避免分散定義造成不一致。
"""

import os
from pathlib import Path

# ── 專案根目錄 ───────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent  # app/ 的上一層

# ── 資料路徑 ─────────────────────────────────────────────────────
DATA_DIR       = BASE_DIR / "app" / "data" / "employees"
KNOWLEDGE_DIR  = BASE_DIR / "app" / "knowledge"

# ── ChromaDB 設定 ─────────────────────────────────────────────────
VECTOR_STORE_DIR = BASE_DIR / "app" / "vector_store"
COLLECTION_NAME  = "hr_knowledge"

# ── RAG 切割參數 ──────────────────────────────────────────────────
CHUNK_SIZE    = 500
CHUNK_OVERLAP = 50

# ── Embedding 模型 ────────────────────────────────────────────────
EMBEDDING_MODEL = "text-embedding-3-small"

# ── LangSmith 追蹤設定（Module G）────────────────────────────────
# 需在 .env 設定，LangGraph 執行時自動送出追蹤紀錄
# LANGCHAIN_TRACING_V2=true 時啟用，false 時關閉（本地除錯用）
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false")
LANGCHAIN_API_KEY    = os.getenv("LANGCHAIN_API_KEY", "")
LANGCHAIN_PROJECT    = os.getenv("LANGCHAIN_PROJECT", "ai-talent-magnet")