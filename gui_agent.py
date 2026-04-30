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
   - 如果用户想打开程序、点击按钮、输入文字等（有明确的操作目标），则 action_type 为 "operate"

2. 如果 action_type 为 "operate"，请进一步：
   - 提取出需要操作的目标名称（如"此电脑"、"回收站"、"浏览器"等）
   - 确定需要执行的动作：
     - `click` - 单击（一般用于获得焦点、单击网页链接、单击普通按钮等）
     - `double_click` - 双击（【重要】在桌面上打开应用、运行程序、打开文件夹/磁盘等，必须使用双击！）
     - `type` - 输入值
   - 观察截图，找到目标在画面中的位置，并输出其中心点的归一化坐标（0-1000）：
     - norm_x: 0-1000 的整数（如果找不到目标，请输出 -1）
     - norm_y: 0-1000 的整数（如果找不到目标，请输出 -1）

请以 JSON 格式返回：
{{
    "action_type": "operate 或 query",
    "target": "目标名称（operate 时必填，query 时留空）",
    "action": "动作类型（operate 时必填，query 时留空）",
    "norm_x": 整数（0-1000，operate 时必填）,
    "norm_y": 整数（0-1000，operate 时必填）,
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

def _execute_single_task(task_intent: str, max_attempts: int, gui_client_url: str, show_img: bool, use_ocr: bool = True):
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
                "coords": [0, 0]
            }).json()
        except Exception as e:
            print(f"请求截图失败: {e}")
            return {"status": "failed", "reason": f"请求截图失败: {e}"}
            
        current_screenshot = initial_res.get("screenshot")
        if not current_screenshot:
            print(f"获取截图失败，服务端返回: {initial_res}")
            return {"status": "failed", "reason": f"获取截图失败: {initial_res.get('detail', '未知错误')}"}
        
        # --- 2. 决策：理解意图并提取目标 ---
        decision = ask_vlm_for_action(current_screenshot, task_intent)
        print(f"Agent 决策理由: {decision.get('reason')}")
        
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
            "key": decision.get("key", "")
        }
        
        response = requests.post(gui_client_url, json=req_data).json()
        print(f"动作执行完成，坐标: {req_data['coords']}")
        
        # 等待界面响应
        time.sleep(2)
        
        # --- 5. 验证结果 ---
        print("正在验证任务是否成功...")
        verify_res = requests.post(gui_client_url, json={
            "action": "screenshot",
            "coords": [0, 0]
        }).json()
        verify_screenshot = verify_res.get("screenshot")
        
        verification = verify_task_success(verify_screenshot, task_intent)
        is_success = verification.get("is_success", False)
        reason = verification.get("reason", "未知原因")
        
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

def run_agent_task(intent:str, max_attempts:int=5, gui_client_url:str="http://192.168.2.16:8000/execute", show_img:bool=False, history:list=None):
    print(f"========== 开始执行总任务: {intent} ==========")
    
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
            res = _execute_single_task(task, max_attempts, gui_client_url, show_img, use_ocr=True)
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
            
            if target_type == "icon":
                print(f"-> 目标 '{location}' 被判定为图标/语义概念，跳过 OCR，直接交由 VLM 处理")
                fallback_intent = f"{predicate}{obj}"
                res = _execute_single_task(fallback_intent, max_attempts, gui_client_url, show_img, use_ocr=False)
                final_results.append(res)
                if res.get("status") == "failed":
                    print(f"子任务执行失败，终止后续任务。原因: {res.get('reason')}")
                    break
                continue
                
            print(f"-> 尝试直接 OCR 定位: {location}")
            
            # 获取当前截图
            try:
                initial_res = requests.post(gui_client_url, json={"action": "screenshot", "coords": [0, 0]}).json()
                current_screenshot = initial_res.get("screenshot")
            except Exception as e:
                print(f"请求截图失败: {e}")
                final_results.append({"status": "failed", "reason": f"请求截图失败: {e}"})
                break
                
            # 尝试 OCR 定位
            coords_result = qwen_detector.get_target_coords(current_screenshot, location)
            
            if coords_result:
                # OCR 找到了，直接执行动作
                coords = [coords_result["x"], coords_result["y"]]
                action = _map_predicate_to_action(predicate)
                print(f"-> OCR 定位成功，物理坐标: {coords}，映射动作: {action}")
                
                req_data = {
                    "action": action,
                    "coords": coords,
                    "text": obj if action == "type" else "",
                    "key": ""
                }
                
                response = requests.post(gui_client_url, json=req_data).json()
                print(f"-> 动作执行完成")
                time.sleep(2)
                
                # --- 新增：验证直接执行的结果 ---
                print("正在验证直接执行是否成功...")
                try:
                    verify_res = requests.post(gui_client_url, json={"action": "screenshot", "coords": [0, 0]}).json()
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
                        res = _execute_single_task(fallback_intent, max_attempts, gui_client_url, show_img, use_ocr=True)
                        final_results.append(res)
                        if res.get("status") == "failed":
                            print(f"子任务执行失败，终止后续任务。原因: {res.get('reason')}")
                            break
                except Exception as e:
                    print(f"验证过程发生异常: {e}，降级交由 VLM 处理")
                    fallback_intent = f"{predicate}{obj}"
                    res = _execute_single_task(fallback_intent, max_attempts, gui_client_url, show_img, use_ocr=True)
                    final_results.append(res)
                    if res.get("status") == "failed":
                        print(f"子任务执行失败，终止后续任务。原因: {res.get('reason')}")
                        break
            else:
                # OCR 没找到，说明缺失中间环节，降级给 VLM
                print(f"-> OCR 未找到目标 '{location}'，可能缺失中间环节，降级交由 VLM 处理")
                fallback_intent = f"{predicate}{obj}" # 组合成自然语言，如 "打开D盘"
                res = _execute_single_task(fallback_intent, max_attempts, gui_client_url, show_img, use_ocr=True)
                final_results.append(res)
                if res.get("status") == "failed":
                    print(f"子任务执行失败，终止后续任务。原因: {res.get('reason')}")
                    break
                    
    print("\n========== 总任务执行完毕 ==========")
    # 返回最后一个任务的结果，或者汇总结果
    if final_results:
        return final_results[-1]
    return {"status": "failed", "reason": "没有执行任何任务"}

if __name__ == "__main__":
    # 保持你的 API Key 不变
    response = run_agent_task(r"打开桌面上的`此电脑`")
    print(json.dumps(response,ensure_ascii=False,indent=4))
