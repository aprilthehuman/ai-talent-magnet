"""
ETL Pipeline：將知識庫 .md 文件 → Chunk → Embedding → 存入 ChromaDB
使用 LangChain 完整 RAG 工具鏈，向量庫透過 as_retriever() 對接後續 LangGraph Tools

執行方式：python scripts/build_vector_store.py
"""

# 1. 標準函式庫
import sys
import shutil
from pathlib import Path

# 2. 將專案根目錄加入 sys.path（必須在本地模組 import 之前）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 3. 第三方套件
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

# 4. 本地模組
from app.config import (
    KNOWLEDGE_DIR,
    VECTOR_STORE_DIR,
    COLLECTION_NAME,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    EMBEDDING_MODEL,
)

# 5. 執行邏輯
load_dotenv()  # 載入 .env 檔中的環境變數（含 OPENAI_API_KEY）


# ── Step 1：載入並切割文件 ──────────────────────────────────────
def load_and_split(file_path: Path) -> list:
    """
    讀取 .md 文件，統一使用 Document 物件貫穿整個 pipeline：
      TextLoader.load()                          → List[Document]
      MarkdownHeaderTextSplitter.split_text()   → 依標題切割（保留語意）
      RecursiveCharacterTextSplitter.split_documents() → 依字數二次切割
    """
    print(f"  載入：{file_path.name}")

    # Step 1a：TextLoader → List[Document]
    loader = TextLoader(str(file_path), encoding="utf-8")
    docs = loader.load()  # 回傳 List[Document]，page_content 為完整 .md 內容

    # Step 1b：依 Markdown 標題切割 → 每個 chunk 是一個完整段落
    # MarkdownHeaderTextSplitter 只有 split_text()（接受 str），
    # 手動迭代 docs 以保持 pipeline 語意統一（List[Document] → List[Document]）
    headers_to_split_on = [
        ("#",   "h1"),
        ("##",  "h2"),
        ("###", "h3"),
    ]
    md_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False,
    )
    header_chunks = []
    for doc in docs:
        header_chunks.extend(md_splitter.split_text(doc.page_content))

    # Step 1c：二次切割：段落仍太長時按字數切
    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    final_chunks = char_splitter.split_documents(header_chunks)

    # 附加來源資訊到 metadata（RAG 引用時可回溯）
    for chunk in final_chunks:
        chunk.metadata["source"] = file_path.stem   # e.g. "labor_law"
        chunk.metadata["file"]   = file_path.name   # e.g. "labor_law.md"

    print(f"    → {len(final_chunks)} chunks")
    return final_chunks


# ── Step 2：建立向量資料庫 ──────────────────────────────────────
def build_vector_store(all_chunks: list) -> Chroma:
    """
    使用 LangChain Chroma 封裝，自動完成：
      embedding → 寫入 ChromaDB persistent storage
    回傳 vectorstore 物件，可直接呼叫 as_retriever()
    """
    print("\n正在建立 Embeddings 並寫入 ChromaDB...")
    print(f"  Embedding model：{EMBEDDING_MODEL}")

    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)

    # Chroma.from_documents：一行完成 embed + store
    # persist_directory：資料持久化，重啟後不需重建
    vectorstore = Chroma.from_documents(
        documents=all_chunks,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=str(VECTOR_STORE_DIR),
    )

    # 使用 len(all_chunks) 而非私有屬性 vectorstore._collection.count()
    print(f"✅ 寫入完成，共 {len(all_chunks)} 筆")
    return vectorstore


# ── Step 3：驗證 retriever ──────────────────────────────────────
def verify_retriever(vectorstore: Chroma):
    """
    以 as_retriever() 進行測試查詢。
    這個介面是後續 LangGraph Tool（rag_search）直接使用的標準介面。
    """
    print("\n=== 驗證：retriever.invoke() 測試 ===")

    # as_retriever()：將 vectorstore 轉為 LangChain Retriever 介面
    # search_type="similarity"：餘弦相似度
    # k=3：回傳最相關的 3 個 chunk
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 3},
    )

    test_queries = [
        "試用期最長幾個月？",
        "特休幾天？",
        "員工推薦獎金是多少？",
    ]

    for query in test_queries:
        print(f"\n查詢：「{query}」")
        docs = retriever.invoke(query)
        for i, doc in enumerate(docs):
            source  = doc.metadata.get("source", "unknown")
            h2      = doc.metadata.get("h2", "")
            preview = doc.page_content[:100].replace("\n", " ")
            print(f"  [{i+1}] [{source}] {h2}")
            print(f"       {preview}...")


# ── 主程式 ───────────────────────────────────────────────────────
def main():
    print("=== 開始建立 ChromaDB 向量資料庫 ===\n")

    # 確認知識庫資料夾存在
    if not KNOWLEDGE_DIR.exists():
        raise FileNotFoundError(f"找不到知識庫資料夾：{KNOWLEDGE_DIR}")

    # 清除舊向量資料庫，避免重複執行時資料重複寫入
    if VECTOR_STORE_DIR.exists():
        shutil.rmtree(VECTOR_STORE_DIR)
        print("已清除舊向量資料庫，準備全量重建\n")
    VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)

    # 讀取所有 .md 文件
    md_files = list(KNOWLEDGE_DIR.glob("*.md"))
    if not md_files:
        raise FileNotFoundError(f"{KNOWLEDGE_DIR} 內沒有 .md 文件")

    print(f"找到 {len(md_files)} 份知識庫文件：")
    all_chunks = []
    for f in md_files:
        chunks = load_and_split(f)
        all_chunks.extend(chunks)

    print(f"\n✅ 共 {len(all_chunks)} chunks 來自 {len(md_files)} 份文件")

    # 建立向量資料庫
    vectorstore = build_vector_store(all_chunks)

    # 驗證 retriever
    verify_retriever(vectorstore)

    print("\n✅ 全部完成！向量資料庫已儲存至 app/vector_store/")
    print("   後續 rag_search tool 載入方式：")
    print("   from app.config import VECTOR_STORE_DIR, COLLECTION_NAME, EMBEDDING_MODEL")
    print("   vectorstore = Chroma(")
    print("       collection_name=COLLECTION_NAME,")
    print("       embedding_function=OpenAIEmbeddings(model=EMBEDDING_MODEL),")
    print("       persist_directory=str(VECTOR_STORE_DIR),")
    print("   )")
    print("   retriever = vectorstore.as_retriever(search_kwargs={'k': 3})")


if __name__ == "__main__":
    main()