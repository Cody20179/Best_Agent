# Vision_Agent_Full.py
# Windows CMD: (py312) python Vision_Agent_Full.py

from agents import Agent, Runner, OpenAIChatCompletionsModel, AsyncOpenAI, ModelSettings, function_tool
from openai import OpenAI
import asyncio
import base64
import mimetypes
from pathlib import Path
import re

# ========= 1) Backend 설정 =========
# Agent (text) 用 async client（Agents SDK）
external_client = AsyncOpenAI(
    base_url="http://140.134.60.218:7650/v1",
    api_key="ollama",
)

# Vision Tool 用 sync client（Tool 內部同步呼叫最穩）
vision_client = OpenAI(
    base_url="http://140.134.60.218:7650/v1",
    api_key="ollama",
)

# 你後端上真正可用的 vision 模型名稱
VISION_MODEL = "qwen3-vl:8b"

# 主 Agent 的文字模型（建議用純文字模型；若你後端只有一個模型也可改同一個）
TEXT_MODEL = "qwen3:4b"


# ========= 2) Utilities =========
def image_to_data_url(image_path: str) -> str:
    """
    Read image from Windows path and convert to data URL:
    data:image/png;base64,....
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"找不到檔案：{path}")

    mime, _ = mimetypes.guess_type(path.name)
    if mime is None:
        mime = "image/png"

    b64 = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def extract_windows_image_path(text: str) -> str | None:
    r"""Very simple extractor for Windows image path (png/jpg/jpeg/webp).
    e.g. E:\...\xxx.png
    """
    # 支援空白、中文路徑、常見副檔名
    pattern = r"([A-Za-z]:\\[^\n\r\t\"']+\.(?:png|jpg|jpeg|webp))"
    m = re.search(pattern, text, flags=re.IGNORECASE)
    return m.group(1) if m else None


# ========= 3) Vision Tool =========
@function_tool
def vision_analyze(image_path: str, prompt: str) -> str:
    """
    Analyze an image and return a concise description in Traditional Chinese.
    Inputs:
      - image_path: Windows local file path to image
      - prompt: what user wants to know about the image
    """
    img_url = image_to_data_url(image_path)

    resp = vision_client.chat.completions.create(
        model=VISION_MODEL,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": img_url}},
            ],
        }],
    )

    return resp.choices[0].message.content


# ========= 4) Agent =========
agent = Agent(
    name="VisionAssistant",
    instructions=(
        "你是嚴謹的工程助理。\n"
        "若使用者問題涉及圖片內容，且提供了 Windows 圖片路徑（例如 E:\\...\\a.png），"
        "你必須先呼叫 vision_analyze 取得圖片描述，再用繁體中文回覆。\n"
        "若找不到圖片路徑，請明確要求使用者提供圖片路徑。\n"
        "回答請精準、具體，不要臆測。"
    ),
    tools=[vision_analyze],
    model=OpenAIChatCompletionsModel(
        model=TEXT_MODEL,
        openai_client=external_client
    ),
    model_settings=ModelSettings(
        temperature=0.2,
        top_p=0.9,
    ),
)


# ========= 5) Runner =========
async def run_once(user_prompt: str):
    # 自動抓路徑：若 user_prompt 沒有明確帶路徑，也可在這裡做提示
    image_path = extract_windows_image_path(user_prompt)
    if image_path:
        # 讓 Agent 更容易 tool-call：把路徑整理成明確格式
        user_prompt = (
            f"使用者提供圖片路徑：{image_path}\n"
            f"問題：{user_prompt}\n"
            "請先用 vision_analyze(image_path, prompt) 解析圖片，再回答。"
        )

    result = await Runner.run(
        starting_agent=agent,
        input=user_prompt,
        max_turns=6
    )
    print("\n=== 系統回覆 ===")
    print(result.final_output)


if __name__ == "__main__":
    # Windows：直接在 CMD 內輸入一句話（含圖片路徑）
    # 例：請幫我看 E:\CODY\Program\Industry\BEST\Figure\1AE-00166_p001.png 的內容
    user_prompt = input("請輸入問題（含圖片路徑）：\n").strip()
    asyncio.run(run_once(user_prompt))
