import os
import json
import base64
import requests
import re
import pyautogui
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

class QwenDetector:
    """职责：利用 Qwen-VL-OCR 模型将视觉文字转化为物理像素坐标"""
    
    def __init__(self, api_key=None):
        # 优先从环境变量获取，或者手动填入
        self.api_key = api_key or os.getenv("QWEN_OCR_API_KEY")
        if not self.api_key:
            raise ValueError("未找到 QWEN_OCR_API_KEY 环境变量，请在 .env 文件中配置")
        self.model = "qwen-vl-ocr-latest"
        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

    def get_target_coords(self, image_source, target_name, max_retries=None):
        """
        核心业务：定位目标并换算坐标
        :param image_source: 可以是本地路径，也可以是 Base64 字符串
        :param target_name: 想要寻找的文字或图标描述
        :param max_retries: 解析失败时最多重试次数（含首次），默认从环境变量 OCR_RETRY 读取
        """
        if max_retries is None:
            max_retries = int(os.getenv("OCR_RETRY", 3))
            
        # 1. 统一处理图片源并获取原始尺寸（关键职责：防止偏移）
        if not image_source:
            print("错误：传入的 image_source 为空")
            return None
            
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
        base_prompt = f"""任务：在图片中寻找文字“{target_name}”。

【输出格式要求（必须严格遵守）】：
1. 只输出一个 JSON 对象，不要包含任何其他文字、解释或 markdown 标记。
2. 你必须首先判断图片中是否存在该文字目标。
3. 请严格按照以下 JSON 格式输出：
{{
    "found": true 或 false,
    "norm_x": 整数 (如果 found 为 true，输出中心点 x 坐标；如果为 false，输出 -1),
    "norm_y": 整数 (如果 found 为 true，输出中心点 y 坐标；如果为 false，输出 -1)
}}

【示例】：
如果目标在图片正中央，输出：{{"found": true, "norm_x": 500, "norm_y": 500}}
如果图片中没有该目标，输出：{{"found": false, "norm_x": -1, "norm_y": -1}}

【警告】：
- 绝对不要输出文本框的四个角坐标！
- 绝对不要输出多个数字（如 488, 418, 15, 57, 90 是错误的）！
- 只输出一个中心点坐标！
- 坐标值必须是 0-1000 之间的整数！
- 不要使用引号包裹数字或布尔值！"""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
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
                print(f"正在请求 Qwen-OCR 定位: {target_name} (尝试 {attempt + 1}/{max_retries}) ...")
                response = requests.post(self.base_url, json=payload, headers=headers, timeout=30)
                response.raise_for_status()
                res_json = response.json()
                content = res_json["choices"][0]["message"]["content"]
                
                # 4. 解析模型返回的坐标
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
                    # 处理 Python 布尔值首字母大写的问题
                    json_str = json_str.replace("True", "true").replace("False", "false")
                    norm_data = json.loads(json_str)
                    
                    found = norm_data.get("found", True) # 默认假设找到了，兼容旧格式
                    
                    # 如果模型明确表示没找到
                    if not found or str(found).lower() == "false":
                        print(f"模型报告：在图片中未找到目标 '{target_name}'")
                        return None
                        
                    norm_x = float(norm_data.get("norm_x", -1))
                    norm_y = float(norm_data.get("norm_y", -1))
                    
                except Exception as e:
                    # Fallback: 暴力提取数字
                    print(f"警告: JSON 解析失败 ({e})，尝试正则提取。原始字符串: {content[:100]}...")
                    
                    # 检查是否包含 false
                    if "false" in clean_content.lower():
                        print(f"模型报告：在图片中未找到目标 '{target_name}'")
                        return None
                        
                    norm_x_match = re.search(r'"?norm_x"?\s*:\s*(-?\d+(?:\.\d+)?)', clean_content)
                    norm_y_match = re.search(r'"?norm_y"?\s*:\s*(-?\d+(?:\.\d+)?)', clean_content)
                    
                    if norm_x_match and norm_y_match:
                        norm_x = float(norm_x_match.group(1))
                        norm_y = float(norm_y_match.group(1))
                    else:
                        nums = re.findall(r'-?\d+(?:\.\d+)?', match.group())
                        if len(nums) >= 2:
                            norm_x = float(nums[0])
                            norm_y = float(nums[1])
                            print(f"警告: 通过正则暴力提取到坐标: norm_x={norm_x}, norm_y={norm_y}")
                        else:
                            last_error = f"JSON 解析失败且无法提取数字"
                            print(last_error)
                            continue

                # 检查是否未找到目标 (兼容旧的 -1, -1 逻辑)
                if norm_x == -1 and norm_y == -1:
                    print(f"模型报告：在图片中未找到目标 '{target_name}'")
                    return None

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
                    return None

        print(f"定位目标 {target_name} 失败，已重试 {max_retries} 次。")
        return None


class BaiduTextAnchorService:
    """基于百度OCR的精准文字定位服务，提供与 QwenDetector 相同的接口"""
    def __init__(self, client_id='nc5WIHMwSorB469QbREyf8ZY', client_secret='ANPo5ZYGed4VK94k4qSuuqk9VXhtVgLd'):
        self.client_id = client_id
        self.client_secret = client_secret
        self.request_url = "https://aip.baidubce.com/rest/2.0/ocr/v1/accurate"
        self.access_token = self._get_token()

    def _get_token(self):
        """获取百度API的access_token"""
        url = 'https://aip.baidubce.com/oauth/2.0/token'
        params = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                return response.json().get("access_token")
            else:
                print(f"获取token失败: {response.text}")
                return None
        except Exception as e:
            print(f"请求获取token发生异常: {e}")
            return None

    def get_target_coords(self, image_source, target_name, max_retries=None):
        """
        核心业务：定位目标并换算坐标
        :param image_source: 可以是本地路径，也可以是 Base64 字符串
        :param target_name: 想要寻找的文字
        :param max_retries: 兼容参数，百度OCR通常不需要重试解析格式
        """
        if not self.access_token:
            print("未获取到access_token，无法进行OCR识别")
            return None

        if not image_source:
            print("错误：传入的 image_source 为空")
            return None

        # 1. 统一处理图片源
        try:
            if isinstance(image_source, str) and not image_source.startswith(('data:', 'iVBO')):
                # 说明是文件路径
                if not os.path.exists(image_source):
                    print(f"错误：找不到文件 {image_source}")
                    return None
                with open(image_source, "rb") as f:
                    img_base64 = base64.b64encode(f.read()).decode('utf-8')
            else:
                # 说明是 Base64 字符串
                img_base64 = image_source.replace('data:image/png;base64,', '')
        except Exception as e:
            print(f"处理图片源失败: {e}")
            return None

        # 2. 调用百度OCR API
        params = {
            "image": img_base64,
            "vertexes_location": "true"  # 返回文字位置信息
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        
        try:
            print(f"正在请求 百度OCR 定位: {target_name} ...")
            response = requests.post(
                self.request_url + "?access_token=" + self.access_token, 
                data=params, 
                headers=headers
            )
            result = response.json()
            
            # 3. 解析结果并查找目标
            if 'words_result' in result:
                for item in result['words_result']:
                    text = item.get('words', '')
                    location = item.get('location')
                    
                    # 模糊匹配目标文字
                    if target_name in text and location:
                        # 计算中心点坐标
                        center_x = int(location['left'] + location['width'] / 2)
                        center_y = int(location['top'] + location['height'] / 2)
                        
                        return {
                            "x": center_x,
                            "y": center_y,
                            "debug": f"百度OCR匹配到文字: '{text}', 区域: {location}"
                        }
                
                print(f"模型报告：在图片中未找到目标 '{target_name}'")
                return None
            else:
                print(f"OCR识别失败或无结果: {result}")
                return None
                
        except Exception as e:
            print(f"调用百度OCR API发生异常: {e}")
            return None

    def get_screen_text_map(self):
        """
        获取当前屏幕文字与物理坐标的映射业务
        Returns: { "文字内容": [中心x, 中心y], ... }
        """
        text_map = {}
        if not self.access_token:
            print("未获取到access_token，无法进行OCR识别")
            return text_map

        # 1. 截取屏幕
        screenshot = pyautogui.screenshot()
        
        # 2. 将截图转换为base64
        img_byte_arr = BytesIO()
        screenshot.save(img_byte_arr, format='PNG')
        img_bytes = img_byte_arr.getvalue()
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')

        # 3. 调用百度OCR API
        params = {
            "image": img_base64,
            "vertexes_location": "true"  # 返回文字位置信息
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        
        try:
            response = requests.post(
                self.request_url + "?access_token=" + self.access_token, 
                data=params, 
                headers=headers
            )
            result = response.json()
            
            # 4. 解析结果并计算中心坐标
            if 'words_result' in result:
                for item in result['words_result']:
                    text = item.get('words', '')
                    location = item.get('location')
                    
                    if text and location:
                        # 计算中心点坐标
                        center_x = int(location['left'] + location['width'] / 2)
                        center_y = int(location['top'] + location['height'] / 2)
                        
                        # 存入映射表，如果有重复文字，保留第一个
                        if text not in text_map:
                            text_map[text] = [center_x, center_y]
            else:
                print(f"OCR识别失败或无结果: {result}")
                
        except Exception as e:
            print(f"调用百度OCR API发生异常: {e}")
            
        return text_map

# ==========================================
# 全局 OCR 实例配置
# 以后更换 OCR 模型时，只需要在这里修改实例化的类即可
# ==========================================
ocr = BaiduTextAnchorService()

# --- 完整测试入口 ---
if __name__ == "__main__":
    # 测试图片路径（请确保目录下有 test.png）
    test_image = "test.png" 
    target = "此电脑"
    
    result = ocr.get_target_coords(test_image, target)
    
    if result:
        print("\n" + "="*30)
        print(f"目标【{target}】定位成功！")
        print(f"物理像素坐标: X={result['x']}, Y={result['y']}")
        print(f"调试信息: {result['debug']}")
        print("="*30)
        print(f"现在你可以直接执行: pyautogui.click({result['x']}, {result['y']})")
    else:
        print("\n定位失败，请检查网络、API Key 或图片内容。")
