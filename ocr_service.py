# ocr_service.py
import os
import json
import base64
import requests
import re
from io import BytesIO
from PIL import Image

class QwenDetector:
    """职责：利用 Qwen-VL-OCR 模型将视觉文字转化为物理像素坐标"""
    
    def __init__(self, api_key=None):
        # 优先从环境变量获取，或者手动填入
        self.api_key = api_key or "sk-ed114e4d50c048c6a485c453ab2b9756" 
        self.model = "qwen-vl-ocr-latest"
        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

    def get_target_coords(self, image_source, target_name):
        """
        核心业务：定位目标并换算坐标
        :param image_source: 可以是本地路径，也可以是 Base64 字符串
        :param target_name: 想要寻找的文字或图标描述
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

        # 2. 构建针对“坐标对齐”业务优化的 Prompt
        prompt = f"""请在这张图片中找到“{target_name}”的具体中心位置。
要求：
1. 给出该目标的中心点归一化坐标（norm_x, norm_y，范围 0-1000）。
2. 严格以 JSON 格式返回，不要包含任何解释。
3. 格式：{{"norm_x": 数字, "norm_y": 数字}}"""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}}
                    ]
                }
            ]
        }

        try:
            print(f"正在请求 Qwen-OCR 定位: {target_name} ...")
            response = requests.post(self.base_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            res_json = response.json()
            content = res_json["choices"][0]["message"]["content"]
            
            # 4. 解析模型返回的坐标
            # 优先使用正则表达式直接提取数字，这比解析 JSON 更稳健，能容忍各种格式错误
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
                    print(f"模型返回内容无法解析: {content}")
                    return None
                    
                try:
                    json_str = match.group().replace("'", '"')
                    norm_data = json.loads(json_str)
                    norm_x = float(norm_data.get("norm_x"))
                    norm_y = float(norm_data.get("norm_y"))
                except Exception as e:
                    print(f"解析坐标失败: {e}, 原始字符串: {content}")
                    return None

            # 5. 坐标换算职责：归一化 -> 物理像素
            # 公式：物理坐标 = (归一化值 / 1000) * 图片原始尺寸
            real_x = int(round((norm_x / 1000.0) * width))
            real_y = int(round((norm_y / 1000.0) * height))

            return {
                "x": real_x, 
                "y": real_y, 
                "debug": f"图片:{width}x{height}, 归一化:[{norm_x},{norm_y}]"
            }

        except Exception as e:
            print(f"定位业务执行失败: {e}")
            return None

# --- 完整测试入口 ---
if __name__ == "__main__":
    # ⚠️ 请确保你的 API KEY 已设置或在此处手动替换
    MY_API_KEY = "sk-7d48078fa897417c9dssdfsda70d95f9a" # 示例 Key
    
    # 初始化检测器
    detector = QwenDetector(api_key=MY_API_KEY)
    
    # 测试图片路径（请确保目录下有 test.jpg）
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
