
from agents import function_tool
from typing import Any, Dict, List, Optional
import requests, dotenv, os

dotenv.load_dotenv()

BASE_URL = os.getenv("RAGFLOW_BASE_URL", "http://192.168.1.36:8080") # 140.134.60.229: 5678
API_KEY = os.getenv("ragflowapi")
DATASET_ID = os.getenv("RAGFLOW_DATASET_ID", "a92508d0dd8d11f0b6ae9e3860c79f60")

def ragflow_retrieval(
    question: str,
    dataset_id: str,
    top_k: int = 5,
    page: int = 1,
    timeout: int = 60,

    # ===== RERANK 相關 =====
    enable_rerank: bool = False,
    rerank_top_k: Optional[int] = None,
    similarity_threshold: Optional[float] = None,
    vector_similarity_weight: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Call RAGFlow retrieval API with optional rerank.
    """

    url = f"{BASE_URL}/api/v1/retrieval"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    payload: Dict[str, Any] = {
        "question": question,
        "dataset_ids": [dataset_id],  # 必須是 list[str]
        "page": page,
        "page_size": top_k,
    }

    # ===== RERANK =====
    if enable_rerank:
        payload["enable_rerank"] = True
        payload["rerank_top_k"] = rerank_top_k if rerank_top_k is not None else top_k

    # ===== 進階控制（可選）=====
    if similarity_threshold is not None:
        payload["similarity_threshold"] = similarity_threshold

    if vector_similarity_weight is not None:
        payload["vector_similarity_weight"] = vector_similarity_weight

    r = requests.post(url, headers=headers, json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json()

def extract_chunks(resp: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract chunks from RAGFlow response safely.
    Your confirmed schema: resp["data"]["chunks"].
    """
    if not isinstance(resp, dict):
        return []
    if resp.get("code") != 0:
        return []
    data = resp.get("data") or {}
    chunks = data.get("chunks") or []
    if not isinstance(chunks, list):
        return []
    return chunks

def pretty_print_chunks(chunks: List[Dict[str, Any]], max_chars: int = 400) -> None:
    for i, c in enumerate(chunks, 1):
        doc = c.get("document_keyword") or c.get("doc_name") or ""
        sim = c.get("similarity")
        term = c.get("term_similarity")
        vec = c.get("vector_similarity")
        text = c.get("content") or ""

        print(f"\n[{i}] doc={doc}")
        print(f"    similarity={sim} term={term} vector={vec}")
        print(text[:max_chars])

@function_tool
def Retrieval_Tool_Text(question: str) -> Dict[str, Any]:
    """RAGFlow retrieval -> return compact context text for LLM"""
    print("=== Retrieval Tool Activated ===")
    print("Question:", question)
    resp = ragflow_retrieval(
        question=question,
        dataset_id=DATASET_ID,
        top_k=5,
        enable_rerank=True,
        rerank_top_k=10,
    )

    chunks = extract_chunks(resp)
    total = (resp.get("data") or {}).get("total", 0)

    context_lines = []
    for i, c in enumerate(chunks, 1):
        doc = c.get("document_keyword", "")
        sim = c.get("similarity", 0)
        text = c.get("content", "")
        context_lines.append(f"[{i}] doc={doc} similarity={sim}\n{text}")

    context = "\n\n".join(context_lines)

    return {
        "total": total,
        "context": context
    }

if __name__ == "__main__":
    Anwser = Retrieval_Tool_Text("材質-板材表格")
    print(Anwser)
