import json
import re
from gui_llm import llm
from langchain_core.messages import SystemMessage, HumanMessage

from typing import Union

def parse_intent(user_input: str, history:list[dict]=None) -> list[Union[dict, str]]:
    """
    使用 LLM 将用户复杂的自然语言描述切分为多个“在什么地方做什么”的三元组子任务列表。
    如果无法提取，则原样返回用户问题。
    
    Args:
        user_input (str): 用户的原始自然语言指令，例如 "帮我打开D盘，然后打开test文件夹"
        history (list[dict]): 聊天对话历史，当用户当前问题无法判断明显的谓宾结构时，可以参考对话历史
        
    Returns:
        list[Union[dict, str]]: 按顺序排列的子任务列表，每个元素包含 location, predicate, object，或者直接是原始字符串
    """
    
    system_prompt = f"""
你是一个专业的 GUI 自动化指令解析引擎。
你的任务是将用户复杂的自然语言指令，拆解为多个按顺序执行的简单子任务。

【拆解规则】：
1. 每个子任务必须被拆解为“在什么地方（位置）做什么（谓语-宾语）”的三元组结构。
   - location: 动作发生的位置或目标名称（便于 OCR 提取位置坐标，如 "D盘"、"搜索框"、"确定按钮"）。
   - predicate: 动作谓词（便于 VLM 决策动作，如 "打开"、"点击"、"输入"、"按"）。
   - object: 动作的宾语或具体内容（如 "D盘"、"hello world"、"回车"）。
2. 必须严格按照用户意图的执行顺序进行拆分。
3. 忽略无意义的语气词（如“帮我”、“请”、“然后”等）。
4. 当用户当前问题无法判断明显的上下文时，必须参考对话历史来推断当前所处的界面或目标。
5. 如果用户的指令无法拆解为明确的动作（例如询问屏幕内容、查询状态等），请直接返回包含原始指令的字符串数组。

【对话历史】:
{history}

【输出格式】：
你必须严格输出一个 JSON 格式的数组，不要包含任何其他解释性文字或 Markdown 标记。
如果是动作指令，格式如下：
[
  {{"location": "位置", "predicate": "谓语", "object": "宾语"}}
]
如果是查询指令或无法拆解，格式如下：
[
  "原始指令字符串"
]

【示例】：
输入：帮我打开D盘，然后打开test文件夹
输出：
[
  {{"location": "D盘", "predicate": "打开", "object": "D盘"}},
  {{"location": "test文件夹", "predicate": "打开", "object": "test文件夹"}}
]

输入：先点击左上角的文件，再点击保存，最后关闭窗口
输出：
[
  {{"location": "文件", "predicate": "点击", "object": "文件"}},
  {{"location": "保存", "predicate": "点击", "object": "保存"}},
  {{"location": "关闭按钮", "predicate": "点击", "object": "关闭窗口"}}
]

输入：在搜索框输入hello world，然后按回车
输出：
[
  {{"location": "搜索框", "predicate": "输入", "object": "hello world"}},
  {{"location": "回车键", "predicate": "按", "object": "回车"}}
]

【带历史的示例】：
对话历史：[{{"role": "user", "content": "帮我打开D盘"}}, {{"role": "assistant", "content": "好的，已经打开D盘"}}]
输入：然后打开test文件夹
输出：
[
  {{"location": "test文件夹", "predicate": "打开", "object": "test文件夹"}}
]

对话历史：[{{"role": "user", "content": "打开微信"}}, {{"role": "assistant", "content": "微信已打开"}}]
输入：发消息给张三说你好
输出：
[
  {{"location": "搜索框", "predicate": "点击", "object": "搜索框"}},
  {{"location": "搜索框", "predicate": "输入", "object": "张三"}},
  {{"location": "张三", "predicate": "点击", "object": "张三"}},
  {{"location": "输入框", "predicate": "输入", "object": "你好"}},
  {{"location": "发送按钮", "predicate": "点击", "object": "发送"}}
]

【无法拆解的示例】：
输入：帮我看一下屏幕上有什么
输出：
[
  "帮我看一下屏幕上有什么"
]
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"输入：{user_input}\n输出：")
    ]
    
    try:
        response = llm.invoke(messages)
        content = response.content.strip()
        
        # 尝试清理可能存在的 Markdown 标记
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
            
        # 尝试解析 JSON
        try:
            tasks = json.loads(content)
            if isinstance(tasks, list):
                return tasks
            else:
                print(f"[警告] LLM 返回的不是列表格式: {content}")
                return [user_input] # 降级处理
        except json.JSONDecodeError:
            print(f"[错误] 无法解析 LLM 响应为 JSON: {content}")
            return [user_input] # 降级处理
                
    except Exception as e:
        print(f"[错误] 调用 LLM 失败: {e}")
        return [user_input] # 降级处理

if __name__ == "__main__":
    # 测试用例
    test_cases = [
        ("帮我打开D盘，然后打开test文件夹", None),
        ("先点击左上角的文件，再点击保存，最后关闭窗口", None),
        ("在搜索框输入hello world，然后按回车", None),
        ("打开微信", None),
        ("然后打开test文件夹", [{"role": "user", "content": "帮我打开D盘"}, {"role": "assistant", "content": "好的，已经打开D盘"}]),
        ("发消息给张三说你好", [{"role": "user", "content": "打开微信"}, {"role": "assistant", "content": "微信已打开"}]),
        ("帮我看一下屏幕上有什么", None)
    ]
    
    print("=== 语义切分引擎测试 ===")
    for i, (test_input, history) in enumerate(test_cases, 1):
        print(f"\n测试 {i}:")
        print(f"原始输入: {test_input}")
        if history:
            print(f"对话历史: {history}")
        
        tasks = parse_intent(test_input, history)
        
        print("切分结果:")
        for j, task in enumerate(tasks, 1):
            if isinstance(task, dict):
                print(f"  步骤 {j}: 在 [{task.get('location', '未知')}] 执行 [{task.get('predicate', '未知')}] -> [{task.get('object', '未知')}]")
            else:
                print(f"  步骤 {j}: [原样返回] {task}")
