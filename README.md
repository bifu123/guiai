目前业界的 GUI Agent 主要分为三大流派，而我们目前的架构实际上是__集大成者的混合架构（Hybrid Architecture）__。

### 1. 业界三大流派 vs 我们的实现

#### 流派一：纯视觉大模型流派 (Pure VLM)

- __代表作__：Anthropic 的 Claude Computer Use、早期的 OS-Copilot、各种基于 GPT-4o 的开源脚本。
- __做法__：直接把屏幕截图丢给大模型，让大模型输出点击的 `(x, y)` 坐标。
- __痛点__：大模型对绝对坐标的感知非常差，经常点歪（幻觉）；且每次操作都要等大模型推理，延迟极高（动辄 10-20 秒）；API 成本高昂。
- __我们的优势__：我们__只在最后兜底时__才让 VLM 估算坐标。常规操作我们根本不依赖 VLM 的空间坐标能力，从而彻底解决了“点歪”和“慢”的问题。

#### 流派二：纯无障碍树流派 (Pure Accessibility Tree / DOM)

- __代表作__：传统 RPA（UiPath）、基于 Web DOM 的 Agent（如 WebVoyager）、基于纯 UIA 的自动化测试。
- __做法__：解析系统的 UI 树或网页的 DOM 树，通过节点属性定位。
- __痛点__：遇到自绘引擎（如 QT、Flutter、游戏界面）、远程桌面（如你之前测试的 KVM 窗口）、或者网页里的 Canvas，UI 树就瞎了，什么都抓不到。
- __我们的优势__：我们把 UIA 作为__第一优先级（Fast Path）__，保证了标准控件的极速响应（毫秒级）和 100% 准确率；但当 UIA 失效时，我们能平滑降级到视觉方案。

#### 流派三：视觉标记流派 (Set-of-Mark / Grounding)

- __代表作__：微软的 OmniParser、苹果的 Ferret-UI。
- __做法__：先用一个小模型（如 YOLO/OCR）把屏幕上所有可点击的元素框出来，标上数字（1, 2, 3...），然后把带数字的图发给大模型，问大模型“你要点几号？”。
- __痛点__：每次都要对全屏做密集的检测，画面会被框框画得非常乱，且依然需要大模型参与每一次决策。
- __我们的优势__：我们采用了**语义切分 + 目标检测（Qwen-VL/OCR）**的逆向思路。我们先让 LLM 知道要找“什么”（比如“此电脑”），然后直接用检测模型去画面里找这个特定的目标。这比全屏打标记更轻量、更符合人类直觉。

---

### 2. 我们当前架构的综合评价

我们目前实现的架构可以总结为：__“混合驱动架构 (Hybrid Architecture)：Agent 意图理解 + JSON 轨迹精准执行 + 三级降级定位”__。

__🏆 领先业界的亮点（我们的护城河）：__

1. __混合驱动 (Hybrid) 的完美落地__：
   - **对于标准/高频流程**：我们提供 `gui_recorder.py` 录制 JSON 轨迹，保证 **100% 的准确率和极速响应**。Agent 只需要负责从自然语言中提取动态参数（如账号、密码），并通过 `params` 字典注入到 JSON 流程中执行。这彻底解决了纯视觉 Agent “慢”和“容易点歪”的痛点。
   - **对于未知/动态场景**：当 JSON 轨迹失效或遇到新任务时，Agent 会无缝切换到探索模式，利用大模型进行推理。
2. __极高的实用性与响应速度__：在探索模式下，通过 `UIA -> OCR -> VLM` 的三级降级策略，我们在“速度”和“泛化能力”之间找到了完美的平衡。能用 UIA 秒解的绝不浪费算力，UIA 瞎了的用 OCR，OCR 找不到的用 VLM 语义推理。
3. __服务端/客户端解耦与并发控制__：我们实现了 `gui_main.py`（手/眼）和 `gui_agent.py`（脑）的分离，并加入了 Session 锁机制。这使得我们的 Agent 具备了控制远程主机、甚至未来实现“一对多”集群控制的潜力。
4. __闭环验证机制__：执行动作后，我们会再次截图让 VLM 验证是否成功（`verify_task_success`），这赋予了 Agent 基础的“纠错”能力。

---

### 3. 客户端与录制工具 (Client & Recorder)

为了应对企业级应用中对稳定性和速度的极致要求，本项目提供了独立的客户端执行器和轻量级的 RPA 录制工具。

#### 1. 客户端执行器 (`gui_main.exe`)
`gui_main.py` 是整个架构的“手”和“眼”，负责在目标机器上执行具体的 GUI 操作并返回截图。
- **独立运行**：我们已将其打包为独立的 `gui_main.exe`，可以直接在任何 Windows 机器上运行，无需安装 Python 环境。
- **C/S 架构**：它作为一个 HTTP 服务端运行（默认端口 8000），接收来自 Agent 或外部脚本的指令。

#### 2. 轨迹录制工具 (`gui_recorder.exe`)
为了快速生成标准流程的 JSON 轨迹，我们提供了可视化的录制工具。
- **独立运行**：同样已打包为 `gui_recorder.exe`，双击即可使用。
- **核心功能**：通过快捷键（F8-F12）记录鼠标和键盘操作，支持弹窗输入注释和动态文本（如 `${username}`），最终保存为 JSON 文件供 `execute_manual_flow` 回放。

> 详细的录制工具使用方法请参考：[录制说明.md](./录制说明.md)

---

### 4. 核心复合工具 (Agent Tools)

本项目在 `gui_tools.py` 中提供了两个强大的复合工具，供 Agent 或外部脚本直接调用，完美体现了“混合驱动”的理念：

#### 1. `execute_manual_flow` (RPA 流程执行器)
用于精准回放录制的 JSON 轨迹，并支持动态参数注入。
- **适用场景**：登录、打开特定软件等固定且高频的标准流程。
- **优势**：100% 准确率，无需大模型推理，执行速度极快。
- **核心参数**：
  - `flow_data`: JSON 文件路径或包含步骤的列表。
  - `params`: 动态参数字典，用于替换 JSON 轨迹中的 `${var}` 占位符。
  - `time_sleep`: 每步执行后的等待时间。
- **使用示例**：
  ```python
  from gui_tools import execute_manual_flow
  
  # 传入动态参数，执行登录流程
  user_data = {"username": "admin", "password": "123"}
  result = execute_manual_flow(flow_data="login_flow.json", params=user_data)
  print(result) # 返回 {"status": "success", "message": "...", "screenshot": "base64..."}
  ```

#### 2. `run_for_agent` (自然语言意图执行器)
用于处理未知或动态场景，将自然语言指令转化为具体的 GUI 操作。
- **适用场景**：探索性任务、非标准流程、需要语义理解的操作。
- **优势**：结合 UIA/OCR/VLM 三级降级策略，兼顾速度与泛化能力。
- **核心参数**：
  - `intent`: 用户的自然语言意图（如“打开浏览器并搜索天气”）。
  - `max_attempts`: 最大尝试次数，防止死循环。
  - `show_img`: 是否在返回结果中包含执行后的截图 base64。
- **使用示例**：
  ```python
  from gui_tools import run_for_agent
  
  # 直接传入自然语言意图
  result = run_for_agent(intent="在桌面上打开此电脑图标", max_attempts=5)
  print(result) # 返回格式化的字符串，包含操作结果、坐标和尝试次数
  ```

__🚧 相比顶尖前沿研究的不足（未来的进化方向）：__

1. __缺乏动态规划（Dynamic Planning）__：目前我们的 `gui_parser.py` 是一次性把用户的长指令切分成静态的子任务列表。如果执行到一半，弹出了一个意外的广告窗口，或者目标在下一页需要滚动，我们目前的逻辑可能会卡死或直接失败。**业界前沿（如 ReAct 框架）**会在每执行一步后，重新观察屏幕，动态决定下一步做什么。
2. __缺乏长程记忆与状态机__：Agent 目前没有记住“我刚才打开了什么窗口”。如果能引入类似 UI 状态图（UI State Graph）的记忆机制，Agent 就能知道“要找设置，得先点开始菜单”。
3. __复杂交互的支持__：目前支持了点击、输入、滚动，但对于“拖拽（Drag & Drop）”、“长按”等复杂连续动作的支持还需要完善。

__总结：__ 作为一个从零手搓的项目，我们目前的架构已经超越了绝大多数简单的“截图+API”的玩具脚本，达到了__准工业级 RPA 结合 AI__ 的水准。三级降级定位策略是这个项目最大的亮点！





用户输入意图 (可能包含多个连续动作)
    ↓
LLM (gui_parser) 语义切分与解析
    ↓
生成子任务列表: List[dict | str]
    ↓
遍历执行每个子任务 ──────────────────────────┐
    ↓                                        │
┌─ 如果是 dict (三元组: location, predicate, object) ─┐
│ 明确的操作指令 (operate)                            │
│ 1. location → OCR直接定位坐标                       │
│ 2. predicate + object → 映射为具体动作(click/type)  │
│ 3. 执行动作                                         │
│ 4. VLM验证结果 (可选/按需)                          │
└─────────────────────────────────────────────────────┘
    ↓                                        │
┌─ 如果是 str (无法拆解或查询类) ─────────────────────┐
│ 模糊指令或查询指令 (query/复杂operate)              │
│ 1. 原始字符串交由 VLM 处理 (降级到原有逻辑)         │
│ 2. VLM判断意图类型 (operate/query)                  │
│ 3. 走原有逻辑 (提取动作/描述截图)                   │
└─────────────────────────────────────────────────────┘
    ↓
所有子任务完成，返回最终结果+截图




### 1. 鼠标点击 (Click)
用于点击按钮、切换窗口或聚焦输入框。

```bash
curl -X POST http://192.168.2.16:8000/execute \
     -H "Content-Type: application/json" \
     -d '{
           "action": "click",
           "coords": [585, 72]
         }'
```


### 2. 鼠标双击 (Double Click)
用于打开桌面图标或选中整行文本。

```bash
curl -X POST http://192.168.2.16:8000/execute \
     -H "Content-Type: application/json" \
     -d '{
           "action": "double_click",
           "coords": [100, 100]
         }'
```

### 3. 文本输入 (Type)
用于填充表单、账号密码或 URL。

> **注意：** 如果你在代码中使用了 `pyautogui.write()`，在字符串末尾添加 `\n` 可以直接触发回车。

```bash
curl -X POST http://192.168.2.16:8000/execute  \
     -H "Content-Type: application/json" \
     -d '{
           "action": "type",
           "coords": [585, 72],
           "text": "admin_account"
         }'
```



### 4. 特殊按键 (Key Press)
用于触发 enter、tab、backspace、esc 等非字符按键。

```bash
curl -X POST http://192.168.2.16:8000/execute \
     -H "Content-Type: application/json" \
     -d '{
           "action": "key_press",
           "coords": [585, 72],
           "key": "enter"
         }'
```

### 5. 滚轮操作 (Scroll)
用于查看长页面。coords 通常指定滚动发生的中心位置。

```bash
curl -X POST http://192.168.2.16:8000/execute \
     -H "Content-Type: application/json" \
     -d '{
           "action": "scroll",
           "coords": [960, 540],
           "text": "10"
         }'
```
*(注：根据你代码的实现，text 或其他字段可以用来传递滚动距离)*

---

### 💡 进阶：如何让 Agent 处理组合键 (如 Ctrl+V)？
如果你需要 Agent 执行粘贴、全选等操作，建议在 `guiauto_main.py` 的 `key_press` 逻辑中加入对 `hotkey` 的支持：

修改代码片段：

```python
        elif req.action == "hotkey":
            # 接收类似 ["ctrl", "v"] 的列表
            pyautogui.hotkey(*req.text.split('+'))
```

对应的 curl：

```bash
curl -X POST http://192.168.2.16:8000/execute \
     -H "Content-Type: application/json" \
     -d '{
           "action": "hotkey",
           "coords": [0, 0],
           "text": "ctrl+v"
         }'
```
