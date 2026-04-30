# gui_agent.py
import base64
import time
import requests
import json
from gui_vl import glm_4_6v_flash
from ocr_service import QwenDetector
from ocr_openrouter import OpenRouterDetector
from gui_parser import parse_intent
from gui_redis import redis_manager

gui_client_url = "http://192.168.2.16:8000/execute"
qwen_detector = QwenDetector()
# qwen_detector = QwenDetector()

# 从模型响应中提取并解析JSON
def parse_json_response(response_text):
    """辅助函数：从模型响应中提取并解析JSON，处理常见的转义问题"""
    if "```json" in response_text:
        json_str = response_text.split("```json")[1].split("```")[0].strip()
    elif "```" in response_text:
        json_str = response_text.split("```")[1].split("```")[0].strip()
    else:
        json_str = response_text.strip()
    
    # 尝试解析逻辑
    try:
        return json.loads(json_str)
    except:
        # 如果解析失败，尝试简单的正则提取（保留原有的健壮性）
        import re
        match = re.search(r'\{.*\}', json_str, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise

def build_react_prompt(total_intent, history, current_ui_description=""):
    history_str = ""
    if history:
        history_str = json.dumps(history[-3:], ensure_ascii=False, indent=2)
    else:
        history_str = "无"

    prompt = f"""
你是一个能够操作电脑 GUI 的智能助手。你需要通过观察屏幕截图，思考当前状态，并决定下一步动作。

【总目标】: {total_intent}

【历史轨迹 (最近3步)】:
{history_str}

【当前 UI 描述】:
{current_ui_description}

【执行职责】：
1. 结合当前截图与总目标，分析现状（例如：“我看到了登录按钮，但我需要先输入账号”），并解释为什么要执行下一步。
2. 决定下一步的具体动作。

【动作类型 (action)】:
- `click` - 单击（一般用于获得焦点、单击网页链接、单击普通按钮等）
- `double_click` - 双击（【重要】在桌面上打开应用、运行程序、打开文件夹/磁盘等，必须使用双击！）
- `type` - 输入文字（此时必须在 text 字段提供要输入的文字）
- `scroll` - 滚动页面（此时必须在 text 字段提供 "down" 或 "up"）
- `key_press` - 按下单个按键（此时必须在 key 字段提供按键名，如 "enter", "esc", "backspace"）
- `hotkey` - 组合快捷键（此时必须在 text 字段提供组合键，如 "ctrl+c", "alt+f4"）
- `window_control` - 窗口控制（此时必须在 text 字段提供 "maximize", "minimize" 或 "close"）
- `finish` - 任务完成（当总目标已经实现时使用）

【输出格式要求】：
请严格按以下格式输出，不要包含其他多余内容：

Thought: <你的分析和思考过程>
Action: <具体的 API 调用 JSON>

Action JSON 格式示例：
{{
    "target": "目标名称（如'此电脑'、'提交按钮'，如果没有具体目标则留空）",
    "action": "动作类型（如 click, type, finish 等）",
    "text": "输入文字、滚动方向或组合键（根据 action 类型填写，否则留空）",
    "key": "单键名称（仅当 action 为 key_press 时填写，否则留空）",
    "norm_x": 整数（0-1000，如果能从截图中直接确定目标中心点坐标则填写，否则填 -1）,
    "norm_y": 整数（0-1000，如果能从截图中直接确定目标中心点坐标则填写，否则填 -1）
}}
"""
    return prompt

def parse_thought_and_action(response_text):
    thought = ""
    action_json = {}
    
    import re
    thought_match = re.search(r'Thought:\s*(.*?)(?=Action:|$)', response_text, re.DOTALL)
    if thought_match:
        thought = thought_match.group(1).strip()
        
    action_match = re.search(r'Action:\s*(\{.*\}|```json\s*\{.*\}\s*```|```\s*\{.*\}\s*```)', response_text, re.DOTALL)
    if action_match:
        action_str = action_match.group(1).strip()
        action_json = parse_json_response(action_str)
    else:
        try:
            action_json = parse_json_response(response_text)
        except:
            pass
            
    return thought, action_json

# 验证结果
def verify_task_success(screenshot_base64, user_intent):
    """
    使用视觉模型判断用户意图是否已经实现
    """
    prompt = f"""
请结合本截图，评价用户意图是否已经实现。

## 用户意图
{user_intent}

请仔细观察截图中的界面状态、打开的窗口、提示信息等，判断该意图是否已经成功完成。

如果已经实现，请严格输出 JSON 格式：
{{
    "is_success": true,
    "reason": "判断成功的理由"
}}

如果未实现，请严格输出 JSON 格式：
{{
    "is_success": false,
    "reason": "判断失败的理由"
}}
"""
    response_text = glm_4_6v_flash(prompt, screenshot_base64)
    print(f"[DEBUG] 验证原始响应: {response_text}")
    return parse_json_response(response_text)

import os
from dotenv import load_dotenv

load_dotenv()

def run_react_loop(total_intent: str, max_attempts: int, gui_client_url: str, show_img: bool, session_id: str):
    print(f"\n>>> 开始执行 ReAct 循环任务: {total_intent}")
    
    redis_manager.set_task_status(session_id, "running")
    
    task_completed = False
    loop_count = 0
    max_loops = max_attempts * 2 # 允许更多的循环次数以支持自愈
    
    final_result = {"status": "failed", "reason": "达到最大循环次数"}
    
    while not task_completed and loop_count < max_loops:
        loop_count += 1
        print(f"\n--- ReAct 循环 第 {loop_count}/{max_loops} 次 ---")
        
        # 1. 观察 (Observation) - 获取截图
        try:
            initial_res = requests.post(gui_client_url, json={
                "action": "screenshot",
                "coords": [0, 0],
                "session_id": session_id
            })
            if initial_res.status_code == 429:
                print("服务端返回 429: 当前有其他任务正在执行")
                return {"status": "failed", "reason": "当前有其他任务正在执行，请稍后再试"}
            initial_res = initial_res.json()
        except Exception as e:
            print(f"请求截图失败: {e}")
            return {"status": "failed", "reason": f"请求截图失败: {e}"}
            
        current_screenshot = initial_res.get("screenshot")
        if not current_screenshot:
            print(f"获取截图失败，服务端返回: {initial_res}")
            return {"status": "failed", "reason": f"获取截图失败: {initial_res.get('detail', '未知错误')}"}
            
        # 获取历史记录
        history = redis_manager.get_history(session_id)
        
        # 2. 思考与动作 (Thought & Action)
        prompt = build_react_prompt(total_intent, history)
        try:
            response_text = glm_4_6v_flash(prompt, current_screenshot)
            print(f"[DEBUG] ReAct 原始响应:\n{response_text}")
            thought, action = parse_thought_and_action(response_text)
            print(f"Thought: {thought}")
            print(f"Action: {action}")
        except Exception as e:
            print(f"解析 VLM 响应失败: {e}")
            redis_manager.add_history(session_id, "解析 VLM 响应失败", {}, f"Failed: {e}")
            continue
            
        if not action:
            print("未能解析出有效的 Action")
            redis_manager.add_history(session_id, thought, {}, "Failed: 未能解析出有效的 Action")
            continue
            
        action_type = action.get("action")
        if action_type == "finish":
            print("Agent 判断任务已完成！")
            task_completed = True
            final_result = {"status": "success", "reason": "任务完成", "attempts": loop_count}
            if show_img:
                final_result["img"] = current_screenshot
            redis_manager.set_task_status(session_id, "success")
            redis_manager.add_history(session_id, thought, action, "Success: 任务完成")
            break
            
        target_name = action.get("target")
        coords = None
        
        # 3. 执行与记录
        if target_name:
            # 优先查 Redis 缓存
            cached_coords = redis_manager.get_element_coords(session_id, target_name)
            if cached_coords:
                print(f"命中 Redis 缓存坐标: {target_name} -> {cached_coords}")
                coords = cached_coords
            else:
                # 尝试 OCR 定位
                print(f"正在使用 QwenDetector 定位目标: {target_name} ...")
                coords_result = qwen_detector.get_target_coords(current_screenshot, target_name)
                if coords_result:
                    coords = [coords_result["x"], coords_result["y"]]
                    redis_manager.set_element_coords(session_id, target_name, coords)
                    print(f"OCR 定位成功，物理坐标: {coords}，已存入 Redis 缓存")
                else:
                    # 尝试 VLM 坐标
                    norm_x = action.get("norm_x", -1)
                    norm_y = action.get("norm_y", -1)
                    if norm_x != -1 and norm_y != -1:
                        import base64
                        from io import BytesIO
                        from PIL import Image
                        img_data = base64.b64decode(current_screenshot.replace('data:image/png;base64,', ''))
                        with Image.open(BytesIO(img_data)) as img:
                            width, height = img.size
                        real_x = int(round((norm_x / 1000.0) * width))
                        real_y = int(round((norm_y / 1000.0) * height))
                        coords = [real_x, real_y]
                        print(f"VLM 坐标换算成功: 物理坐标 {coords}")
                        
        if not coords and action_type in ["click", "double_click"]:
            print(f"定位目标 {target_name} 失败，无法执行点击动作。")
            redis_manager.add_history(session_id, thought, action, "Failed: 目标定位失败")
            continue
            
        req_data = {
            "action": action_type,
            "coords": coords or [0, 0],
            "text": action.get("text", ""),
            "key": action.get("key", ""),
            "session_id": session_id
        }
        
        try:
            response = requests.post(gui_client_url, json=req_data).json()
            print(f"动作执行完成: {action_type} on {target_name or 'None'}")
        except Exception as e:
            print(f"执行动作失败: {e}")
            redis_manager.add_history(session_id, thought, action, f"Failed: 执行动作异常 {e}")
            continue
            
        # 等待界面响应
        time.sleep(2)
        
        # 4. 核验 (Observation 更新)
        print("正在验证动作是否成功...")
        try:
            verify_res = requests.post(gui_client_url, json={
                "action": "screenshot",
                "coords": [0, 0],
                "session_id": session_id
            }).json()
            verify_screenshot = verify_res.get("screenshot")
            
            verify_prompt = f"""
我刚刚执行了动作：{action_type} 目标：{target_name}。
请观察当前截图，判断该动作是否成功执行并产生了预期效果？

如果成功，请严格输出 JSON 格式：
{{
    "is_success": true,
    "reason": "判断成功的理由"
}}

如果失败，请严格输出 JSON 格式：
{{
    "is_success": false,
    "reason": "判断失败的理由"
}}
"""
            verification_text = glm_4_6v_flash(verify_prompt, verify_screenshot)
            print(f"[DEBUG] 验证原始响应: {verification_text}")
            verification = parse_json_response(verification_text)
            
            is_success = verification.get("is_success", False)
            reason = verification.get("reason", "未知原因")
        except Exception as e:
            print(f"验证过程异常: {e}")
            is_success = False
            reason = f"验证异常: {e}"
            
        print(f"验证结果: {'成功' if is_success else '失败'} - {reason}")
        
        # 5. 更新上下文
        observation = "Success" if is_success else f"Failed: {reason}"
        redis_manager.add_history(session_id, thought, action, observation)
        
    if not task_completed:
        redis_manager.set_task_status(session_id, "failed")
        
    return final_result

import uuid

def run_agent_task(intent:str, max_attempts:int=5, gui_client_url:str="http://192.168.2.16:8000/execute", show_img:bool=False, history:list=None):
    print(f"========== 开始执行总任务: {intent} ==========")
    
    # 生成本次任务的唯一 Session ID
    session_id = str(uuid.uuid4())
    print(f"分配任务 Session ID: {session_id}")
    
    try:
        # --- 新增：在语义切分前，先尝试获取锁（通过请求一次截图） ---
        print("正在检查服务端是否空闲...")
        try:
            check_res = requests.post(gui_client_url, json={
                "action": "screenshot",
                "coords": [0, 0],
                "session_id": session_id
            }, timeout=5)
            if check_res.status_code == 429:
                print("服务端返回 429: 当前有其他任务正在执行，放弃本次任务")
                return {"status": "failed", "reason": "当前有其他任务正在执行，请稍后再试"}
        except Exception as e:
            print(f"检查服务端状态失败: {e}")
            return {"status": "failed", "reason": f"无法连接到执行器服务端: {e}"}

        # 直接使用 ReAct 循环处理总任务
        result = run_react_loop(intent, max_attempts, gui_client_url, show_img, session_id)
        
        print("\n========== 总任务执行完毕 ==========")
        return result
        
    finally:
        # 无论任务成功、失败还是异常，都主动释放服务端的锁
        print(f"正在释放任务 Session 锁: {session_id}")
        try:
            requests.post(gui_client_url, json={
                "action": "release_lock",
                "coords": [0, 0],
                "session_id": session_id
            }, timeout=3)
        except Exception as e:
            print(f"释放锁失败 (可能服务端已关闭): {e}")

if __name__ == "__main__":
    # 保持你的 API Key 不变
    intent = input("请输出你的指令：")
    gui_client_url = input("请输入目标接口 (默认 http://192.168.68.15:8000/execute): ") or "http://192.168.68.15:8000/execute"
    response = run_agent_task(intent=rf'{intent}', gui_client_url=gui_client_url)
    print(json.dumps(response,ensure_ascii=False,indent=4))
