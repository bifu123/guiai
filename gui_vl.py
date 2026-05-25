# gui_vl.py
import base64
import time
import os
from zhipuai import ZhipuAI
from dotenv import load_dotenv
import ollama

load_dotenv()

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def glm_4_6v_flash(text, image_base64=None):
    # 从环境变量获取 API Key
    api_key = os.getenv("ZHIPU_API_KEY")
    if not api_key:
        raise ValueError("未找到 ZHIPU_API_KEY 环境变量，请在 .env 文件中配置")
    client = ZhipuAI(api_key=api_key)
    
    # 如果传入了 base64 则直接使用，否则读取 test.png
    img_data = image_base64 if image_base64 else encode_image("test.png")
    
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": text},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_data}"}}
            ]
        }
    ]
    
    # 降低 temperature 增加确定性，这对 GUI 定位业务至关重要
    max_retries = 10
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="glm-4.6v-flash",
                messages=messages,
                max_tokens=1000,
                temperature=0.01  
            )
            content = response.choices[0].message.content
            if content is None or content.strip() == "":
                raise ValueError("模型返回了空内容，可能是限流导致的降级响应")
            return content
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"调用模型失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                print("等待 2 秒后重试...")
                time.sleep(2)
            else:
                print(f"调用模型失败，已达到最大重试次数: {e}")
                raise e

from io import BytesIO
from PIL import Image

def process_image_for_ollama(image_base64):
    """处理图片：去除前缀，并限制最大分辨率以防止 OOM"""
    # 1. 去除可能存在的 data:image/...;base64, 前缀
    if image_base64.startswith('data:image'):
        image_base64 = image_base64.split(',', 1)[1]
        
    try:
        # 2. 解码并检查尺寸
        img_data = base64.b64decode(image_base64)
        img = Image.open(BytesIO(img_data))
        
        # 限制最大宽度或高度，例如 1920
        max_size = 1920
        if img.width > max_size or img.height > max_size:
            # 等比例缩放
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            # 重新编码为 base64
            buffered = BytesIO()
            # 如果是 RGBA 转换为 RGB
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            img.save(buffered, format="JPEG", quality=85)
            return base64.b64encode(buffered.getvalue()).decode('utf-8')
            
        return image_base64
    except Exception as e:
        print(f"图片预处理失败: {e}")
        return image_base64 # 如果处理失败，返回原始数据尝试

def ollama_qwen3_vl(text, image_base64=None):
    client = ollama.Client(host='http://192.168.68.28:11434')
    
    # 如果传入了 base64 则直接使用，否则读取 test.png
    raw_img_data = image_base64 if image_base64 else encode_image("test.png")
    
    # 预处理图片
    img_data = process_image_for_ollama(raw_img_data)
    
    messages = [{
        'role': 'user',
        'content': text,
        'images': [img_data]
    }]
    
    max_retries = 10
    for attempt in range(max_retries):
        try:
            # 移除 options={'temperature': 0.01}，与 test.py 保持一致，避免参数不兼容
            response = client.chat(
                model='qwen3-vl',
                messages=messages
            )
            content = response.get('message', {}).get('content', '')
            if content is None or content.strip() == "":
                raise ValueError("模型返回了空内容")
            return content
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"调用模型失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                print("等待 2 秒后重试...")
                time.sleep(2)
            else:
                print(f"调用模型失败，已达到最大重试次数: {e}")
                raise e

# 统一的视觉模型接口
vlm = ollama_qwen3_vl

if __name__ == "__main__":
    print("正在测试 ollama_qwen3_vl...")
    try:
        result = ollama_qwen3_vl("请问这张图片里有什么。")
        print("测试成功！模型返回结果：")
        print(result)
    except Exception as e:
        print(f"测试失败: {e}")
