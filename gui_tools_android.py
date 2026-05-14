# gui_tools_android.py
# 职责：AINS Android 节点专用 Agent 工具集

import os
from dotenv import load_dotenv

load_dotenv()

import requests
from typing import List, Dict, Any, Optional

# 默认读取环境变量，如果没有设置，则默认指向 Termux 本地 8000 端口
DEFAULT_ENDPOINT = os.getenv("GUI_CLIENT_URL_ANDROID", "http://192.168.66.40:8000/execute")

# 辅助函数：通用请求封装，处理与 gui_client_android_final.py 的通信
def _call_executor(payload: Dict[str, Any], endpoint: str) -> Dict[str, Any]:
    """
    通用请求封装，处理与 Android 执行器的通信
    """
    try:
        response = requests.post(endpoint, json=payload, timeout=20) # 考虑到手机响应稍慢，超时延长到 20s
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

#----------------------------
#  原始工具 (Android 适配版)
#----------------------------
# 在屏幕指定坐标执行点击 (映射到 adb shell input tap)。
def mouse_click(
    x: int, 
    y: int, 
    endpoint: str = DEFAULT_ENDPOINT
) -> Dict[str, Any]:
    """
    在屏幕指定坐标执行点击。用于点击按钮、打开 App 或聚焦输入框。

    Args:
        x (int): 目标的横坐标 (像素，以手机物理分辨率为准)。
        y (int): 目标的纵坐标 (像素，以手机物理分辨率为准)。
        endpoint (str): GUI 执行器的 URL 地址。

    Returns:
        Dict: 包含操作状态和执行后手机截图的 JSON。
    """
    payload = {
        "action": "click",
        "coords": [x, y],
        "text": "",
        "key": ""
    }
    return _call_executor(payload, endpoint)

# 在屏幕指定坐标执行双击 (Android 极少使用，保留以确保 Agent 兼容)。
def mouse_double_click(
    x: int, 
    y: int, 
    endpoint: str = DEFAULT_ENDPOINT
) -> Dict[str, Any]:
    """
    在屏幕指定坐标执行双击。(注：Android 通常使用单击即可打开 App，保留此方法用于向后兼容)。

    Args:
        x (int): 目标的横坐标 (像素)。
        y (int): 目标的纵坐标 (像素)。
        endpoint (str): GUI 执行器的 URL 地址。

    Returns:
        Dict: 包含操作状态和执行后手机截图的 JSON。
    """
    payload = {
        "action": "double_click",
        "coords": [x, y],
        "text": "",
        "key": ""
    }
    return _call_executor(payload, endpoint)

# 在指定位置点击聚焦并输入文本 (映射到 adb shell input text，已处理空格转义)。
def type_text(
    x: int, 
    y: int, 
    text: str, 
    endpoint: str = DEFAULT_ENDPOINT
) -> Dict[str, Any]:
    """
    在指定位置点击聚焦并输入文本字符串。用于填充表单、输入搜索内容。

    Args:
        x (int): 输入框的横坐标 (像素)。
        y (int): 输入框的纵坐标 (像素)。
        text (str): 要输入的文本内容。
        endpoint (str): GUI 执行器的 URL 地址。

    Returns:
        Dict: 包含操作状态和执行后手机截图的 JSON。
    """
    payload = {
        "action": "type",
        "coords": [x, y],
        "text": text,
        "key": ""
    }
    return _call_executor(payload, endpoint)

# 按下特殊功能按键（映射到 adb shell input keyevent）。
def press_key(
    x: int, 
    y: int, 
    key_name: str, 
    endpoint: str = DEFAULT_ENDPOINT
) -> Dict[str, Any]:
    """
    在 Android 上按下系统级按键。

    Args:
        x (int): 目标位置横坐标 (传 0 即可)。
        y (int): 目标位置纵坐标 (传 0 即可)。
        key_name (str): 按键名称。支持 'enter', 'back'(返回), 'home'(回到桌面), 'recent'(多任务)。
        endpoint (str): GUI 执行器的 URL 地址。

    Returns:
        Dict: 包含操作状态和执行后手机截图的 JSON。
    """
    payload = {
        "action": "key_press",
        "coords": [x, y],
        "text": "",
        "key": key_name
    }
    return _call_executor(payload, endpoint)

# 组合快捷键 (Android 环境基本失效，保留签名供 Agent 兼容)。
def use_hotkey(
    keys_combo: str, 
    x: int = 0, 
    y: int = 0, 
    endpoint: str = DEFAULT_ENDPOINT
) -> Dict[str, Any]:
    """
    触发组合快捷键（注：Android 环境不支持此特性，调用可能会被忽略）。

    Args:
        keys_combo (str): 组合键字符串。
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

# 在指定坐标位置执行滚动（映射为默认的上下滑动）。
def scroll_screen(
    x: int, 
    y: int, 
    endpoint: str = DEFAULT_ENDPOINT
) -> Dict[str, Any]:
    """
    执行屏幕滚动。在 Android 中通常表现为基础的滑动动作。若需精确控制，推荐使用 swipe_screen。

    Args:
        x (int): 滚动触发点的横坐标。
        y (int): 滚动触发点的纵坐标。
        endpoint (str): GUI 执行器的 URL 地址。

    Returns:
        Dict: 包含操作状态和执行后手机截图的 JSON。
    """
    payload = {
        "action": "scroll",
        "coords": [x, y],
        "text": "",
        "key": ""
    }
    return _call_executor(payload, endpoint)

# --- 新增：Android 专属滑动手势 ---
def swipe_screen(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    duration: int = 300,
    endpoint: str = DEFAULT_ENDPOINT
) -> Dict[str, Any]:
    """
    Android 专属功能：从起点滑动到终点。用于翻页或下拉刷新。

    Args:
        start_x (int): 滑动起点横坐标。
        start_y (int): 滑动起点纵坐标。
        end_x (int): 滑动终点横坐标。
        end_y (int): 滑动终点纵坐标。
        duration (int): 滑动持续时间(毫秒)，时间越长滑动越平缓，默认 300。
        endpoint (str): GUI 执行器的 URL 地址。

    Returns:
        Dict: 包含操作状态和执行后手机截图的 JSON。
    """
    payload = {
        "action": "drag", # 借用原系统的 drag 动作，在后端映射为 adb shell input swipe
        "coords": [start_x, start_y],
        "text": f"{end_x},{end_y},{duration}",
        "session_id": "swipe_session"
    }
    return _call_executor(payload, endpoint)

# 恢复启用的窗口控制逻辑 (映射到 Android 的系统导航)。
def control_window(
    mode: str = "maximize", 
    endpoint: str = DEFAULT_ENDPOINT
) -> Dict[str, Any]:
    """
    控制当前 Android 界面状态。

    Args:
        mode (str): 操作模式。可选值为 'minimize' (相当于按 Home 键回到桌面), 'close' (相当于按 Back 键返回)。
        endpoint (str): GUI 执行器的 URL 地址。

    Returns:
        Dict: 包含操作状态和执行后手机截图的 JSON。
    """
    payload = {
        "action": "window_control",
        "coords": [0, 0],
        "text": mode,
        "key": ""
    }
    return _call_executor(payload, endpoint)


#----------------------------
#  手动流程自动化工具
#----------------------------
from typing import Union
import os
import json

def execute_manual_flow(
    flow_data: Union[List[Dict[str, Any]], str], 
    endpoint: str = DEFAULT_ENDPOINT,
    time_sleep: float = 3.0,
    params: dict = None
) -> Dict[str, Any]:
    """
    顺次执行手动定义的流程自动化列表。支持从 JSON 文件读取或直接传入列表，并支持动态参数注入。
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

    print("\n========== 开始执行 Android 手动流程 ==========")
    last_screenshot = None
    
    try:
        for i, step in enumerate(flow_list):
            description = step.get("description", f"步骤 {i+1}")
            auto_data = step.get("auto", {})
            
            print(f"[{i+1}/{len(flow_list)}] 正在执行: {description}")
            
            # 解析动态参数
            text_val = auto_data.get("text", "")
            if text_val and params:
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
                "session_id": "manual_flow_session" # 保持 Android 设备的操作连贯性
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
            
            if i < len(flow_list) - 1:
                print(f"等待 {time_sleep} 秒...")
                time.sleep(time_sleep)
            
        print("========== Android 手动流程执行完毕 ==========\n")
        
        return {
            "status": "success",
            "message": "所有步骤执行完毕",
            "total_steps": len(flow_list),
            "screenshot": last_screenshot
        }
    finally:
        _call_executor({"action": "release_lock", "coords": [0, 0], "session_id": "manual_flow_session"}, endpoint)

#----------------------------
#  agent工具
#----------------------------
def run_for_agent(user_id:str, intent:str, max_attempts:int=5, gui_client_url:str=DEFAULT_ENDPOINT, show_img:bool=False, history:list=None) -> Dict[str, Any]:
    """
    执行 GUI Agent 任务，根据自然语言意图自动操作设备界面。
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
    
    result_dict = {
        "result": "GUI 操作结果\n\n",
        "coords": response.get("coords"),
        "attempts": response.get("attempts"),
        "img": response.get("img") if show_img else None
    }
    
    if response.get("status") == "success":
        result_dict["result"] += f'''操作成功：\n结果：{response.get("reason")}'''
        if response.get("thought"):
            result_dict["result"] += f'''\nAgent 思考/描述：\n{response.get("thought")}'''
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
    
    print("请选择 AINS Android 测试模式：")
    print("1. 测试 Agent 自然语言意图执行")
    print("2. 测试手动流程自动化 (Android 专用轨迹)")
    choice = input("请输入选项 (1 或 2): ")
    
    if choice == "1":
        print("." * 50)
        user_id = input("请输入测试用户ID (默认 ains_user): ") or "ains_user"
        intent = input("请输出你的操作意图 (例如: 打开微信)：")
        max_attempts = 5
        print("*" * 50, f'\n{run_for_agent(user_id=user_id, intent=intent, max_attempts=max_attempts, gui_client_url=DEFAULT_ENDPOINT, show_img=True)}')
        
    elif choice == "2":
        print("." * 50)
        print("请选择数据来源：")
        print("A. 使用内置测试列表 (自动点击屏幕中心并返回桌面)")
        print("B. 读取 JSON 文件")
        sub_choice = input("请输入选项 (A 或 B): ").strip().upper()
        
        if sub_choice == "A":
            print("正在加载内置 Android 流程数据...")
            # 这里的坐标已经适配了普通手机的分辨率 (如 1080x2400)
            test_flow = [
                {
                    "auto": {
                        "action": "click",
                        "coords": [540, 1200], # 屏幕中心点击
                        "text": "",
                        "key": ""
                    },
                    "description": "点击屏幕中心区域"
                },
                {
                    "auto": {
                        "action": "key_press",
                        "coords": [0, 0],
                        "text": "",
                        "key": "home" # 按下 Home 键
                    },
                    "description": "模拟按下 Home 键返回桌面"
                }
            ]
            result = execute_manual_flow(test_flow)
            
        elif sub_choice == "B":
            json_file = input("请输入轨迹文件路径：")
            print("正在读取 JSON 文件...")
            demo_params = {
                "username": "admin",
                "password": "123"
            }
            print(f"使用的动态参数: {demo_params}")
            result = execute_manual_flow(rf'{json_file}', params=demo_params)
        else:
            print("无效的选项。")
            exit()
        
        print("\n最终执行结果:")
        if "screenshot" in result and result["screenshot"]:
            screenshot_preview = result["screenshot"][:50] + "..."
            print(f"截图(base64前50字符): {screenshot_preview}")
            print_result = result.copy()
            print_result["screenshot"] = screenshot_preview
            print(json.dumps(print_result, ensure_ascii=False, indent=4))
        else:
            print(json.dumps(result, ensure_ascii=False, indent=4))
    else:
        print("无效的选项。")