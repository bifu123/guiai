# gui_client_android.py
# 职责：Android 终端执行器服务端，负责接收 Agent 指令并操作手机屏幕底层业务
# 架构规范：遵循 AINS 理念，将动作抽象为标准 API，通过 ADB 协议驱动设备

import uvicorn
from fastapi import FastAPI, HTTPException
import base64
import time
import threading
import sys
import os
import subprocess
import re
import xml.etree.ElementTree as ET
from pydantic import BaseModel
from typing import List, Optional

# --- 0. 环境初始化业务 ---
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

app = FastAPI(title="Guiai Android 执行器职责端")

# 全局 Session 锁，保障单任务独占执行业务，支持长任务和超时自动释放
current_session_id = None
last_active_time = 0
SESSION_TIMEOUT = 120 # 闲置超时时间（秒）
session_lock = threading.Lock()

# 基础目录配置，用于临时存放截图和布局文件
TEMP_DIR = "/sdcard/guiai_temp"
os.system(f"adb shell mkdir -p {TEMP_DIR}")

# 定义标准数据结构业务
class ActionRequest(BaseModel):
    action: str            # 动作类型: click, double_click, type, scroll, key_press, hotkey, screenshot, release_lock, find_element, drag, window_control
    coords: List[int]      # 物理像素坐标: [x, y]
    text: Optional[str] = "" # 输入的内容或查找的元素名称
    key: Optional[str] = ""  # 特殊按键
    session_id: str = ""   # 任务会话 ID，用于独占控制
    scroll_dir: Optional[str] = None  # 滚动方向: down, up, left, right
    scroll_dist: Optional[int] = None # 滚动距离

# --- 底层驱动调用业务 ---
def run_adb(cmd: str, wait: bool = True):
    """执行 adb shell 命令的底层职责"""
    full_cmd = f"adb shell {cmd}"
    if wait:
        result = subprocess.run(full_cmd.split(), capture_output=True, text=True)
        return result.stdout.strip()
    else:
        subprocess.Popen(full_cmd.split())
        return ""

def capture_screen_base64():
    """捕获当前手机屏幕并转为高质量 Base64 的业务"""
    remote_path = f"{TEMP_DIR}/screen.png"
    local_path = "screen_local.png"
    
    # 手机端截图
    run_adb(f"screencap -p {remote_path}")
    # 拉取到本地执行环境 (Termux)
    subprocess.run(["adb", "pull", remote_path, local_path], capture_output=True)
    
    try:
        with open(local_path, "rb") as f:
            img_str = base64.b64encode(f.read()).decode("utf-8")
        return img_str
    except Exception as e:
        print(f"截图读取失败: {e}")
        return ""

def find_element_bounds(target_name: str) -> Optional[List[int]]:
    """解析 Android 屏幕 UI 树，查找指定语义节点并返回中心坐标 [x, y]"""
    remote_xml = f"{TEMP_DIR}/window_dump.xml"
    local_xml = "window_dump_local.xml"
    
    # 导出 UI 布局
    run_adb(f"uiautomator dump {remote_xml}")
    subprocess.run(["adb", "pull", remote_xml, local_xml], capture_output=True)
    
    if not os.path.exists(local_xml):
        return None

    try:
        tree = ET.parse(local_xml)
        root = tree.getroot()
        
        # 遍历所有节点寻找匹配的 text 或 content-desc
        for node in root.iter('node'):
            text = node.attrib.get('text', '')
            desc = node.attrib.get('content-desc', '')
            
            if target_name in text or target_name in desc:
                bounds_str = node.attrib.get('bounds', '')
                # bounds 格式: "[left,top][right,bottom]"
                match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds_str)
                if match:
                    left, top, right, bottom = map(int, match.groups())
                    center_x = left + (right - left) // 2
                    center_y = top + (bottom - top) // 2
                    return [center_x, center_y]
    except Exception as e:
        print(f"UI 树解析异常: {e}")
    
    return None

# --- API 路由与动作分发业务 ---
@app.post("/execute")
def execute_action(req: ActionRequest):
    """
    接收指令并执行具体手机系统操作的职责
    """
    global current_session_id, last_active_time
    
    # --- Session 锁逻辑 ---
    with session_lock:
        now = time.time()
        if current_session_id is None or (now - last_active_time) > SESSION_TIMEOUT:
            if req.action == "release_lock":
                return {"status": "success", "message": "Lock already free"}
            current_session_id = req.session_id
            last_active_time = now
            print(f"[{now}] 接受新任务 Session: {current_session_id}")
        else:
            if req.session_id != current_session_id:
                print(f"[{now}] 拒绝请求：当前有任务正在执行 (Session: {current_session_id})")
                raise HTTPException(status_code=429, detail="当前有任务正在执行，请稍后再试")
            else:
                last_active_time = now
                
        if req.action == "release_lock":
            print(f"[{now}] 任务主动释放锁 Session: {current_session_id}")
            current_session_id = None
            return {"status": "success", "message": "Lock released"}

    try:
        x, y = req.coords
        print(f"执行业务: {req.action} | 坐标: {req.coords} | 内容: {req.text or req.key} | Session: {req.session_id}")

        # --- 分发动作职责 ---
        if req.action == "find_element":
            print(f"正在分析 UI 树查找语义节点: {req.text}")
            coords = find_element_bounds(req.text)
            
            if coords:
                print(f"语义节点 '{req.text}' 定位成功，中心坐标: {coords}")
                return {
                    "status": "success",
                    "action_performed": "find_element",
                    "coords": coords,
                    "screenshot": capture_screen_base64()
                }
            else:
                print(f"未找到节点 '{req.text}'")
                return {
                    "status": "failed",
                    "action_performed": "find_element",
                    "reason": "Element not found in UI tree",
                    "screenshot": capture_screen_base64()
                }

        elif req.action == "screenshot":
            # 仅拍照业务
            pass

        elif req.action == "click":
            # 坐标点击业务
            run_adb(f"input tap {x} {y}")
            
        elif req.action == "double_click":
            # 双击业务
            run_adb(f"input tap {x} {y}")
            time.sleep(0.1)
            run_adb(f"input tap {x} {y}")
            
        elif req.action == "type":
            # 文本输入业务
            if req.coords != [0, 0]:
                run_adb(f"input tap {x} {y}")
            time.sleep(0.5)
            # 注意：原生 ADB 输入中文可能存在乱码，如需稳定中文支持可后续引入 ADBKeyBoard
            escaped_text = req.text.replace(' ', '%s')
            run_adb(f"input text '{escaped_text}'")
            
        elif req.action == "key_press":
            # 物理按键映射业务
            key_map = {
                "enter": "66", "esc": "111", "backspace": "67", 
                "home": "3", "back": "4", "tab": "61"
            }
            keycode = key_map.get(req.key.lower(), "")
            if keycode:
                run_adb(f"input keyevent {keycode}")
            
        elif req.action == "scroll" or req.action == "drag":
            # 滑动与拖拽业务归一化
            # 手机屏幕滑动通常从中心向边缘，此处做通用距离推算
            start_x, start_y = x, y
            end_x, end_y = x, y
            distance = req.scroll_dist if req.scroll_dist is not None else 500
            
            if req.action == "drag" and req.text:
                try:
                    ex_str, ey_str = req.text.split(',')
                    end_x, end_y = int(ex_str), int(ey_str)
                except: pass
            else:
                direction = req.scroll_dir or (req.text if req.text in ["down", "up", "left", "right"] else "down")
                if direction == "up":    end_y = max(0, y - distance)
                elif direction == "down":  end_y = y + distance
                elif direction == "left":  end_x = max(0, x - distance)
                elif direction == "right": end_x = x + distance
                
            run_adb(f"input swipe {start_x} {start_y} {end_x} {end_y} 500") # 500ms 滑动时长
            
        elif req.action == "window_control":
            # 手机级系统控制业务
            if req.text == "home" or req.text == "minimize":
                run_adb("input keyevent 3") # HOME 键
            elif req.text == "back" or req.text == "close":
                run_adb("input keyevent 4") # BACK 键
            elif req.text == "recents":
                run_adb("input keyevent 187") # 任务列表

        # --- 动作完成后统一回传最新系统状态 ---
        time.sleep(1.0) # 等待界面动画渲染完成
        new_screenshot = capture_screen_base64()
        
        return {
            "status": "success",
            "action_performed": req.action,
            "screenshot": new_screenshot
        }

    except Exception as e:
        print(f"执行异常: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("Android GUI 执行器已启动，端口 8000，等待 Agent 调度指令...")
    # 直接在主线程启动 Uvicorn 服务，无需后台守护线程
    uvicorn.run(app, host="0.0.0.0", port=8000)