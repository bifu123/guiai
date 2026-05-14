import requests
import json
import threading
import os
from dotenv import load_dotenv

load_dotenv()

# 向 GUI Agent 发起请求，通过直接操作电脑桌面的方式来完成目标任务
def gui_trask_invoke(intent:str, user_id:str, gui_server_url:str="http://192.168.66.41:8001/api/run_for_agent", gui_client_url:str="http://192.168.66.42:8000/execute", history:dict=None, device_type:str="pc"):
    """
    向 GUI Agent 发起请求，通过直接操作电脑桌面的方式来完成目标任务
    Args:
        intent: (str) 操作电脑的指令。如：请打此电脑
        user_id: (str) 用户的user_id
        gui_server_url: (str) GUI 服务端，默认为`http://192.168.66.41:8001/api/run_for_agent`
        gui_client_url: (str) GUI 客户端，默认为`http://192.168.66.42:8000/execute`
        history: (dict) 聊天历史上下文
        device_type: (str) 设备类型，"pc" 或 "android"
    Returns:
        操作结果提示(dict)
    Notice：
        - 输入指令后会后台执行，你可以随时发送新指令或发送`/end`终止任务
        - GUI Agent 执行时，如果不是补充、更改、修正已发出指令，请耐心等待返回结果
    """
    
    # 构造请求数据，匹配 gui_server.py 中的 AgentRequest 模型
    payload = {
        "user_id": user_id,
        "intent": intent,
        "history": history,
        "max_attempts": 3,
        "gui_client_url": gui_client_url,
        "show_img": True,
        "device_type": device_type
    }
    
    print(f"\n[线程启动] 正在向 {gui_server_url} 发送请求: {intent}")
    
    try:
        response = requests.post(gui_server_url, json=payload)
        response.raise_for_status() # 检查 HTTP 错误
        
        result = response.json()
        
        if result.get("img"):
            print('[GUI] 发送图片到聊天界面...')
            
        print(result)
        
        return result
        
    except requests.exceptions.RequestException as e:
        result = f"\n[请求失败] (意图: {intent}): {e}"
        if hasattr(e, 'response') and e.response is not None:
            result = f"服务器返回: {e.response.text}"
        print(result)
        return result


# 向 GUI Server 发起手动流程自动化请求，按预定义的步骤列表顺次执行桌面操作
def gui_trask_flow(
    flow_data,
    gui_server_url: str = "http://192.168.66.41:8001/api/execute_manual_flow",
    gui_client_url: str = "http://192.168.66.42:8000/execute",
    time_sleep: float = 3.0,
    params: dict = None
):
    """
    向 GUI Server 发起手动流程自动化请求，按预定义的步骤列表顺次执行桌面操作。
    
    Args:
        flow_data: (list or str) 操作步骤列表，或 JSON 文件的路径字符串。
        gui_server_url: (str) GUI 服务端地址
        gui_client_url: (str) GUI 客户端地址
        time_sleep: (float) 每一步执行后的等待时间（秒）
        params: (dict, optional) 动态参数字典
    Returns:
        dict: 服务器返回的执行结果
    """
    payload = {
        "flow_data": flow_data,
        "endpoint": gui_client_url,
        "time_sleep": time_sleep,
        "params": params
    }
    
    print(f"\n[线程启动] 正在向 {gui_server_url} 发送手动流程自动化请求")
    
    try:
        response = requests.post(gui_server_url, json=payload)
        response.raise_for_status()
        result = response.json()
        print(result)
        return result
    except requests.exceptions.RequestException as e:
        result = f"\n[请求失败]: {e}"
        if hasattr(e, 'response') and e.response is not None:
            result = f"服务器返回: {e.response.text}"
        print(result)
        return result
    
    

if __name__ == "__main__":
    print("\n提示：输入指令后会后台执行，你可以随时输入新指令或输入 /end 终止任务。")
    
    user_id = "415135222"
    gui_server_url = os.getenv("GUI_SERVER_URL")
    gui_client_url = os.getenv("GUI_CLIENT_URL_ANDROID")
    history = [
            {
                "user_id": user_id,
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
        ]
    
    while True:
        intent = input("\n请输入你的指令：")
        if not intent.strip():
            continue
            
        thread = threading.Thread(target=gui_trask_invoke, args=(intent, user_id, gui_server_url, gui_client_url, history, "android"))
        thread.daemon = True
        thread.start()
    


    # gui_server_url = "http://192.168.66.41:8001/api/execute_manual_flow"
    # gui_client_url = "http://192.168.66.42:8000/execute"
    
    # # # 执行JSON参数的轨迹重播
    # # test_flow = [
    # #     {
    # #         "auto": {
    # #             "action": "double_click",
    # #             "coords": [38, 35],
    # #             "text": "",
    # #             "key": ""
    # #         },
    # #         "description": "双击打开此电脑"
    # #     },
    # #     {
    # #         "auto": {
    # #             "action": "double_click",
    # #             "coords": [460, 147],
    # #             "text": "",
    # #             "key": ""
    # #         },
    # #         "description": "双击最大化窗口"
    # #     },
    # #     {
    # #         "auto": {
    # #             "action": "double_click",
    # #             "coords": [1048, 259],
    # #             "text": "",
    # #             "key": ""
    # #         },
    # #         "description": "双击打开E盘"
    # #     }
    # # ]
    # # gui_trask_flow(flow_data=test_flow, gui_server_url=gui_server_url, gui_client_url=gui_client_url)
    
    # # # 执行JSON文件为参数的轨迹重播
    # # json_file = input("请输入流程 JSON 文件路径: ").strip()
    # # if not json_file or not os.path.exists(json_file):
    # #     print(f"❌ 文件不存在: {json_file}")
    # #     exit()
    # # gui_trask_flow(flow_data=json_file, gui_server_url=gui_server_url, gui_client_url=gui_client_url)
    
    # #  # 执行JSON文件（带参数）为参数的轨迹重播
    # # json_file = input("请输入流程 JSON 文件路径: ").strip()
    
    # json_file = [
    #     {
    #         "auto": {
    #             "action": "click",
    #             "coords": [
    #                 426,
    #                 266
    #             ],
    #             "text": "",
    #             "key": ""
    #         },
    #         "description": "点击用户名输入框获得焦点"
    #     },
    #     {
    #         "auto": {
    #             "action": "type",
    #             "coords": [
    #                 0,
    #                 0
    #             ],
    #             "text": "${nickName}",
    #             "key": ""
    #         },
    #         "description": "输入用户名"
    #     },
    #     {
    #         "auto": {
    #             "action": "click",
    #             "coords": [
    #                 422,
    #                 328
    #             ],
    #             "text": "",
    #             "key": ""
    #         },
    #         "description": "输入留言内容"
    #     },
    #     {
    #         "auto": {
    #             "action": "type",
    #             "coords": [
    #                 0,
    #                 0
    #             ],
    #             "text": "${content}",
    #             "key": ""
    #         },
    #         "description": "type content"
    #     },
    #     {
    #         "auto": {
    #             "action": "click",
    #             "coords": [
    #                 623,
    #                 424
    #             ],
    #             "text": "",
    #             "key": ""
    #         },
    #         "description": "提交留言"
    #     }
    # ]
    
    # # 模板参数
    # params = {
    #     "nickName": "大好",
    #     "content": "test"
    # }
    
    # gui_trask_flow(flow_data=json_file, gui_server_url=gui_server_url, gui_client_url=gui_client_url, params=params)
