用户输入意图
    ↓
VLM判断意图类型
    ↓
┌─ operate ──────────────────────┐
│ VLM提取目标名称+动作            │
│ → OCR定位坐标                   │
│ → 执行动作                      │
│ → 验证结果                      │
│ → 返回成功/失败+截图             │
└────────────────────────────────┘
    ↓
┌─ query ────────────────────────┐
│ VLM描述当前截图内容              │
│ → 返回描述文本+截图              │
└────────────────────────────────┘

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