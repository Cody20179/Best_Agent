from agents import function_tool
from pathlib import Path
import base64

@function_tool
def image_to_base64(image_path: str) -> str:
    """
    image_to_base64 的 Docstring
    
    :param image_path: 說明
    :type image_path: str
    :return: 說明
    :rtype: str
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"找不到檔案：{path}")

    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

if __name__ == "__main__":
    test_image_path = r"E:\CODY\Program\Industry\BEST\Figure\1AE-00166_p001.png"  # 替換成你的測試圖片路徑
    try:
        b64_string = image_to_base64(test_image_path)
        print(type(b64_string))
        print(len(b64_string))
        print(b64_string[:100] + "...")  # 只打印前100個字元以避免輸出過長
    except FileNotFoundError as e:
        print(e)