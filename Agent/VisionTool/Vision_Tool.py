from agents import function_tool
from typing import Dict
from litellm import completion
import base64

api_host = "http://127.0.0.1:11434"
use_model = "ollama/qwen3-vl:2b"

prompt = "請問這張圖的內容"
img_path = r"E:\CODY\Program\Industry\BEST\Figure\1AE-00166_p001.png"

@function_tool
def Vision_Tool(prompt: str, img_path: str):
    """Vision Tool: Analyze and describe the content of an image."""
    print("Vision Tool Activated")

    with open(img_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")

    response = completion(
        model=use_model,
        api_base=api_host,
        stream=True,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                ],
            }
        ],
    )

    print(f"Question:{prompt}")

    Result = ""

    for chunk in response:
        delta = chunk["choices"][0]["delta"]
        if "content" in delta and delta["content"]:
            print(delta["content"], end="", flush=True)
            Result += delta["content"]

    return Result

if __name__ == "__main__":
    resp = Vision_Tool(prompt, img_path)

    # 重點：要把串流跑完，才會看到內容
    for chunk in resp:
        delta = chunk["choices"][0]["delta"]
        if "content" in delta and delta["content"]:
            print(delta["content"], end="", flush=True)

    print()  # 換行
