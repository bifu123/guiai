# gui_agent.py
import base64
import time
import requests
import json
from gui_vl import glm_4_6v_flash
from ocr_service import QwenDetector
from ocr_openrouter import OpenRouterDetector

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
     - `click` - 单击（一般用于获得焦点、单击按钮等）
     - `double_click` - 双击（一般用于打开程序图标、选中长文本）
     - `type` - 输入值

请以 JSON 格式返回：
{{
    "action_type": "operate 或 query",
    "target": "目标名称（operate 时必填，query 时留空）",
    "action": "动作类型（operate 时必填，query 时留空）",
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

def run_agent_task(intent:str, max_attempts:int=5, gui_client_url:str="http://192.168.2.16:8000/execute", show_img:bool=False):
    print(f"开始执行任务职责: {intent}")
    
    reason = "操作失败"
    
    for attempt in range(max_attempts):
        print(f"\n--- 第 {attempt + 1}/{max_attempts} 次尝试 ---")
        
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
        # print(f'[GUI] - step 1 - 初始截图:\n {current_screenshot[50]}...')
        
        # --- 2. 决策：理解意图并提取目标 ---
        decision = ask_vlm_for_action(current_screenshot, intent)
        # print(f'[GUI] - step 2 - 决策：理解意图并提取目标:\n {json.dumps(decision,ensure_ascii=False,indent=4)}')
        print(f"Agent 决策理由: {decision.get('reason')}")
        
        action_type = decision.get("action_type", "operate")
        
        # --- 如果是 query 类型（查询/描述屏幕），直接返回描述结果 ---
        if action_type == "query":
            print("检测到查询型意图，正在描述屏幕内容...")
            description = describe_screen(current_screenshot, intent)
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

        # --- 3. 定位：使用 QwenDetector 获取物理坐标 ---
        print(f"正在使用 QwenDetector 定位目标: {target_name} ...")
        coords_result = qwen_detector.get_target_coords(current_screenshot, target_name)
        # print(f'[GUI] - step 3 - 定位目标:\n {json.dumps(coords_result,ensure_ascii=False,indent=4)}')
        
        if not coords_result:
            print(f"定位目标 {target_name} 失败。")
            return {"status": "failed", "reason": "Target localization failed"}
            
        coords = [coords_result["x"], coords_result["y"]]
        print(f"定位成功，物理坐标: {coords}")
        
        # --- 4. 执行动作 ---
        req_data = {
            "action": action,
            "coords": coords,
            "text": decision.get("text", ""),
            "key": decision.get("key", "")
        }
        
        response = requests.post(gui_client_url, json=req_data).json()
        # print(f'[GUI] - step 4 - 执行动作:\n {json.dumps(response,ensure_ascii=False,indent=4)}')
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
        
        verification = verify_task_success(verify_screenshot, intent)
        # print(f'[GUI] - step 5 - 验证任务是否成功:\n {json.dumps(verification,ensure_ascii=False,indent=4)}')
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
            
    return {
        "status": "failed", 
        "reason": reason
    }

if __name__ == "__main__":
    # 保持你的 API Key 不变
    response = run_agent_task(r"打开桌面上的`此电脑`")
    print(json.dumps(response,ensure_ascii=False,indent=4))
