# gui_agent.py
import base64
import time
import requests
import json
from gui_vl import glm_4_6v_flash
from ocr_service import QwenDetector
from ocr_openrouter import OpenRouterDetector
from gui_parser import parse_intent

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

# 请求操作指导
def ask_vlm_for_action(screenshot_base64, user_intent):
    """
    请求操作指导，负责判断意图类型并提取目标名称和动作
    """
    prompt = f"""
用户意图：{user_intent}

【执行职责】：
1. 判断用户意图的类型：
   - 如果用户想查看屏幕内容、询问当前状态、要求描述画面等（没有明确要操作某个图标/按钮），则 action_type 为 "query"
   - 如果用户想打开程序、点击按钮、输入文字、滚动页面、使用快捷键等（有明确的操作目标或动作），则 action_type 为 "operate"

2. 如果 action_type 为 "operate"，请进一步：
   - 提取出需要操作的目标名称（如"此电脑"、"回收站"、"浏览器"等，如果没有具体目标则留空）
   - 确定需要执行的动作（action）：
     - `click` - 单击（一般用于获得焦点、单击网页链接、单击普通按钮等）
     - `double_click` - 双击（【重要】在桌面上打开应用、运行程序、打开文件夹/磁盘等，必须使用双击！）
     - `type` - 输入文字（此时必须在 text 字段提供要输入的文字）
     - `scroll` - 滚动页面（此时必须在 text 字段提供 "down" 或 "up"）
     - `key_press` - 按下单个按键（此时必须在 key 字段提供按键名，如 "enter", "esc", "backspace"）
     - `hotkey` - 组合快捷键（此时必须在 text 字段提供组合键，如 "ctrl+c", "alt+f4"）
     - `window_control` - 窗口控制（此时必须在 text 字段提供 "maximize", "minimize" 或 "close"）
   - 观察截图，找到目标在画面中的位置，并输出其中心点的归一化坐标（0-1000）：
     - norm_x: 0-1000 的整数（如果找不到目标或不需要坐标，请输出 -1）
     - norm_y: 0-1000 的整数（如果找不到目标或不需要坐标，请输出 -1）

请以 JSON 格式返回：
{{
    "action_type": "operate 或 query",
    "target": "目标名称（operate 时尽量填写，没有则留空，query 时留空）",
    "action": "动作类型（operate 时必填，query 时留空）",
    "text": "输入文字、滚动方向或组合键（根据 action 类型填写，否则留空）",
    "key": "单键名称（仅当 action 为 key_press 时填写，否则留空）",
    "norm_x": 整数（0-1000，operate 时必填，不需要坐标填 -1）,
    "norm_y": 整数（0-1000，operate 时必填，不需要坐标填 -1）,
    "reason": "判断理由"
}}
"""
    
    response_text = glm_4_6v_flash(prompt, screenshot_base64)
    print(f"[DEBUG] 决策原始响应: {response_text}")
    return parse_json_response(response_text)

# 描述屏幕内容（用于 query 类型意图）
def describe_screen(screenshot_base64, user_intent):
    """
    使用视觉模型描述当前屏幕内容
    """
    prompt = f"""
用户想知道：{user_intent}

请仔细观察当前屏幕截图，用中文详细描述：
1. 当前屏幕上能看到什么内容？
2. 有哪些窗口或程序是打开的？
3. 桌面上有哪些图标？
4. 根据用户的问题，给出有针对性的回答。

请用自然语言描述，不要输出 JSON。
"""
    response_text = glm_4_6v_flash(prompt, screenshot_base64)
    print(f"[DEBUG] 描述屏幕原始响应: {response_text}")
    return response_text

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

def _execute_single_task(task_intent: str, max_attempts: int, gui_client_url: str, show_img: bool, use_ocr: bool = True, session_id: str = ""):
    """执行单个子任务（降级到 VLM 逻辑）"""
    print(f"\n>>> 开始执行子任务: {task_intent}")
    reason = "操作失败"
    
    # 优先使用传入的 max_attempts，如果未传入或为默认值，则尝试从环境变量读取
    env_retry = os.getenv("DO_RETRY")
    if env_retry and max_attempts == 5: # 5 是默认值
        try:
            max_attempts = int(env_retry)
        except ValueError:
            pass
            
    for attempt in range(max_attempts):
        print(f"--- 第 {attempt + 1}/{max_attempts} 次尝试 ---")
        
        # --- 1. 初始截图 ---
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
        
        # --- 2. 决策：理解意图并提取目标 ---
        try:
            decision = ask_vlm_for_action(current_screenshot, task_intent)
            print(f"Agent 决策理由: {decision.get('reason')}")
        except Exception as e:
            print(f"解析 VLM 决策响应失败: {e}")
            reason = f"解析 VLM 决策响应失败: {e}"
            continue
        
        action_type = decision.get("action_type", "operate")
        
        # --- 如果是 query 类型（查询/描述屏幕），直接返回描述结果 ---
        if action_type == "query":
            print("检测到查询型意图，正在描述屏幕内容...")
            description = describe_screen(current_screenshot, task_intent)
            result = {
                "status": "success",
                "action_type": "query",
                "description": description,
                "reason": decision.get("reason", "用户想查看屏幕内容"),
                "coords": [0, 0],
                "attempts": 1
            }
            if show_img:
                result["img"] = current_screenshot
            return result
        
        # --- 如果是 operate 类型（操作型意图），走原有流程 ---
        target_name = decision.get("target")
        action = decision.get("action", "click")
        
        if not target_name:
            print("未能从意图中提取到目标名称。")
            return {"status": "failed", "reason": "No target found"}

        # --- 3. 定位 ---
        coords_result = None
        if use_ocr:
            print(f"正在使用 QwenDetector 定位目标: {target_name} ...")
            coords_result = qwen_detector.get_target_coords(current_screenshot, target_name)
            
        if not coords_result:
            if use_ocr:
                print(f"OCR 定位失败，尝试使用 VLM 估算的坐标...")
            else:
                print(f"跳过 OCR，直接使用 VLM 估算的坐标...")
                
            norm_x = decision.get("norm_x", -1)
            norm_y = decision.get("norm_y", -1)
            
            if norm_x != -1 and norm_y != -1:
                import base64
                from io import BytesIO
                from PIL import Image
                img_data = base64.b64decode(current_screenshot.replace('data:image/png;base64,', ''))
                with Image.open(BytesIO(img_data)) as img:
                    width, height = img.size
                real_x = int(round((norm_x / 1000.0) * width))
                real_y = int(round((norm_y / 1000.0) * height))
                coords_result = {"x": real_x, "y": real_y}
                print(f"VLM 坐标换算成功: 物理坐标 [{real_x}, {real_y}]")
            else:
                print(f"VLM 未提供有效坐标。")
                
        if not coords_result:
            print(f"定位目标 {target_name} 失败。")
            return {"status": "failed", "reason": "Target localization failed"}
            
        coords = [coords_result["x"], coords_result["y"]]
        print(f"最终定位成功，物理坐标: {coords}")
        
        # --- 4. 执行动作 ---
        req_data = {
            "action": action,
            "coords": coords,
            "text": decision.get("text", ""),
            "key": decision.get("key", ""),
            "session_id": session_id
        }
        
        response = requests.post(gui_client_url, json=req_data).json()
        print(f"动作执行完成，坐标: {req_data['coords']}")
        
        # 等待界面响应
        time.sleep(2)
        
        # --- 5. 验证结果 ---
        print("正在验证任务是否成功...")
        verify_res = requests.post(gui_client_url, json={
            "action": "screenshot",
            "coords": [0, 0],
            "session_id": session_id
        }).json()
        verify_screenshot = verify_res.get("screenshot")
        
        try:
            verification = verify_task_success(verify_screenshot, task_intent)
            is_success = verification.get("is_success", False)
            reason = verification.get("reason", "未知原因")
        except Exception as e:
            print(f"解析 VLM 验证响应失败: {e}")
            reason = f"解析 VLM 验证响应失败: {e}"
            continue
            
        print(f"验证结果: {'成功' if is_success else '失败'} - {reason}")
        
        if is_success:
            result = {
                "status": "success", 
                "reason": reason,
                "coords": req_data['coords'], 
                "attempts": attempt + 1
            }
            if show_img:
                result["img"] = verify_screenshot
            return result
            
    res_dict = {
        "status": "failed", 
        "reason": reason
    }
    if show_img and 'current_screenshot' in locals():
        res_dict["img"] = current_screenshot
    return res_dict

def _map_predicate_to_action(predicate: str) -> str:
    """将自然语言谓词映射为系统支持的动作"""
    predicate = predicate.lower()
    if "双击" in predicate or "打开" in predicate:
        return "double_click"
    elif "输入" in predicate:
        return "type"
    elif "按" in predicate:
        return "click" # 键盘按键通常也需要先点击聚焦，或者后续扩展专门的 key 动作
    else:
        return "click" # 默认单击

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

        # 1. 语义切分
        print("正在进行语义切分...")
        tasks = parse_intent(intent, history)
        print(f"切分结果: {tasks}")
        
        final_results = []
        
        # 2. 遍历执行子任务
        for i, task in enumerate(tasks):
            print(f"\n[{i+1}/{len(tasks)}] 处理子任务: {task}")
            
            if isinstance(task, str):
                # 降级逻辑：无法拆解的指令，直接交给 VLM
                print("-> 触发降级逻辑，交由 VLM 处理")
                res = _execute_single_task(task, max_attempts, gui_client_url, show_img, use_ocr=True, session_id=session_id)
                final_results.append(res)
                if res.get("status") == "failed":
                    print(f"子任务执行失败，终止后续任务。原因: {res.get('reason')}")
                    break
                    
            elif isinstance(task, dict):
                # 明确的四元组指令
                location = task.get("location")
                predicate = task.get("predicate")
                obj = task.get("object")
                target_type = task.get("target_type", "text")
                
                print(f"-> 尝试使用 UIAutomation 定位: {location}")
                coords_result = None
                
                # 1. 尝试 UIA 定位 (无论 target_type 是 text 还是 icon，都先尝试 UIA)
                try:
                    uia_res = requests.post(gui_client_url, json={
                        "action": "find_element",
                        "coords": [0, 0],
                        "text": location,
                        "session_id": session_id
                    }, timeout=5).json()
                    
                    if uia_res.get("status") == "success":
                        if "coords" in uia_res:
                            coords_result = {"x": uia_res["coords"][0], "y": uia_res["coords"][1]}
                            print(f"-> UIAutomation 定位成功，物理坐标: {coords_result}")
                            current_screenshot = uia_res.get("screenshot")
                        else:
                            print(f"-> UIAutomation 请求成功但未返回坐标，请检查服务端 gui_main.py 是否为最新版本！")
                    else:
                        print(f"-> UIAutomation 未找到目标 '{location}'")
                except Exception as e:
                    print(f"-> UIAutomation 请求失败: {e}")
                
                # 2. 如果 UIA 失败，根据 target_type 决定降级策略
                if not coords_result:
                    if target_type == "icon":
                        print(f"-> 目标 '{location}' 被判定为图标/语义概念，且 UIA 未找到，跳过 OCR，直接交由 VLM 处理")
                        fallback_intent = f"{predicate}{obj}"
                        res = _execute_single_task(fallback_intent, max_attempts, gui_client_url, show_img, use_ocr=False, session_id=session_id)
                        final_results.append(res)
                        if res.get("status") == "failed":
                            print(f"子任务执行失败，终止后续任务。原因: {res.get('reason')}")
                            break
                        continue
                    
                    print(f"-> 尝试直接 OCR 定位: {location}")
                    
                    # 获取当前截图
                    try:
                        initial_res = requests.post(gui_client_url, json={"action": "screenshot", "coords": [0, 0], "session_id": session_id})
                        if initial_res.status_code == 429:
                            print("服务端返回 429: 当前有其他任务正在执行")
                            final_results.append({"status": "failed", "reason": "当前有其他任务正在执行，请稍后再试"})
                            break
                        initial_res = initial_res.json()
                        current_screenshot = initial_res.get("screenshot")
                    except Exception as e:
                        print(f"请求截图失败: {e}")
                        final_results.append({"status": "failed", "reason": f"请求截图失败: {e}"})
                        break
                        
                    # 尝试 OCR 定位
                    coords_result = qwen_detector.get_target_coords(current_screenshot, location)
                    if coords_result:
                        print(f"-> OCR 定位成功，物理坐标: {coords_result}")
                
                if coords_result:
                    # UIA 或 OCR 找到了，直接执行动作
                    coords = [coords_result["x"], coords_result["y"]]
                    action = _map_predicate_to_action(predicate)
                    print(f"-> 准备执行动作: {action}，坐标: {coords}")
                    
                    req_data = {
                        "action": action,
                        "coords": coords,
                        "text": obj if action == "type" else "",
                        "key": "",
                        "session_id": session_id
                    }
                    
                    response = requests.post(gui_client_url, json=req_data).json()
                    print(f"-> 动作执行完成")
                    time.sleep(2)
                    
                    # --- 新增：验证直接执行的结果 ---
                    print("正在验证直接执行是否成功...")
                    try:
                        verify_res = requests.post(gui_client_url, json={"action": "screenshot", "coords": [0, 0], "session_id": session_id}).json()
                        verify_screenshot = verify_res.get("screenshot")
                        
                        verify_intent = f"{predicate}{obj}"
                        verification = verify_task_success(verify_screenshot, verify_intent)
                        is_success = verification.get("is_success", False)
                        reason = verification.get("reason", "未知原因")
                        
                        print(f"验证结果: {'成功' if is_success else '失败'} - {reason}")
                        
                        if is_success:
                            res_dict = {
                                "status": "success",
                                "reason": f"直接执行 {predicate} {obj} 成功: {reason}",
                                "coords": coords,
                                "attempts": 1
                            }
                            if show_img:
                                res_dict["img"] = verify_screenshot
                            final_results.append(res_dict)
                        else:
                            print(f"-> 直接执行后验证失败，降级交由 VLM 处理")
                            fallback_intent = f"{predicate}{obj}"
                            res = _execute_single_task(fallback_intent, max_attempts, gui_client_url, show_img, use_ocr=True, session_id=session_id)
                            final_results.append(res)
                            if res.get("status") == "failed":
                                print(f"子任务执行失败，终止后续任务。原因: {res.get('reason')}")
                                break
                    except Exception as e:
                        print(f"验证过程发生异常: {e}，降级交由 VLM 处理")
                        fallback_intent = f"{predicate}{obj}"
                        res = _execute_single_task(fallback_intent, max_attempts, gui_client_url, show_img, use_ocr=True, session_id=session_id)
                        final_results.append(res)
                        if res.get("status") == "failed":
                            print(f"子任务执行失败，终止后续任务。原因: {res.get('reason')}")
                            break
                else:
                    # OCR 没找到，说明缺失中间环节，降级给 VLM
                    print(f"-> OCR 未找到目标 '{location}'，可能缺失中间环节，降级交由 VLM 处理")
                    fallback_intent = f"{predicate}{obj}" # 组合成自然语言，如 "打开D盘"
                    res = _execute_single_task(fallback_intent, max_attempts, gui_client_url, show_img, use_ocr=True, session_id=session_id)
                    final_results.append(res)
                    if res.get("status") == "failed":
                        print(f"子任务执行失败，终止后续任务。原因: {res.get('reason')}")
                        break
                        
        print("\n========== 总任务执行完毕 ==========")
        # 返回最后一个任务的结果，或者汇总结果
        if final_results:
            return final_results[-1]
        return {"status": "failed", "reason": "没有执行任何任务"}
        
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
