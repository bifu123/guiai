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
from gui_skills import skill_manager

import os
from dotenv import load_dotenv

load_dotenv()

gui_client_url = os.getenv("GUI_CLIENT_URL")
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
            extracted_str = match.group()
            try:
                return json.loads(extracted_str)
            except:
                # 尝试处理单引号的情况
                try:
                    import ast
                    return ast.literal_eval(extracted_str)
                except:
                    pass
        raise

def build_react_prompt(total_intent, history, agent_history, current_ui_description="", skill_context=""):
    agent_history_str = ""
    if agent_history:
        agent_history_str = json.dumps(agent_history[-3:], ensure_ascii=False, indent=4)
    else:
        agent_history_str = "无"

    chat_history_section = ""
    if history is not None:
        if isinstance(history, (dict, list)):
            chat_history_str = json.dumps(history, ensure_ascii=False, indent=4)
        elif isinstance(history, str):
            chat_history_str = history
        else:
            chat_history_str = str(history)
            
        chat_history_section = f"\n【对话历史上下文】:\n{chat_history_str}\n"

    skill_section = ""
    if skill_context:
        skill_section = f"\n【专属技能指导】:\n{skill_context}\n"

    prompt = f"""
你是一个能够操作电脑 GUI 的智能助手。你需要通过观察屏幕截图，思考当前状态，并决定下一步动作。

【总目标】: {total_intent}
{skill_section}{chat_history_section}
【Agent 历史轨迹 (最近3步)】:
{agent_history_str}

【当前 UI 描述】:
{current_ui_description}

【执行职责】：
1. 结合当前截图、总目标以及【Agent 历史轨迹】，分析现状。判断当前是否已经完成了总目标，如果未完成，解释为什么要执行下一步。
2. 决定下一步的具体动作。
3. 【重要回退机制】：当发现目标难以定位（如历史记录中提示“未找到目标”），或者点击操作验证失败时，优先考虑使用 `hotkey` 快捷键来达成目的（例如使用 `win+d` 回到桌面，`alt+f4` 关闭窗口，`win+e` 打开资源管理器等）。
4. 【纯观察任务】：如果总目标仅仅是“观察”、“查看”、“描述”屏幕内容，而不需要进行任何实际的点击或输入操作，请在 Thought 中详细描述你看到的内容，并在 Action 中直接输出 `{{"action": "finish"}}`。
5. 【滚动策略】：如果判断目标在当前屏幕之外需要滚动，请注意：
   - 距离控制：请根据画面情况自行决定 scroll_dist 的大小。如果目标可能就在附近，请使用较小的值避免错过；如果需要大范围寻找，使用较大的值；明确找底/顶时使用 10000。
   - 坐标控制：滚动坐标 (norm_x, norm_y) 必须指向目标滚动区域的内部（如全屏滚动直接用 500, 500），绝对不要指向滚动条本身。
6. 【任务完成判断】：在决定下一步动作前，必须严格检查【Agent 历史轨迹】。如果发现总目标已经达成（例如：已经滚动了要求的总距离、已经点击了目标按钮、已经获取了需要的信息等），请在 Thought 中说明任务已完成，并在 Action 中直接输出 `{{"action": "finish"}}`，绝对不要陷入无限重复的死循环！

【动作类型 (action)】:
- `click` - 单击（一般用于获得焦点、单击网页链接、单击普通按钮等）
- `double_click` - 双击（【重要】在桌面上打开应用、运行程序、打开文件夹/磁盘等，必须使用双击！）
- `type` - 追加输入文字（在当前光标位置追加输入。必须在 text 字段提供要输入的文字）
- `clear_and_type` - 清空并输入文字（【推荐】用于地址栏、搜索框等需要覆盖原有内容的场景。会自动全选清空再输入。必须在 text 字段提供要输入的文字）
- `scroll` - 滚动页面（【注意】执行滚动时，必须将坐标指向需要滚动的区域内部。如果是全屏滚动，直接填 norm_x: 500, norm_y: 500。千万不要指向边缘的细长滚动条！支持上下左右，可指定距离，详见下方 JSON 示例）
- `key_press` - 按下单个按键（如 "enter" 回车确认, "backspace" 退格删除, "delete" 删除, "esc" 等，必须在 key 字段提供按键名）
- `hotkey` - 组合快捷键（此时必须在 text 字段提供组合键，如 "ctrl+a" 全选, "ctrl+c" 复制, "ctrl+v" 粘贴）
- `window_control` - 窗口控制（此时必须在 text 字段提供 "maximize", "minimize" 或 "close"）
- `wait_for_human` - 等待人工介入（当遇到需要人类完成的操作，如扫码登录、刷脸、输入复杂验证码时使用。必须在 text 字段说明需要人类做什么）
- `finish` - 任务完成（当总目标已经实现时使用）

【输出格式要求】：
请严格按以下格式输出，不要包含其他多余内容：

Thought: <你的分析和思考过程>
Action: <具体的 API 调用 JSON>

Action JSON 格式示例：
{{
    "target": "目标名称（【极其重要】必须是屏幕上确切显示的文字，或标准的系统控件名称。绝对不要自己脑补加上'图标'、'按钮'、'输入框'等后缀！例如：应输出'此电脑'而不是'此电脑图标'，应输出'文件资源管理器'而不是'文件资源管理器图标'。如果没有具体目标则留空）",
    "action": "动作类型（如 click, type, finish 等）",
    "text": "输入文字或组合键（根据 action 类型填写，否则留空）",
    "key": "单键名称（仅当 action 为 key_press 时填写，否则留空）",
    "scroll_dir": "滚动方向（仅当 action 为 scroll 时填写，可选: down, up, left, right。默认 down）",
    "scroll_dist": 整数（仅当 action 为 scroll 时填写，表示滚动的相对距离/像素。请根据你需要滚动的幅度自行决定数值，例如微调填较小值，大范围翻页填较大值，直接到底/顶填 10000。默认 500）,
    "norm_x": 整数（0-1000，如果能从截图中直接确定目标中心点坐标则填写，否则填 -1）,
    "norm_y": 整数（0-1000，如果能从截图中直接确定目标中心点坐标则填写，否则填 -1）
}}

【重要提醒】
如果需要在浏览器地址栏中输入网址，请省略`http://`和`https://`
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

def run_react_loop(initial_intent: str, history: list, max_attempts: int, gui_client_url: str, show_img: bool, session_id: str):
    print(f"\n>>> 开始执行 ReAct 循环任务: {initial_intent}")
    
    # 初始化当前意图
    redis_manager.set_task_intent(session_id, initial_intent)
    
    # 1. 技能路由：根据总目标选择合适的技能
    print("正在分析任务意图，匹配专属技能...")
    skill_context = skill_manager.select_skill(initial_intent)
    if skill_context:
        print("已加载专属技能指导。")
    else:
        print("未匹配到特定技能，使用通用模式。")
        
    redis_manager.set_task_status(session_id, "running")
    
    task_completed = False
    loop_count = 0
    max_loops = max_attempts * 2 # 允许更多的循环次数以支持自愈
    
    final_result = {"status": "failed", "reason": "达到最大循环次数"}
    
    while not task_completed and loop_count < max_loops:
        # 检查是否被外部（如 /end 指令或新指令）强制终止或打断
        current_status = redis_manager.get_task_status(session_id)
        if current_status == "failed":
            print(f"检测到任务状态已被外部终止，退出循环。")
            final_result = {"status": "failed", "reason": "任务已被强制终止"}
            break
        elif current_status == "interrupted":
            print(f"检测到新指令打断，当前循环交出控制权并退出。")
            final_result = {"status": "interrupted", "reason": "被新指令打断"}
            break
            
        loop_count += 1
        print(f"\n--- ReAct 循环 第 {loop_count}/{max_loops} 次 ---")
        
        # 动态读取最新意图
        current_intent = redis_manager.get_task_intent(session_id) or initial_intent
        print(f"当前执行意图: {current_intent}")
        
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
        agent_history = redis_manager.get_history(session_id)
        
        # 2. 思考与动作 (Thought & Action)
        prompt = build_react_prompt(current_intent, history, agent_history, skill_context=skill_context)
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
            # 如果有 thought 但没有 action，且是观察类任务，或者已经重试多次，强制结束
            if thought and ("查看" in current_intent or "观察" in current_intent or "描述" in current_intent or loop_count >= 3):
                print("检测到纯观察任务或多次解析 Action 失败，强制结束任务。")
                action = {"action": "finish"}
            else:
                redis_manager.add_history(session_id, thought, {}, "Failed: 未能解析出有效的 Action")
                continue
            
        action_type = action.get("action")
        if action_type == "finish":
            print("Agent 判断任务已完成！")
            task_completed = True
            final_result = {"status": "success", "reason": "任务完成", "attempts": loop_count, "thought": thought}
            if show_img:
                # 确保在 finish 时获取最新的截图
                try:
                    final_res = requests.post(gui_client_url, json={
                        "action": "screenshot",
                        "coords": [0, 0],
                        "session_id": session_id
                    }).json()
                    final_result["img"] = final_res.get("screenshot", current_screenshot)
                except Exception as e:
                    print(f"获取最终截图失败: {e}")
                    final_result["img"] = current_screenshot
            redis_manager.set_task_status(session_id, "success")
            redis_manager.add_history(session_id, thought, action, "Success: 任务完成")
            break
            
        if action_type == "wait_for_human":
            human_task = action.get("text", "请完成必要的操作")
            print(f"\n==================================================")
            print(f"🤖 Agent 请求人工介入: {human_task}")
            print(f"==================================================")
            
            # 记录历史，说明正在等待人类介入
            redis_manager.add_history(session_id, thought, action, "Waiting: 等待人类完成操作")
            redis_manager.set_task_status(session_id, "waiting_for_human")
            
            # 中断循环，返回状态给调用方
            final_result = {
                "status": "waiting_for_human", 
                "reason": human_task, 
                "session_id": session_id,
                "attempts": loop_count
            }
            if show_img:
                final_result["img"] = current_screenshot
            return final_result
            
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
                # 尝试 UIA 定位
                print(f"正在使用 UIAutomation 查找目标: {target_name} ...")
                try:
                    uia_res = requests.post(gui_client_url, json={
                        "action": "find_element",
                        "coords": [0, 0],
                        "text": target_name,
                        "session_id": session_id
                    }, timeout=5).json()
                    if uia_res.get("status") == "success" and uia_res.get("coords"):
                        coords = uia_res.get("coords")
                        redis_manager.set_element_coords(session_id, target_name, coords)
                        print(f"UIA 定位成功，物理坐标: {coords}，已存入 Redis 缓存")
                except Exception as e:
                    print(f"UIA 定位请求异常: {e}")
                
                if not coords:
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
            if action_type == "clear_and_type":
                print(f"执行 clear_and_type: 先点击并全选，然后输入 '{action.get('text', '')}'")
                # 1. 点击获取焦点
                requests.post(gui_client_url, json={"action": "click", "coords": coords or [0, 0], "session_id": session_id})
                time.sleep(0.5)
                # 2. 全选 (ctrl+a)
                requests.post(gui_client_url, json={"action": "hotkey", "coords": coords or [0, 0], "text": "ctrl+a", "session_id": session_id})
                time.sleep(0.5)
                # 3. 退格删除 (backspace) 确保清空
                requests.post(gui_client_url, json={"action": "key_press", "coords": coords or [0, 0], "key": "backspace", "session_id": session_id})
                time.sleep(0.5)
                # 4. 输入新内容
                req_data["action"] = "type"
                response = requests.post(gui_client_url, json=req_data).json()
            else:
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

def run_agent_task(user_id: str, intent: str, history: list, max_attempts: int=5, gui_client_url: str=os.getenv("GUI_CLIENT_URL"), show_img: bool=False):
    print(f"========== 开始执行总任务: {intent} ==========")
    
    session_id = str(user_id)
    print(f"任务 Session ID (User ID): {session_id}")
    
    # 处理强制结束指令
    if intent.strip() == "/end":
        print(f"收到强制结束指令，正在清理用户 {session_id} 的所有任务状态...")
        redis_manager.set_task_status(session_id, "failed")
        try:
            # 清理所有相关的 Redis 键
            redis_manager.redis_client.delete(f"task:{session_id}:history")
            redis_manager.redis_client.delete(f"task:{session_id}:current_intent")
            redis_manager.redis_client.delete(f"task:{session_id}:summary")
            redis_manager.redis_client.delete(f"task:{session_id}:elements")
            
            # 释放全局占用锁
            redis_manager.clear_global_active_user(session_id)
            
            # 释放执行器锁
            requests.post(gui_client_url, json={
                "action": "release_lock",
                "coords": [0, 0],
                "session_id": session_id
            }, timeout=3)
        except Exception as e:
            print(f"清理任务状态时发生异常: {e}")
        return {"status": "success", "reason": "已强制结束当前任务并清理所有状态"}

    # --- 全局保护性拒绝机制 ---
    active_user = redis_manager.get_global_active_user()
    if active_user and active_user != session_id:
        # 检查占用者是否真的在运行任务
        active_user_status = redis_manager.get_task_status(active_user)
        if active_user_status in ["running", "waiting_for_human"]:
            print(f"全局保护触发: 用户 {session_id} 的请求被拒绝，因为 {active_user} 正在占用 Agent (状态: {active_user_status})")
            return {"status": "failed", "reason": f"Agent 正在为其他用户执行任务，请稍后再试"}
        else:
            # 如果占用者的状态不是 running/waiting，说明可能是残留的锁，强制清除
            print(f"发现残留的全局锁 (用户 {active_user} 状态为 {active_user_status})，强制清除。")
            redis_manager.redis_client.delete("global:active_user")

    # 检查状态 (保护性拒绝或动态更新)
    status = redis_manager.get_task_status(session_id)
    if status == "running":
        print(f"用户 {session_id} 有任务正在执行中，准备打断并接管...")
        # 1. 获取旧意图并融合
        old_intent = redis_manager.get_task_intent(session_id) or ""
        merged_intent = f"最初目标：{old_intent}\n用户最新补充/修改：{intent}"
        print(f"融合后的新意图:\n{merged_intent}")
        
        # 2. 更新意图并标记打断状态
        redis_manager.set_task_intent(session_id, merged_intent)
        redis_manager.set_task_status(session_id, "interrupted")
        redis_manager.add_history(session_id, "系统通知", {"action": "update_intent"}, f"用户下达了新指令，重新评估规划: {intent}")
        
        # 3. 等待旧循环退出 (最多等待 15 秒)
        wait_time = 0
        while wait_time < 15:
            # 如果旧循环已经退出，它可能还没来得及改状态，但我们自己接管后会重新设为 running
            # 这里我们主要靠时间延迟让旧循环有机会检测到 interrupted 并 break
            time.sleep(1)
            wait_time += 1
            print(f"等待旧任务退出... ({wait_time}s)")
            # 简单起见，等待 3 秒通常足够旧循环在下一次检查时退出
            if wait_time >= 3:
                break
                
        print("接管控制权，启动新的 ReAct 循环...")
        # 重新设置为 running，开始新的循环
        redis_manager.set_task_status(session_id, "running")
        # 注意：这里直接调用 run_react_loop，它会继续使用之前的 history
        result = run_react_loop(merged_intent, history, max_attempts, gui_client_url, show_img, session_id)
        return result
        
    elif status == "waiting_for_human":
        print("人类已完成操作，继续执行任务...")
        # 可以在这里追加一条历史记录，告诉模型人类已经完成了操作
        redis_manager.add_history(session_id, "人类介入", {"action": "human_action"}, "Success: 人类已完成操作")
    elif status in ["success", "failed"]:
        print(f"任务已结束 (状态: {status})，将作为新任务重新开始。")
        # 清理旧的历史记录，准备开始新任务
        try:
            redis_manager.redis_client.delete(f"task:{session_id}:history")
        except:
            pass
    
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

        # 获取全局占用锁
        redis_manager.set_global_active_user(session_id)

        # 直接使用 ReAct 循环处理总任务
        result = run_react_loop(intent, history, max_attempts, gui_client_url, show_img, session_id)
        
        print("\n========== 总任务执行完毕 ==========")
        return result
        
    finally:
        # 只有当任务真正结束（成功或失败）时，才释放锁。如果是等待人类，则保留锁（或根据业务需求决定是否释放）
        # 为了防止死锁，这里我们依然释放服务端的执行锁，因为等待人类期间不需要占用执行器
        print(f"正在释放任务 Session 锁: {session_id}")
        try:
            requests.post(gui_client_url, json={
                "action": "release_lock",
                "coords": [0, 0],
                "session_id": session_id
            }, timeout=3)
        except Exception as e:
            print(f"释放锁失败 (可能服务端已关闭): {e}")
            
        # 释放全局占用锁 (如果任务是 waiting_for_human，则不释放，保持占用)
        current_status = redis_manager.get_task_status(session_id)
        if current_status != "waiting_for_human":
            redis_manager.clear_global_active_user(session_id)

if __name__ == "__main__":
    # 保持你的 API Key 不变
    user_id = input("请输入测试用户ID (默认 test_user_001): ") or "test_user_001"
    intent = input("请输出你的指令：")
    gui_client_url = input("请输入目标接口 (默认 http://192.168.68.15:8000/execute): ") or os.getenv("GUI_CLIENT_URL")
    
    mock_history = []
    
    response = run_agent_task(user_id=user_id, intent=intent, history=mock_history, gui_client_url=gui_client_url)
    print(json.dumps(response,ensure_ascii=False,indent=4))
