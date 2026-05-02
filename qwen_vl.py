import os
import requests
import json
import base64
from dotenv import load_dotenv

# 加载环境变量，强制覆盖以确保读取到最新的 .env
load_dotenv(override=True)

# 从环境变量获取 SiliconFlow API Key
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY")

def qwen2_vl_72b_instruct(prompt: str, image_source: str) -> str:
    """
    调用 SiliconFlow 提供的 Qwen2.5-VL-72B-Instruct 模型
    
    Args:
        prompt (str): 提示词
        image_source (str): 图片的文件路径，或者是 base64 编码字符串
        
    Returns:
        str: 模型的文本回复
    """
    if not SILICONFLOW_API_KEY:
        raise ValueError("未找到 SILICONFLOW_API_KEY 环境变量，请在 .env 文件中配置。")

    # 打印前几个字符以确认读取到了正确的 Key
    print(f"[DEBUG] 当前使用的 API Key: {SILICONFLOW_API_KEY[:8]}...{SILICONFLOW_API_KEY[-4:]}")

    url = "https://api.siliconflow.cn/v1/chat/completions"
    
    # 判断是文件路径还是 base64
    if os.path.isfile(image_source):
        with open(image_source, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            image_data = f"data:image/png;base64,{encoded_string}"
    else:
        # 确保 base64 字符串带有正确的前缀
        if not image_source.startswith("data:image"):
            image_data = f"data:image/png;base64,{image_source}"
        else:
            image_data = image_source

    payload = {
        "model": "Qwen/Qwen2.5-VL-72B-Instruct",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_data,
                            "detail": "auto"
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ],
        "stream": False,
        "max_tokens": 4096,
        "temperature": 0.1, # 降低温度以获得更确定的输出（特别是 JSON）
        "top_p": 0.7,
        "top_k": 50,
        "frequency_penalty": 0.5,
        "n": 1
    }
    
    headers = {
        "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        result = response.json()
        
        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        else:
            print(f"API 返回格式异常: {result}")
            return ""
            
    except requests.exceptions.RequestException as e:
        print(f"调用 SiliconFlow API 失败: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"错误详情: {e.response.text}")
        raise

if __name__ == "__main__":
    # 简单的测试代码
    print("请确保 .env 文件中已配置 SILICONFLOW_API_KEY")
    
    test_image_path = "./test.png"
    if os.path.exists(test_image_path):
        print(f"正在测试读取本地图片: {test_image_path}")
        result = qwen2_vl_72b_instruct("描述这张图片", test_image_path)
        print("模型回复:")
        print(result)
    else:
        print(f"未找到测试图片 {test_image_path}，请准备一张图片用于测试。")
