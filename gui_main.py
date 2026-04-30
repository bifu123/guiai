# gui_main.py
# 职责：GUI 执行器服务端，负责接收 Agent 指令并操作本地操作系统

import uvicorn
from fastapi import FastAPI, HTTPException
import pyautogui
import base64
import time
import ctypes
import threading
import sys
import os
import pystray
from PIL import Image, ImageDraw
from io import BytesIO
from pydantic import BaseModel
from typing import List, Optional
import uiautomation as auto

# --- 0. 解决 PyInstaller --noconsole 模式下 stdout/stderr 丢失导致崩溃的问题 ---
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

# --- 1. 核心初始化：彻底解决高分屏点击偏移业务 ---
try:
    # 业务逻辑：告诉 Windows，本程序会自己处理缩放，不要帮我做逻辑坐标转换
    # 这样 pyautogui 拿到的坐标和屏幕真实的像素坐标就是 1:1 对应的
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception as e:
    print(f"DPI 意识设置失败: {e}")

# 禁用 PyAutoGUI 的安全故障保护（防止 Agent 把鼠标移到屏幕角落导致报错停机）
pyautogui.FAILSAFE = False
# 动作之间的默认间隔（留出系统响应时间）
pyautogui.PAUSE = 0.5 

app = FastAPI(title="Guiai 桌面执行器职责端")

# 全局 Session 锁，保障单任务独占执行，支持长任务和超时自动释放
current_session_id = None
last_active_time = 0
SESSION_TIMEOUT = 120 # 闲置超时时间（秒）
session_lock = threading.Lock() # 用于保护 session 变量的并发修改

# 定义数据结构业务
class ActionRequest(BaseModel):
    action: str            # 动作类型: click, double_click, type, scroll, key_press, hotkey, screenshot, release_lock, find_element
    coords: List[int]      # 物理像素坐标: [x, y]
    text: Optional[str] = "" # 输入的内容或查找的元素名称
    key: Optional[str] = ""  # 特殊按键 (Enter, Tab 等)
    session_id: str = ""   # 任务会话 ID，用于独占控制

def capture_screen_base64():
    """捕获当前全屏并转为高质量 Base64 的业务"""
    # 截取全屏
    screenshot = pyautogui.screenshot()
    buffered = BytesIO()
    # 使用 PNG 格式确保截图文字清晰，方便 OCR 识别
    screenshot.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_str

@app.post("/execute")
def execute_action(req: ActionRequest):
    """
    接收指令并执行具体操作系统操作的职责
    """
    global current_session_id, last_active_time
    
    # --- Session 锁逻辑 ---
    with session_lock:
        now = time.time()
        # 如果当前没有 session，或者 session 已经闲置超时
        if current_session_id is None or (now - last_active_time) > SESSION_TIMEOUT:
            if req.action == "release_lock":
                return {"status": "success", "message": "Lock already free"}
            # 接受新任务
            current_session_id = req.session_id
            last_active_time = now
            print(f"[{now}] 接受新任务 Session: {current_session_id}")
        else:
            # 当前有任务正在执行
            if req.session_id != current_session_id:
                print(f"[{now}] 拒绝请求：当前有任务正在执行 (Session: {current_session_id})")
                raise HTTPException(status_code=429, detail="当前有任务正在执行，请稍后再试")
            else:
                # 是同一个任务，刷新活跃时间
                last_active_time = now
                
        # 如果是主动释放锁的请求
        if req.action == "release_lock":
            print(f"[{now}] 任务主动释放锁 Session: {current_session_id}")
            current_session_id = None
            return {"status": "success", "message": "Lock released"}

    try:
        x, y = req.coords
        print(f"执行业务: {req.action} | 坐标: {req.coords} | 内容: {req.text or req.key} | Session: {req.session_id}")

        # --- 分发动作职责 ---
        if req.action == "find_element":
            # UIAutomation 查找元素业务
            target_name = req.text
            print(f"正在使用 UIAutomation 查找元素: {target_name}")
            
            # 设置查找超时时间（秒）
            auto.SetGlobalSearchTimeout(2.0)
            
            # 尝试查找包含该名称的控件
            # 这里使用 Control(searchDepth=8) 限制搜索深度，避免全树搜索太慢
            # Name 属性通常对应屏幕上显示的文本
            # 注意：在多线程中使用 UIAutomation 需要初始化 COM
            with auto.UIAutomationInitializerInThread():
                control = auto.Control(Name=target_name, searchDepth=8)
                
                if control.Exists(0, 0):
                    rect = control.BoundingRectangle
                    # 计算中心点坐标
                    center_x = rect.left + (rect.right - rect.left) // 2
                    center_y = rect.top + (rect.bottom - rect.top) // 2
                    print(f"UIAutomation 找到元素 '{target_name}'，中心坐标: [{center_x}, {center_y}]")
                    return {
                        "status": "success",
                        "action_performed": "find_element",
                        "coords": [center_x, center_y],
                        "screenshot": capture_screen_base64() # 保持接口一致性
                    }
                else:
                    print(f"UIAutomation 未找到元素 '{target_name}'")
                    return {
                        "status": "failed",
                        "action_performed": "find_element",
                        "reason": "Element not found by UIAutomation",
                        "screenshot": capture_screen_base64()
                    }

        elif req.action == "screenshot":
            # 仅拍照业务
            pass

        elif req.action == "click":
            # 单击业务
            pyautogui.click(x, y)
            
        elif req.action == "double_click":
            # 双击业务（常用于打开桌面图标）
            pyautogui.doubleClick(x, y)
            
        elif req.action == "type":
            # 文本输入业务
            if req.coords != [0, 0]:
                pyautogui.click(x, y) # 先点击定位焦点
            time.sleep(0.2)
            pyautogui.write(req.text, interval=0.1)
            
        elif req.action == "key_press":
            # 特殊单键按下 (如 enter, esc, backspace)
            pyautogui.press(req.key.lower())
            
        elif req.action == "hotkey":
            # 组合键业务 (如 ctrl+c, alt+f4)
            keys = req.text.split('+')
            pyautogui.hotkey(*[k.strip().lower() for k in keys])
            
        elif req.action == "scroll":
            # 滚轮操作业务
            pyautogui.scroll(-500 if req.text == "down" else 500, x=x, y=y)
            
        elif req.action == "window_control":
            # 窗口控制业务：maximize, minimize, close
            if req.coords != [0, 0]:
                pyautogui.click(x, y) # 尝试点击标题栏夺取焦点
            
            time.sleep(0.2)
            if req.text == "maximize":
                pyautogui.hotkey('win', 'up')
            elif req.text == "minimize":
                pyautogui.hotkey('win', 'down')
            elif req.text == "close":
                pyautogui.hotkey('alt', 'f4')

        # --- 动作完成后统一回传最新截图 ---
        # 这一步职责是让 Agent 看到操作后的反馈
        time.sleep(1.0) # 等待 UI 刷新动画
        new_screenshot = capture_screen_base64()
        
        return {
            "status": "success",
            "action_performed": req.action,
            "screenshot": new_screenshot
        }

    except Exception as e:
        print(f"执行异常: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def run_server():
    """在后台线程运行 FastAPI 服务"""
    print("GUI 执行器已启动，等待 Agent 指令...")
    # 注意：在多线程中运行 uvicorn，需要设置 log_config=None 避免日志冲突，或者保持默认
    uvicorn.run(app, host="0.0.0.0", port=8000)

def create_image():
    """生成一个简单的托盘图标（蓝色正方形带白色 G 字）"""
    width = 64
    height = 64
    color1 = (0, 120, 215) # Windows 蓝
    color2 = (255, 255, 255)
    
    image = Image.new('RGB', (width, height), color1)
    dc = ImageDraw.Draw(image)
    # 画一个简单的 G
    dc.text((20, 15), "G", fill=color2, font=None, align="center")
    return image

def on_quit(icon, item):
    """退出程序的处理函数"""
    icon.stop()
    # 强制结束整个进程（因为 uvicorn 线程可能还在运行）
    os._exit(0)

if __name__ == "__main__":
    # 1. 启动 FastAPI 后台线程
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # 2. 创建并运行系统托盘图标（必须在主线程）
    icon_image = create_image()
    menu = pystray.Menu(
        pystray.MenuItem("GUI Agent 执行器运行中...", lambda: None, enabled=False),
        pystray.MenuItem("退出", on_quit)
    )
    
    icon = pystray.Icon("GUI_Agent", icon_image, "GUI Agent 执行器", menu)
    # 运行托盘图标（这是一个阻塞调用，直到用户点击退出）
    icon.run()
