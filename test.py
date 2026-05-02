import requests
import json

def test_gui_server():
    """
    模拟向 gui_server.py 发送请求
    """
    url = "http://192.168.2.16:8001/api/run_for_agent"
    intent = input("请输入你的指令：")
    
    # 构造请求数据，匹配 gui_server.py 中的 AgentRequest 模型
    payload = {
        "user_id": "test_user_123",
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
        "gui_client_url": "http://192.168.68.16:8000/execute",
        "show_img": False
    }
    
    print(f"正在向 {url} 发送请求...")
    print(f"请求数据: {json.dumps(payload, ensure_ascii=False, indent=2)}")
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status() # 检查 HTTP 错误
        
        result = response.json()
        print("\n--- 响应结果 ---")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    except requests.exceptions.RequestException as e:
        print(f"\n请求失败: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"服务器返回: {e.response.text}")

if __name__ == "__main__":
    test_gui_server()
