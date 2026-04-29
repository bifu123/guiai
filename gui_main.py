# gui_main.py
# 职责：GUI 执行器服务端，负责接收 Agent 指令并操作本地操作系统

import uvicorn
from fastapi import FastAPI, HTTPException
import pyautogui
import base64
import time
import ctypes
from io import BytesIO
from pydantic import BaseModel
from typing import List, Optional

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

# 定义数据结构业务
class ActionRequest(BaseModel):
    action: str            # 动作类型: click, double_click, type, scroll, key_press, hotkey, screenshot
    coords: List[int]      # 物理像素坐标: [x, y]
    text: Optional[str] = "" # 输入的内容
    key: Optional[str] = ""  # 特殊按键 (Enter, Tab 等)

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
async def execute_action(req: ActionRequest):
    """
    接收指令并执行具体操作系统操作的职责
    """
    try:
        x, y = req.coords
        print(f"执行业务: {req.action} | 坐标: {req.coords} | 内容: {req.text or req.key}")

        # --- 分发动作职责 ---
        if req.action == "screenshot":
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

if __name__ == "__main__":
    # 在 8000 端口启动服务
    print("GUI 执行器已启动，等待 Agent 指令...")
    uvicorn.run(app, host="0.0.0.0", port=8000)