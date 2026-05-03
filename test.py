import requests
import json
import threading
import os
from dotenv import load_dotenv

load_dotenv()

def test_gui_server(intent, url):
    """
    模拟向 gui_server.py 发送请求
    """
    # 构造请求数据，匹配 gui_server.py 中的 AgentRequest 模型
    payload = {
        "user_id": "3787687088",
        "intent": intent,
        "history": [
            {
                "user_id": "3787687088",
                "source_id": "815669761",
                "user": "孙膑",
                "content": "廉颇将军，您这是在考我算术呢？🤔\n\n1 - 2 = -1，再加上 2，那就是 -1 + 2 = 1 啊！\n\n绕了一圈又回到了原点，正所谓\"江湖路远，终归故里\"啊！⚔️\n",
                "time": "2026-05-02 14:54:36"
            },
            {
                "user_id": "415135222",
                "source_id": "815669761",
                "user": "廉颇",
                "content": "@孙膑 再加上2呢？",
                "time": "2026-05-02 14:54:22"
            },
            {
                "user_id": "415135222",
                "source_id": "815669761",
                "user": "廉颇",
                "content": "1-2=？",
                "time": "2026-05-02 14:53:40"
            }
        ],
        "max_attempts": 3,
        "gui_client_url": os.getenv("GUI_CLIENT_URL"),
        "show_img": True
    }
    
    print(f"\n[线程启动] 正在向 {url} 发送请求: {intent}")
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status() # 检查 HTTP 错误
        
        result = response.json()
        print(f"\n--- 响应结果 (意图: {intent}) ---")
        # 如果截图存在，打印前 50 个字符作为示意
        if "img" in result and result["img"]:
            screenshot_preview = result["img"][:50] + "..."
            print_result = result.copy()
            print_result["img"] = screenshot_preview
            print(json.dumps(print_result, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        
    except requests.exceptions.RequestException as e:
        print(f"\n[请求失败] (意图: {intent}): {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"服务器返回: {e.response.text}")

if __name__ == "__main__":
    print("GUI Agent 测试客户端已启动。")
    print("提示：输入指令后会后台执行，你可以随时输入新指令或输入 /end 终止任务。")
    url = os.getenv("GUI_SERVER_URL")
    
    while True:
        intent = input("\n请输入你的指令：")
        if not intent.strip():
            continue
            
        # 使用多线程发送请求，避免阻塞主线程的 input
        thread = threading.Thread(target=test_gui_server, args=(intent, url))
        thread.daemon = True
        thread.start()
