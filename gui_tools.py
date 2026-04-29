# tools.py

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

# 在屏幕指定坐标执行鼠标左键单击。用于点击按钮、切换窗口或聚焦输入框。
def mouse_click(
    x: int, 
    y: int, 
    endpoint: str = "http://192.168.2.16:8000/execute"
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
    endpoint: str = "http://192.168.2.16:8000/execute"
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
    endpoint: str = "http://192.168.2.16:8000/execute"
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
    endpoint: str = "http://192.168.2.16:8000/execute"
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
    endpoint: str = "http://192.168.2.16:8000/execute"
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
    endpoint: str = "http://192.168.2.16:8000/execute"
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
#     endpoint: str = "http://192.168.2.16:8000/execute"
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



if __name__ == "__main__":
    import time
    

    # 1. 双击打开
    mouse_double_click(x=39, y=46) 
    time.sleep(2) # 窗口渲染需要时间
    
    # 2. 关键：点击窗口的大致位置（通常是中心或标题栏）来把窗口“提”到最前面
    # 这里我们点击屏幕中心 [960, 540]
    mouse_click(x=900, y=600)
    time.sleep(0.5)
    
