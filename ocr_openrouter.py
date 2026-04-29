import os
import json
import base64
import requests
import re
from io import BytesIO
from PIL import Image

class OpenRouterDetector:
    """职责：利用 OpenRouter 上的免费视觉模型将视觉文字转化为物理像素坐标"""
    
    def __init__(self, api_key=None):
        # 优先从环境变量获取，或者手动填入
        self.api_key = api_key or "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" 
        # 使用支持视觉的免费模型，例如 google/gemini-2.5-flash:free 或 qwen/qwen-vl-plus:free
        # 注意：baidu/qianfan-ocr-fast:free 可能不支持标准的 chat/completions 视觉输入格式
        # 这里我们使用一个通用的免费视觉模型
        self.model = "baidu/qianfan-ocr-fast:free"
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"

    def get_target_coords(self, image_source, target_name, max_retries=3):
        """
        核心业务：定位目标并换算坐标
        :param image_source: 可以是本地路径，也可以是 Base64 字符串
        :param target_name: 想要寻找的文字或图标描述
        :param max_retries: 解析失败时最多重试次数（含首次）
        """
        # 1. 统一处理图片源并获取原始尺寸（关键职责：防止偏移）
        if isinstance(image_source, str) and not image_source.startswith(('data:', 'iVBO')):
            # 说明是文件路径
            if not os.path.exists(image_source):
                print(f"错误：找不到文件 {image_source}")
                return None
            with Image.open(image_source) as img:
                width, height = img.size
            with open(image_source, "rb") as f:
                img_base64 = base64.b64encode(f.read()).decode('utf-8')
        else:
            # 说明是 Base64 字符串
            img_data = base64.b64decode(image_source.replace('data:image/png;base64,', ''))
            with Image.open(BytesIO(img_data)) as img:
                width, height = img.size
            img_base64 = image_source.replace('data:image/png;base64,', '')

        # 2. 构建初始 Prompt
        base_prompt = f"""任务：在图片中定位文字“{target_name}”的中心位置。

【输出格式要求（必须严格遵守）】：
1. 只输出一个 JSON 对象，不要包含任何其他文字、解释或 markdown 标记。
2. JSON 格式必须严格如下，其中 norm_x 和 norm_y 必须是 0-1000 之间的整数：
{{"norm_x": 整数, "norm_y": 整数}}

【示例】：
如果目标在图片正中央，输出：{{"norm_x": 500, "norm_y": 500}}

【警告】：
- 不要输出文本框的四个角坐标！
- 不要输出多个坐标！
- 只输出一个中心点坐标！
- 不要使用引号包裹数字！"""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/guiai",
            "X-Title": "GUI AI Agent"
        }

        # 3. 重试循环：解析失败时把错误反馈给模型，让它修正
        last_error = ""
        for attempt in range(max_retries):
            # 构建本次调用的 prompt
            if attempt == 0:
                current_prompt = base_prompt
            else:
                current_prompt = base_prompt + f"""

【上一次输出错误】：
你上一次的输出格式不正确，错误信息：{last_error}
请根据错误信息修正你的输出，严格按照要求的 JSON 格式重新输出。"""

            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": current_prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}}
                        ]
                    }
                ]
            }

            try:
                print(f"正在请求 OpenRouter ({self.model}) 定位: {target_name} (尝试 {attempt + 1}/{max_retries}) ...")
                response = requests.post(self.base_url, json=payload, headers=headers, timeout=30)
                response.raise_for_status()
                res_json = response.json()
                content = res_json["choices"][0]["message"]["content"]
                
                # 4. 解析模型返回的坐标
                norm_x_match = re.search(r'"?norm_x"?\s*:\s*(\d+(?:\.\d+)?)', content)
                norm_y_match = re.search(r'"?norm_y"?\s*:\s*(\d+(?:\.\d+)?)', content)
                
                if norm_x_match and norm_y_match:
                    norm_x = float(norm_x_match.group(1))
                    norm_y = float(norm_y_match.group(1))
                else:
                    # Fallback: 尝试标准的 JSON 解析
                    clean_content = content.strip()
                    if "```json" in clean_content:
                        clean_content = clean_content.split("```json")[1].split("```")[0].strip()
                    elif "```" in clean_content:
                        clean_content = clean_content.split("```")[1].split("```")[0].strip()
                        
                    match = re.search(r'\{.*\}', clean_content, re.DOTALL)
                    if not match:
                        last_error = f"无法从响应中提取 JSON: {content[:100]}..."
                        print(last_error)
                        continue
                        
                    try:
                        json_str = match.group().replace("'", '"')
                        norm_data = json.loads(json_str)
                        norm_x = float(norm_data.get("norm_x"))
                        norm_y = float(norm_data.get("norm_y"))
                    except Exception as e:
                        last_error = f"JSON 解析失败: {e}"
                        print(f"{last_error}, 原始字符串: {content[:100]}...")
                        continue

                # 校验：如果坐标值包含逗号（说明模型返回了文本框坐标序列），则报错
                if ',' in str(norm_x) or ',' in str(norm_y):
                    last_error = f"坐标值包含逗号（输出了文本框坐标序列）: norm_x={norm_x}, norm_y={norm_y}"
                    print(last_error)
                    continue
                    
                # 校验：坐标必须在 0-1000 范围内
                if not (0 <= norm_x <= 1000) or not (0 <= norm_y <= 1000):
                    last_error = f"坐标超出 0-1000 范围: norm_x={norm_x}, norm_y={norm_y}"
                    print(last_error)
                    continue

                # 5. 坐标换算职责：归一化 -> 物理像素
                real_x = int(round((norm_x / 1000.0) * width))
                real_y = int(round((norm_y / 1000.0) * height))

                return {
                    "x": real_x, 
                    "y": real_y, 
                    "debug": f"图片:{width}x{height}, 归一化:[{norm_x},{norm_y}]"
                }

            except Exception as e:
                last_error = f"API 调用异常: {e}"
                print(last_error)
                if attempt < max_retries - 1:
                    continue
                else:
                    print(f"定位业务执行失败，已达到最大重试次数: {e}")
                    if 'response' in locals() and hasattr(response, 'text'):
                        print(f"API 响应: {response.text}")
                    return None

        print(f"定位目标 {target_name} 失败，已重试 {max_retries} 次。")
        return None

# --- 完整测试入口 ---
if __name__ == "__main__":
    # 初始化检测器
    detector = OpenRouterDetector()
    
    # 测试图片路径（请确保目录下有 test.png）
    test_image = "test.png" 
    target = "此电脑"
    
    result = detector.get_target_coords(test_image, target)
    
    if result:
        print("\n" + "="*30)
        print(f"目标【{target}】定位成功！")
        print(f"物理像素坐标: X={result['x']}, Y={result['y']}")
        print(f"调试信息: {result['debug']}")
        print("="*30)
        print(f"现在你可以直接执行: pyautogui.click({result['x']}, {result['y']})")
    else:
        print("\n定位失败，请检查网络、API Key 或图片内容。")
