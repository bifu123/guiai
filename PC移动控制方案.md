# Ylbot GUI Agent - PC与移动端统一控制架构方案

随着 `gui_client_android.py` 和 `gui_tools_android.py` 的引入，Ylbot GUI Agent 正在从单一的 PC 桌面自动化平台，向**跨平台（PC + 移动端）统一控制中枢**演进。

为了保持系统架构的简洁性、可维护性和高扩展性，我们**不需要**为移动端单独建立一套 `gui_agent.py` 或 `gui_server.py`。相反，我们应该将现有的 Server 端打造为一个**跨平台的中央大脑**。

---

## 1. 核心设计理念：大脑与四肢分离

*   **中央大脑 (Server 端)**：`gui_server.py` (API 网关) 和 `gui_agent.py` (ReAct 决策引擎)。它们负责接收指令、管理状态 (Redis)、调用大模型 (VLM) 进行视觉推理和动作规划。大脑**不关心**具体的执行环境是 Windows 还是 Android。
*   **跨平台四肢 (Client 端)**：`gui_client.py` (PC 执行器) 和 `gui_client_android.py` (Android 执行器)。它们负责接收标准化的动作指令（如 `click`, `type`, `scroll`），在各自的平台上执行，并返回屏幕截图。

---

## 2. 统一控制架构图

```text
[用户/群聊 (ylbot 标准)] 
       │ (发送自然语言指令 intent + 聊天历史 history + 用户标识 user_id + 目标设备 device_type)
       ▼
[API 网关 / gui_server.py] 
       │ (接收请求，根据 device_type 确定目标 gui_client_url)
       ▼
[GUI Agent 大脑 (gui_agent.py)] ──(检查 Redis 锁)──> 【拒绝并发请求】
       │ (将 user_id 作为 session_id)
       │ <══> [Redis 集群 (gui_redis.py: 状态/历史/坐标缓存)]
       │ (ReAct 循环: 思考、决策)
       │ (加载专属技能 gui_skills.py)
       │ (调用视觉模型 gui_vl.py)
       │ (调用坐标定位 ocr_service.py)
       │
       ├───────────────────────── 动态路由分发 ─────────────────────────┐
       │ (发送标准 ActionRequest)                                       │ (发送标准 ActionRequest)
       ▼                                                                ▼
[PC 客户端 (gui_client.py)]                                      [Android 客户端 (gui_client_android.py)]
(运行在 Windows 物理机/虚拟机)                                   (运行在 Android 手机/模拟器)
       │                                                                │
       └─> 执行 pyautogui 动作并返回截图                                └─> 执行 adb/uiautomator 动作并返回截图
```

---

## 3. 具体实现方案

为了实现上述架构，我们需要在现有的代码基础上进行轻量级的改造，核心在于**动态路由**和**接口标准化**。

### 方案 A：通过 `gui_client_url` 动态路由 (推荐，最简单)

这是目前最平滑的过渡方案。`AgentRequest` 模型中已经存在 `gui_client_url` 字段。

1.  **API 网关层 (`gui_server.py`)**：
    *   允许调用方在请求 `/api/run_for_agent` 时，显式传入目标设备的 `gui_client_url`。
    *   例如，控制 PC 传入 `http://192.168.x.x:8000/execute`，控制 Android 传入 `http://192.168.y.y:8002/execute`。
2.  **Agent 大脑层 (`gui_agent.py`)**：
    *   无需修改核心逻辑。`requests.post(gui_client_url, ...)` 会自动将动作指令发送到指定的执行器。
3.  **Client 执行层**：
    *   **关键要求**：`gui_client_android.py` 必须实现与 `gui_client.py` **完全一致的 API 接口规范**。即接收相同的 `ActionRequest` JSON 结构，并返回包含 `screenshot` (Base64) 的 JSON 响应。

### 方案 B：引入 `device_type` 字段进行智能路由

这种方案对最终用户更友好，用户不需要记住具体的 IP 和端口。

1.  **修改请求模型 (`gui_server.py`)**：
    *   在 `AgentRequest` 中增加 `device_type: str = "pc"` (可选 "pc" 或 "android")。
2.  **配置管理**：
    *   在 `.env` 文件中配置不同设备的默认 URL：
        ```env
        GUI_CLIENT_URL_PC=http://192.168.x.x:8000/execute
        GUI_CLIENT_URL_ANDROID=http://192.168.y.y:8002/execute
        ```
3.  **智能路由 (`gui_server.py`)**：
    *   在 `api_run_for_agent` 函数中，根据传入的 `device_type`，从环境变量中读取对应的 URL，并将其作为 `gui_client_url` 传递给 `gui_agent.py`。

---

## 4. 关于手动流程工具 (`gui_tools.py` vs `gui_tools_android.py`)

对于录制好的固定流程（JSON 轨迹），同样适用上述路由逻辑。

*   `gui_server.py` 中的 `/api/execute_manual_flow` 接口接收 `endpoint` 参数。
*   如果执行 PC 流程，传入 PC 端的 URL；如果执行 Android 流程，传入 Android 端的 URL。
*   为了代码整洁，可以考虑将 `gui_tools.py` 和 `gui_tools_android.py` 中通用的网络请求逻辑提取出来，只在具体的动作解析上做区分（如果 JSON 轨迹格式有差异的话）。如果 JSON 轨迹格式完全一致，甚至可以合并为一个工具。

## 5. 总结

通过**统一的 API 协议**和**动态的 URL 路由**，Ylbot GUI Agent 可以轻松实现“一个大脑，控制多端”。这不仅避免了代码的重复建设，也为未来接入更多类型的设备（如 Mac、Linux、甚至 IoT 设备）奠定了坚实的架构基础。
