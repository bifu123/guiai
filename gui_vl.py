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

def process_image_for_ollama(image_base64, max_width=1280, max_height=800):
    """处理图片：去除前缀，限制最大分辨率，并保持 PNG 格式以防止模型解析卡死"""
    # 1. 去除可能存在的 data:image/...;base64, 前缀
    if image_base64.startswith('data:image'):
        image_base64 = image_base64.split(',', 1)[1]
        
    try:
        # 2. 解码图片
        img_data = base64.b64decode(image_base64)
        img = Image.open(BytesIO(img_data))
        
        orig_size = img.size
        orig_mode = img.mode
        
        # 拦截无效的极小图片 (例如 1x1 占位图)，防止 Ollama 模型崩溃
        if img.width < 10 or img.height < 10:
            raise ValueError(f"图片尺寸过小 ({img.width}x{img.height})，已被拦截以防止模型崩溃")
        
        # 3. 限制最大宽度或高度 (1280x800)
        if img.width > max_width or img.height > max_height:
            # 计算缩放比例，保持宽高比
            ratio = min(max_width / img.width, max_height / img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            
        # 4. 重新编码为 PNG base64 (保持 PNG 格式，避免 JPEG 导致的卡死)
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        new_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        print(f"[VL Image Process] 原始尺寸: {orig_size}, 模式: {orig_mode} -> 新尺寸: {img.size}, 格式: PNG")
        return new_base64
        
    except ValueError as ve:
        # 向上抛出 ValueError，让调用方知道这是被主动拦截的
        raise ve
    except Exception as e:
        print(f"图片预处理失败: {e}")
        return image_base64 # 如果处理失败，返回原始数据尝试

def ollama_qwen3_vl(text, image_base64=None):
    ollama_host = os.getenv("OLLAMA_HOST", "http://192.168.68.28:11434")
    client = ollama.Client(host=ollama_host)
    
    # 如果传入了 base64，则进行预处理；否则直接传递文件路径（与 test.py 保持一致）
    if image_base64:
        img_data = process_image_for_ollama(image_base64)
        images_param = [img_data]
    else:
        images_param = ['./test.png']
    
    messages = [{
        'role': 'user',
        'content': text,
        'images': images_param
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
