# Ylbot GUI Agent

目前业界的 GUI Agent 主要分为三大流派，而我们目前的架构实际上是__集大成者的混合架构（Hybrid Architecture）__。

## 📚 文档导航 (Documentation)

- [如何安装配置](./docs/如何安装配置.md) - 从零开始的环境搭建与启动指南
- [怎样更换视觉模型和OCR模型](./怎样更换视觉模型和OCR模型.md) - 详细说明如何切换或添加新的大模型
- [录制说明](./录制说明.md) - 如何使用 `gui_recorder.py` 录制标准 RPA 流程
- [人在回路 (Human-in-the-loop)](./人在回路.md) - 了解 Agent 如何在遇到困难时请求人类协助
- [PC移动控制方案](./PC移动控制方案.md) - 关于如何控制 Android 设备的说明
- [ReAct 架构说明](./ReAct.md) - 深入了解 Agent 的动态规划与自愈机制

### 1. 核心竞争力与业界对比 (Core Competitiveness vs. Industry)

结合 **ReAct 动态规划**、**Redis 状态管理**、**人在回路 (Human-in-the-loop)** 以及 **C/S 分布式架构**，本项目已经从一个“高级自动化脚本”正式蜕变为一个**企业级 AI-RPA 平台**。

#### 1. vs. 传统商业 RPA (如 UiPath, 影刀, 实在智能)
*   **传统痛点**：高度依赖固定的 DOM 树或 UIA 节点。一旦目标软件更新 UI、或者遇到自绘引擎（游戏、远程桌面 KVM、Flash/Canvas），传统 RPA 就会直接“致盲”并报错卡死。
*   **我们的降维打击**：我们拥有 **AI 视觉兜底 (OCR + VLM)** 和 **ReAct 动态自愈** 能力。即使 UI 变了，Agent 也能通过“观察-思考”发现变化，并动态调整点击策略。

#### 2. vs. 前沿纯视觉 Agent (如 Claude Computer Use, OS-Copilot)
*   **前沿痛点**：纯视觉方案（直接让大模型输出 x,y 坐标）存在严重的“幻觉”问题，经常点歪；且每次操作都要等待大模型推理，单步延迟极高（动辄 10-20 秒），API 成本极其高昂。
*   **我们的降维打击**：我们采用 **混合定位策略 (Redis 缓存 -> 本地 OCR -> VLM 兜底)**。对于已知目标，直接走缓存或本地轻量级 OCR，实现**毫秒级响应**和 **100% 准确率**，只有在极度复杂的语义理解时才动用 VLM，兼顾了极致的速度与极低的成本。

#### 3. vs. 学术界视觉标记流派 (如 微软 OmniParser, 苹果 Ferret-UI)
*   **学术界痛点**：Set-of-Mark (SoM) 方案会在屏幕上所有可点击元素画上框并标上数字（1, 2, 3...），然后让大模型选数字。这种方式对全屏进行密集检测，计算冗余极大，且画面极其混乱。
*   **我们的降维打击**：我们采用 **目标驱动的逆向检测**。大模型先思考“我要找什么”（比如“提交按钮”），然后直接用检测模型去画面里精准定位这个目标。这更符合人类的视觉注意力机制，算力消耗极小。

#### 4. vs. 开源单机 GUI 脚本 (如 GitHub 上的各类 Auto-GUI 项目)
*   **开源痛点**：绝大多数开源项目都是单机玩具，代码耦合严重，一旦多用户并发调用就会互相抢夺鼠标键盘，状态完全混乱。
*   **我们的降维打击**：我们原生设计了 **C/S 分布式架构 + Redis 全局状态锁 + 人在回路**。通过 `user_id = session_id` 的完美映射，我们不仅解决了并发冲突（保护性拒绝），还能随时暂停任务等待人类扫码/验证，直接具备了 **RPA-as-a-Service (SaaS)** 的商业化落地能力。

---

### 2. 我们当前架构的综合评价

目前的 `Ylbot GUI Agent` 架构，在**执行稳定性**上超越了纯视觉大模型，在**泛化能力**上碾压了传统 RPA，在**商业落地能力**上甩开了绝大多数开源单机脚本。它是一个真正懂业务、能落地、可扩展的“数字员工”基础设施。

__🏆 领先业界的亮点（我们的护城河）：__

1. __ReAct 动态规划与自愈 (Dynamic Planning & Self-Healing)__：
   - 彻底抛弃了脆弱的静态子任务切分。Agent 在每执行一步后，都会重新观察屏幕，动态决定下一步做什么。如果点击失败或遇到弹窗，Agent 会自动思考并修正行为（自愈）。
2. __混合驱动 (Hybrid) 的完美落地__：
   - **对于标准/高频流程**：我们提供 `gui_recorder.py` 录制 JSON 轨迹，保证 **100% 的准确率和极速响应**。
   - **对于未知/动态场景**：Agent 会无缝切换到探索模式，利用大模型进行推理。
3. __极高的实用性与响应速度__：在探索模式下，通过 `Redis 缓存 -> OCR -> VLM` 的三级降级策略，我们在“速度”和“泛化能力”之间找到了完美的平衡。能用缓存秒解的绝不浪费算力，缓存失效的用 OCR，OCR 找不到的用 VLM 语义推理。
4. __服务端/客户端解耦与并发控制__：我们实现了 `gui_main.py`（手/眼）和 `gui_agent.py`（脑）的分离，并加入了基于 Redis 的 Session 锁机制。这使得我们的 Agent 具备了控制远程主机、甚至未来实现“一对多”集群控制的潜力。
5. __闭环验证机制__：执行动作后，我们会再次截图让 VLM 验证是否成功（`verify_task_success`），这赋予了 Agent 基础的“纠错”能力。

---

### 3. 分布式 RPA 商业架构 (RPA-as-a-Service)

本项目已经进化为一个支持**分布式部署**和**人在回路 (Human-in-the-loop)** 的企业级 RPA 平台。其核心商业逻辑如下：

#### 架构亮点：
1. **大脑与四肢分离 (Server vs Clients)**：
   - **Server 端 (`gui_agent.py` / `gui_server.py`)**：集中管理 LLM/VLM 算力、技能库 (Skills) 和 Redis 状态。相当于系统的“大脑”。
   - **Client 端 (`gui_client.py` / `gui_main.exe`)**：部署在无数台 PC 上的轻量级执行器，只负责截图和执行鼠标/键盘动作。相当于系统的“四肢”。
2. **天然的负载均衡**：
   - 当用户请求涌入时，Server 可以将任务分发给任意空闲的 PC 节点。这意味着可以通过简单地增加 PC（甚至让用户贡献自己的 PC 算力）来无限提升系统的并发处理能力。
3. **状态与会话的完美映射 (`user_id` = `session_id`)**：
   - 完美兼容 `ylbot` 标准，将群聊/私聊的 `user_id` 作为 Agent 的全局唯一 `session_id`。
   - 无论用户在哪个终端发起请求，也无论中间是否经历了“人在回路”的等待，Agent 都能从 Redis 中精准捞出该用户的上下文（历史轨迹、当前状态），彻底解决多并发下的状态串扰问题。
4. **保护性拒绝 (Protective Rejection)**：
   - 基于 Redis 的全局锁机制。如果一个用户的任务正在执行中，系统会直接在 Server 端拒绝新的并发请求，保证任务的原子性和稳定性。

#### 架构示意图：

```text
[用户/群聊 (ylbot 标准)] 
       │ (发送自然语言指令 intent + 聊天历史 history + 用户标识 user_id)
       ▼
[API 网关 / gui_server.py] 
       │ (接收 user_id, intent, history)
       ▼
[GUI Agent 大脑 (gui_agent.py)] ──(检查 Redis 锁)──> 【拒绝并发请求】
       │ (将 user_id 作为 session_id)
       │ <══> [Redis 集群 (gui_redis.py: 状态/历史/坐标缓存)]
       │ (ReAct 循环: 思考、决策)
       │ (加载专属技能 gui_skills.py)
       │ (调用视觉模型 gui_vl.py)
       │ (调用坐标定位 ocr_service.py)
       │ (调用底层动作 gui_tools.py / gui_tools_android.py)
       ▼
[负载均衡器 / 路由] (未来规划)
       │
   ┌───┴───┬───────────────┐
   ▼       ▼               ▼
[PC1]    [PCN]          [Phone1]
(Windows/Mac/Linux)     (Android 手机)
运行 gui_client.py      运行 gui_client_android.py
```

#### 核心模块功能说明：
*   **`gui_server.py` (API 网关)**：提供 HTTP 接口（如 `/api/run_for_agent`），接收外部请求，解析参数并转发给 Agent。
*   **`gui_agent.py` (Agent 大脑)**：系统的核心控制中枢。实现 ReAct 循环，负责任务规划、状态管理、调用 VLM/OCR 进行决策，并处理“人在回路”等复杂逻辑。
*   **`gui_tools.py` / `gui_tools_android.py` (工具层)**：封装了供 Agent 调用的各种底层操作（如 PC 端的 `mouse_click`, `type_text`，以及 Android 端的 `window_control` 等）以及标准流程回放功能。
*   **`gui_redis.py` (状态管理层)**：封装了与 Redis 的交互，用于存储会话状态（防并发）、历史轨迹（供模型参考）和坐标缓存（加速执行）。
*   **`gui_skills.py` (技能管理层)**：负责根据用户意图匹配并加载专属的技能指导（Prompt），让 Agent 在特定场景下表现更专业。
*   **`gui_vl.py` (视觉大模型接口)**：封装了与 GLM-4V 等视觉大模型的交互，负责“观察”截图并输出“思考与动作”。
*   **`ocr_service.py` (坐标定位服务)**：负责屏幕元素的精准坐标定位，作为 VLM 的轻量级、高精度补充。
*   **`gui_main.py` / `gui_client.py` / `gui_client_android.py` (客户端执行器)**：部署在目标机器（PC 或 Android 手机）上的“手”和“眼”，负责执行具体的鼠标/键盘/触控动作并返回实时截图。

### 4. 核心执行逻辑 (ReAct 循环)

本项目已全面升级为基于 **ReAct (Reasoning + Acting)** 模式的动态规划架构，彻底取代了早期的静态子任务切分。

```text
[接收用户指令 + 对话历史]
       ↓
[技能路由 (Skill Manager)] ──> 匹配专属技能 (如: 浏览器操作、人在回路)
       ↓
[进入 ReAct 循环 (While not completed)]
       │
       ├─ 1. 观察 (Observation): 请求 Client 获取当前屏幕截图
       │
       ├─ 2. 思考 (Thought): VLM 结合总目标、对话历史、Agent 历史轨迹和当前截图，分析现状
       │
       ├─ 3. 动作 (Action): VLM 输出具体的 JSON 动作 (click, type, wait_for_human 等)
       │      │
       │      └─ 如果是 wait_for_human: 中断循环，保存状态到 Redis，等待人类介入
       │
       ├─ 4. 执行 (Execution): 将动作发送给 Client 执行
       │
       ├─ 5. 核验 (Verification): 再次截图，VLM 验证动作是否成功
       │
       └─ 6. 记忆 (Memory): 将 Thought, Action, Observation 存入 Redis 历史轨迹
       ↓
[任务完成 (Finish) 或 达到最大循环次数]
```

### 5. 客户端与录制工具 (Client & Recorder)

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

### 6. 核心复合工具 (Agent Tools)

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

### 7. 未来进化方向
1.  **长程记忆与状态机**：引入 UI 状态图（UI State Graph），让 Agent 具备跨窗口操作的逻辑连贯性。
2.  **复杂交互增强**：完善对“拖拽”、“长按”等非点按式连续动作的底层支持。
3.  **动态客户端路由**：实现真正的负载均衡器，让 Server 能够自动发现并分配任务给空闲的 Client 节点。

---

### 8. 基础 API 调用示例 (Client API)

#### 1. 鼠标点击 (Click)
用于点击按钮、切换窗口或聚焦输入框。

```bash
curl -X POST http://192.168.66.42:8000/execute \
     -H "Content-Type: application/json" \
     -d '{
           "action": "click",
           "coords": [585, 72]
         }'
```


#### 2. 鼠标双击 (Double Click)
用于打开桌面图标或选中整行文本。

```bash
curl -X POST http://192.168.66.42:8000/execute \
     -H "Content-Type: application/json" \
     -d '{
           "action": "double_click",
           "coords": [100, 100]
         }'
```

#### 3. 文本输入 (Type)
用于填充表单、账号密码或 URL。

> **注意：** 如果你在代码中使用了 `pyautogui.write()`，在字符串末尾添加 `\n` 可以直接触发回车。

```bash
curl -X POST http://192.168.66.42:8000/execute  \
     -H "Content-Type: application/json" \
     -d '{
           "action": "type",
           "coords": [585, 72],
           "text": "admin_account"
         }'
```



#### 4. 特殊按键 (Key Press)
用于触发 enter、tab、backspace、esc 等非字符按键。

```bash
curl -X POST http://192.168.66.42:8000/execute \
     -H "Content-Type: application/json" \
     -d '{
           "action": "key_press",
           "coords": [585, 72],
           "key": "enter"
         }'
```

#### 5. 滚轮操作 (Scroll)
用于查看长页面。coords 通常指定滚动发生的中心位置。

**基础向下滚动示例 (兼容旧版)：**
```bash
curl -X POST http://192.168.66.42:8000/execute \
     -H "Content-Type: application/json" \
     -d '{
           "action": "scroll",
           "coords": [960, 540],
           "text": "down"
         }'
```

**高级滚动示例 (支持方向和距离)：**
```bash
curl -X POST http://192.168.66.42:8000/execute \
     -H "Content-Type: application/json" \
     -d '{
           "action": "scroll",
           "coords": [960, 540],
           "scroll_dir": "right",
           "scroll_dist": 800
         }'
```

**直接滚动到底部示例：**
```bash
curl -X POST http://192.168.66.42:8000/execute \
     -H "Content-Type: application/json" \
     -d '{
           "action": "scroll",
           "coords": [960, 540],
           "scroll_dir": "down",
           "scroll_dist": 10000
         }'
```
*(注：`scroll_dir` 支持 "down", "up", "left", "right"；`scroll_dist` 默认 500，填极大值如 10000 可实现直接到底/顶)*

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
curl -X POST http://192.168.66.42:8000/execute \
     -H "Content-Type: application/json" \
     -d '{
           "action": "hotkey",
           "coords": [0, 0],
           "text": "ctrl+v"
         }'
```

## 项目地址
https://wwww.github.com/bifu123/guiai

## 联系方式
QQ: 415135222
