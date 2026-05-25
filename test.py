import ollama

# 1. 初始化客户端，指向远程 Ollama 服务器
client = ollama.Client(host='http://192.168.68.28:11434')

image_path = './test.png'

# 2. 使用 client.chat 代替 ollama.chat
response = client.chat(
    model='qwen3-vl', # vlm: qwen3-vl | ocr: deepseek-ocr
    messages=[{
        'role': 'user',
        'content': '请问这张图片里有什么。',
        'images': [image_path] 
    }]
)

# 打印识别结果
print(response['message']['content'])