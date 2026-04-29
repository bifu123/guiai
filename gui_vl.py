# gui_vl.py
import base64
import time
from zhipuai import ZhipuAI

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def glm_4_6v_flash(text, image_base64=None):
    # 你的 API Key 保持不变
    client = ZhipuAI(api_key="72932f11433b34acc283470ab987f86e.ctxyPjOALSRrxnox")
    
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
