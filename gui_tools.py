# tools.py

import os
from dotenv import load_dotenv

load_dotenv()

import requests
from typing import List, Dict, Any, Optional

# 辅助函数：通用请求封装，处理与 gui_main.py 的通信
def _call_executor(payload: Dict[str, Any], endpoint: str) -> Dict[str, Any]:
    """
    通用请求封装，处理与 gui_main.py 的通信
    """
    try:
        response = requests.post(endpoint, json=payload, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

#----------------------------
#  原始工具
#----------------------------
# 在屏幕指定坐标执行鼠标左键单击。用于点击按钮、切换窗口或聚焦输入框。
def mouse_click(
    x: int, 
    y: int, 
    endpoint: str = os.getenv("GUI_CLIENT_URL")
) -> Dict[str, Any]:
    """
    在屏幕指定坐标执行鼠标左键单击。用于点击按钮、切换窗口或聚焦输入框。

    Args:
        x (int): 目标的横坐标 (像素)。
        y (int): 目标的纵坐标 (像素)。
        endpoint (str): GUI 执行器的 URL 地址。

    Returns:
        Dict: 包含操作状态和执行后桌面截图的 JSON。
    """
    payload = {
        "action": "click",
        "coords": [x, y],
        "text": "",
        "key": ""
    }
    return _call_executor(payload, endpoint)

# 在屏幕指定坐标执行鼠标左键双击。用于打开桌面图标或选中整行文本。
def mouse_double_click(
    x: int, 
    y: int, 
    endpoint: str = os.getenv("GUI_CLIENT_URL")
) -> Dict[str, Any]:
    """
    在屏幕指定坐标执行鼠标左键双击。用于打开桌面图标或选中整行文本。

    Args:
        x (int): 目标的横坐标 (像素)。
        y (int): 目标的纵坐标 (像素)。
        endpoint (str): GUI 执行器的 URL 地址。

    Returns:
        Dict: 包含操作状态和执行后桌面截图的 JSON。
    """
    payload = {
        "action": "double_click",
        "coords": [x, y],
        "text": "",
        "key": ""
    }
    return _call_executor(payload, endpoint)

# 在指定位置点击聚焦并输入文本字符串。用于填充表单、输入账号密码或 URL。
def type_text(
    x: int, 
    y: int, 
    text: str, 
    endpoint: str = os.getenv("GUI_CLIENT_URL")
) -> Dict[str, Any]:
    """
    在指定位置点击聚焦并输入文本字符串。用于填充表单、输入账号密码或 URL。

    Args:
        x (int): 输入框的横坐标 (像素)。
        y (int): 输入框的纵坐标 (像素)。
        text (str): 要输入的文本内容。
        endpoint (str): GUI 执行器的 URL 地址。

    Returns:
        Dict: 包含操作状态和执行后桌面截图的 JSON。
    """
    payload = {
        "action": "type",
        "coords": [x, y],
        "text": text,
        "key": ""
    }
    return _call_executor(payload, endpoint)

# 在指定坐标聚焦并按下特殊功能按键（如 Enter, Tab, Esc 等）。
def press_key(
    x: int, 
    y: int, 
    key_name: str, 
    endpoint: str = os.getenv("GUI_CLIENT_URL")
) -> Dict[str, Any]:
    """
    在指定坐标聚焦并按下特殊功能按键（如 Enter, Tab, Esc 等）。

    Args:
        x (int): 目标位置横坐标 (像素)。
        y (int): 目标位置纵坐标 (像素)。
        key_name (str): 按键名称，如 'enter', 'tab'。
        endpoint (str): GUI 执行器的 URL 地址。

    Returns:
        Dict: 包含操作状态和执行后桌面截图的 JSON。
    """
    payload = {
        "action": "key_press",
        "coords": [x, y],
        "text": "",
        "key": key_name
    }
    return _call_executor(payload, endpoint)

# 在指定坐标位置聚焦（若坐标非0）并触发组合快捷键（如 ctrl+v）。
def use_hotkey(
    keys_combo: str, 
    x: int = 0, 
    y: int = 0, 
    endpoint: str = os.getenv("GUI_CLIENT_URL")
) -> Dict[str, Any]:
    """
    在指定坐标位置聚焦（若坐标非0）并触发组合快捷键（如 ctrl+v）。

    Args:
        keys_combo (str): 组合键字符串，用 '+' 连接，如 'win+e'。
        x (int): 焦点坐标 X，默认为 0。
        y (int): 焦点坐标 Y，默认为 0。
        endpoint (str): GUI 执行器的 URL 地址。

    Returns:
        Dict: 包含操作状态和执行后桌面截图的 JSON。
    """
    payload = {
        "action": "hotkey",
        "coords": [x, y],
        "text": keys_combo,
        "key": ""
    }
    return _call_executor(payload, endpoint)

# 在指定坐标位置执行鼠标滚轮滚动（默认固定增量）。
def scroll_screen(
    x: int, 
    y: int, 
    endpoint: str = os.getenv("GUI_CLIENT_URL")
) -> Dict[str, Any]:
    """
    在指定坐标位置执行鼠标滚轮滚动（默认固定增量）。

    Args:
        x (int): 滚动触发点的横坐标。
        y (int): 滚动触发点的纵坐标。
        endpoint (str): GUI 执行器的 URL 地址。

    Returns:
        Dict: 包含操作状态和执行后桌面截图的 JSON。
    """
    payload = {
        "action": "scroll",
        "coords": [x, y],
        "text": "",
        "key": ""
    }
    return _call_executor(payload, endpoint)

# 在 gui_tools.py 中添加：

# def control_window(
#     mode: str = "maximize", 
#     endpoint: str = os.getenv("GUI_CLIENT_URL")
# ) -> Dict[str, Any]:
#     """
#     控制当前活动窗口的状态（最大化、最小化、关闭）。

#     Args:
#         mode (str): 操作模式。可选值为 'maximize' (最大化), 'minimize' (最小化), 'close' (关闭)。默认为 'maximize'。
#         endpoint (str): GUI 执行器的 URL 地址。

#     Returns:
#         Dict: 包含操作状态和执行后桌面截图的 JSON。
#     """
    
    
#     # 窗口控制通常针对当前激活的窗口，坐标传 [0, 0]
#     payload = {
#         "action": "window_control",
#         "coords": [0, 0],
#         "text": mode,
#         "key": ""
#     }
#     return _call_executor(payload, endpoint)


#----------------------------
#  手动流程自动化工具
#----------------------------
from typing import Union
import os
import json

def execute_manual_flow(
    flow_data: Union[List[Dict[str, Any]], str], 
    endpoint: str = os.getenv("GUI_CLIENT_URL"),
    time_sleep: float = 3.0,
    params: dict = None
) -> Dict[str, Any]:
    """
    顺次执行手动定义的流程自动化列表。支持从 JSON 文件读取或直接传入列表，并支持动态参数注入。
    
    Args:
        flow_data (Union[List[Dict], str]): 包含操作步骤的列表，或者 JSON 文件的绝对/相对路径。
            列表元素格式示例：
            [
                {
                    "auto": {
                        "action": "double_click",  # 动作类型: click, double_click, type, scroll, drag
                        "coords": [39, 945],       # 目标坐标 [x, y]
                        "text": "${username}",     # 文本内容，支持 ${var} 格式的动态参数占位符
                        "key": ""                  # 特殊按键（暂留）
                    },
                    "description": "输入用户名"      # 步骤描述，用于日志打印
                }
            ]
        endpoint (str): GUI 执行器的 URL 地址，默认为 os.getenv("GUI_CLIENT_URL")。
        time_sleep (float): 每一步执行后的等待时间（秒），用于给程序加载或窗口打开留出时间，默认 3.0 秒。
        params (dict, optional): 动态参数字典。如果 flow_data 的 text 字段中包含类似 `${username}` 的占位符，
            且 params 中存在对应的键（如 `{"username": "root"}`），则会自动将其替换为真实值。默认为 None。
        
        Returns:
        Dict: 包含最终执行状态的字典。
            成功示例: {"status": "success", "message": "所有步骤执行完毕", "total_steps": 5, "screenshot": "base64..."}
            失败示例: {"status": "failed", "error_step": 2, "description": "点击登录", "reason": "...", "screenshot": "base64..."}
            
    Examples:
        # 示例 1: 直接传入 JSON 文件路径
        result = execute_manual_flow(flow_data="record_flow.json")
        
        # 示例 2: 传入动态参数
        user_data = {"username": "admin", "password": "123"}
        result = execute_manual_flow(flow_data="login_flow.json", params=user_data)
        
        # 示例 3: 调整等待时间
        result = execute_manual_flow(flow_data="slow_loading_flow.json", time_sleep=5.0)
    """
    import time
    import re
    
    # 1. 参数校验与解析
    flow_list = []
    if isinstance(flow_data, str):
        if not os.path.exists(flow_data):
            return {"status": "failed", "reason": f"文件不存在: {flow_data}"}
        try:
            with open(flow_data, 'r', encoding='utf-8') as f:
                flow_list = json.load(f)
        except Exception as e:
            return {"status": "failed", "reason": f"读取或解析 JSON 文件失败: {e}"}
    elif isinstance(flow_data, list):
        flow_list = flow_data
    else:
        return {"status": "failed", "reason": "flow_data 必须是列表或文件路径字符串"}

    if not flow_list:
        return {"status": "failed", "reason": "流程列表为空"}

    # 2. 校验列表格式
    for i, step in enumerate(flow_list):
        if not isinstance(step, dict) or "auto" not in step:
            return {"status": "failed", "reason": f"第 {i+1} 步格式错误，缺少 'auto' 键"}
        auto_data = step["auto"]
        if "action" not in auto_data or "coords" not in auto_data:
            return {"status": "failed", "reason": f"第 {i+1} 步格式错误，'auto' 中缺少 'action' 或 'coords'"}

    print("\n========== 开始执行手动流程自动化 ==========")
    last_screenshot = None
    
    for i, step in enumerate(flow_list):
        description = step.get("description", f"步骤 {i+1}")
        auto_data = step.get("auto", {})
        
        print(f"[{i+1}/{len(flow_list)}] 正在执行: {description}")
        
        # 解析动态参数
        text_val = auto_data.get("text", "")
        if text_val and params:
            # 查找所有 ${var} 格式的占位符
            matches = re.findall(r'\$\{([^}]+)\}', text_val)
            for var_name in matches:
                if var_name in params:
                    text_val = text_val.replace(f"${{{var_name}}}", str(params[var_name]))
        
        # 构造请求 payload
        payload = {
            "action": auto_data.get("action", "click"),
            "coords": auto_data.get("coords", [0, 0]),
            "text": text_val,
            "key": auto_data.get("key", ""),
            "session_id": "manual_flow_session" # 使用固定 session_id 保持连贯性
        }
        
        # 调用执行器
        res = _call_executor(payload, endpoint)
        
        if res.get("status") != "success":
            error_msg = f"执行失败: {description}。原因: {res.get('message', res.get('reason', '未知错误'))}"
            print(f"❌ {error_msg}")
            return {
                "status": "failed",
                "error_step": i + 1,
                "description": description,
                "reason": error_msg,
                "screenshot": res.get("screenshot")
            }
            
        print(f"✅ 成功: {description}")
        last_screenshot = res.get("screenshot")
        
        # 步骤之间稍微停顿，等待界面响应
        if i < len(flow_list) - 1:
            print(f"等待 {time_sleep} 秒...")
            time.sleep(time_sleep)
        
    print("========== 手动流程自动化执行完毕 ==========\n")
    
    # 释放 session 锁
    _call_executor({"action": "release_lock", "coords": [0, 0], "session_id": "manual_flow_session"}, endpoint)
    
    return {
        "status": "success",
        "message": "所有步骤执行完毕",
        "total_steps": len(flow_list),
        "screenshot": last_screenshot
    }

#----------------------------
#  agent工具
#----------------------------
def run_for_agent(user_id:str, intent:str, max_attempts:int=5, gui_client_url:str=os.getenv("GUI_CLIENT_URL"), show_img:bool=False, history:list=None) -> Dict[str, Any]:
    """
    执行 GUI Agent 任务，根据自然语言意图自动操作桌面。

    Args:
        user_id (str): 用户的唯一标识符，用于区分不同的会话。
        intent (str): 用户的自然语言意图，例如 "在桌面上打开此电脑图标"。
        max_attempts (int, optional): 最大尝试次数。默认为 5。
        gui_client_url (str, optional): GUI 执行器的 URL 地址。默认为 os.getenv("GUI_CLIENT_URL")。
        show_img (bool, optional): 是否在成功时返回截图 base64。默认为 False。
        history (list, optional): 聊天对话历史，用于上下文推断。默认为 None。

    Returns:
        Dict[str, Any]: 包含操作结果、坐标、尝试次数和截图的字典。
    """
    
    from gui_agent import run_agent_task
    
    response = run_agent_task(
        user_id=user_id, 
        intent=intent, 
        history=history, 
        max_attempts=max_attempts, 
        gui_client_url=gui_client_url, 
        show_img=show_img
    )
    
    # 构造返回的字典结构
    result_dict = {
        "result": "GUI 操作结果\n\n",
        "coords": response.get("coords"),
        "attempts": response.get("attempts"),
        "img": response.get("img") if show_img else None
    }
    
    # 处理 query 类型（查询/描述屏幕）
    if response.get("action_type") == "query":
        result_dict["result"] += f'''屏幕描述：\n{response.get("description", "无法描述屏幕内容")}'''
        return result_dict
    
    # 处理 operate 类型（操作型）
    if response.get("status") == "success":
        result_dict["result"] += f'''操作成功：\n结果：{response.get("reason")}'''
    elif response.get("status") == "failed":
        result_dict["result"] += f'''操作失败：\n结果：{response.get("reason")}'''
        if "当前有其他任务正在执行" in response.get("reason", ""):
            result_dict["result"] += f'''\n建议：如果需要立即开始本任务，请先发送`/end`结束先前任务'''
    elif response.get("status") == "rejected":
        result_dict["result"] += f'''操作被拒绝：\n结果：{response.get("reason")}'''
    elif response.get("status") == "waiting_for_human":
        result_dict["result"] += f'''等待人工介入：\n结果：{response.get("reason")}'''
    elif response.get("status") == "updated":
        result_dict["result"] += f'''任务已更新：\n结果：{response.get("reason")}'''

    return result_dict


if __name__ == "__main__":
    import json
    
    print("请选择测试模式：")
    print("1. 测试 Agent 自然语言意图执行")
    print("2. 测试手动流程自动化 (执行 test.py 中的数据)")
    choice = input("请输入选项 (1 或 2): ")
    
    if choice == "1":
        print("." * 50)
        user_id = input("请输入测试用户ID (默认 test_user): ") or "test_user"
        intent = input("请输出你的操作意图：")
        max_attempts = 5
        gui_client_url = os.getenv("GUI_CLIENT_URL")
        print("*" * 50, f'\n{run_for_agent(user_id=user_id, intent=intent, max_attempts=max_attempts, gui_client_url=gui_client_url, show_img=True)}')
        
    elif choice == "2":
        print("." * 50)
        print("请选择数据来源：")
        print("A. 使用内置测试列表")
        print("B. 读取 record_flow.json 文件")
        sub_choice = input("请输入选项 (A 或 B): ").strip().upper()
        json_file = input("请输入轨迹文件路径：")
        
        if sub_choice == "A":
            print("正在加载内置流程数据...")
            test_flow = [
                {
                    "auto": {
                        "action": "double_click",
                        "coords": [38, 35],
                        "text": "",
                        "key": ""
                    },
                    "description": "打开我的电脑"
                },
                {
                    "auto": {
                        "action": "double_click",
                        "coords": [460, 147],
                        "text": "",
                        "key": ""
                    },
                    "description": "双击最大化窗口"
                },
                {
                    "auto": {
                        "action": "double_click",
                        "coords": [1048, 259],
                        "text": "",
                        "key": ""
                    },
                    "description": "打开E盘"
                }
            ]
            result = execute_manual_flow(test_flow)
        elif sub_choice == "B":
            print("正在读取 JSON 文件...")
            # 演示如何传入动态参数
            demo_params = {
                "username": "root",
                "password": "shift962512"
            }
            print(f"使用的动态参数: {demo_params}")
            result = execute_manual_flow(rf'{json_file}', params=demo_params)
        else:
            print("无效的选项。")
            exit()
        
        print("\n最终执行结果:")
        # 如果截图存在，打印前 50 个字符作为示意，保留完整数据在字典中
        if "screenshot" in result and result["screenshot"]:
            screenshot_preview = result["screenshot"][:50] + "..."
            print(f"截图(base64前50字符): {screenshot_preview}")
            # 为了控制台打印不刷屏，我们在打印 JSON 时临时替换一下，但 result 字典里依然是完整的 base64
            print_result = result.copy()
            print_result["screenshot"] = screenshot_preview
            print(json.dumps(print_result, ensure_ascii=False, indent=4))
        else:
            print(json.dumps(result, ensure_ascii=False, indent=4))
    else:
        print("无效的选项。")
