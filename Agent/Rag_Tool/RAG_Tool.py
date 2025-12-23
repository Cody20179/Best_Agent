import requests
import dotenv
import os

dotenv.load_dotenv()  # Load environment variables from .env file

BASE_URL = "http://192.168.1.36:8080"   # 改成你的 RAGFlow 位址
API_KEY = os.getenv("ragflowapi")       # 從環境變數讀取 API key

def ragflow_retrieve(question: str, dataset_ids: list[str], page: int = 1, page_size: int = 5):
    url = f"{BASE_URL}/api/v1/retrieval"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    payload = {
        "question": question,
        "dataset_ids": dataset_ids,
        "page": page,
        "page_size": page_size,
        # 下面這些欄位若你不確定就先不要放；等你要調品質再加
        # "similarity_threshold": 0.2,
        # "vector_similarity_weight": 0.5,
    }

    r = requests.post(url, headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()

if __name__ == "__main__":
    dataset_ids = ["a92508d0dd8d11f0b6ae9e3860c79f60"]  # 改成你的 dataset id
    resp = ragflow_retrieve("FFT 是什麼？用一句話說明。", dataset_ids)

    print("RAW JSON:")
    print(resp)

    # 常見做法：把 chunks 文字抽出來（不同版本欄位名可能略不同）
    data = resp.get("data", resp)
    chunks = data.get("chunks") or data.get("data") or []
    print("\nTop chunks:")
    for i, c in enumerate(chunks, 1):
        text = c.get("content") or c.get("text") or str(c)
        print(f"{i}. {text[:200]}")
