# 在 Android 手机（OPPO A95 5G）安装客户端实现 GUI 对手机的控制

我们实现的思路是在手机上通过安装 `Termux` 来提供一个 linux python 的环境来实现对手机的控制，我们将一台 OPPO A95 5G 手机成功改造为了由 Agent 调度的标准化执行节点。以下是全流程的架构与业务实现总结：

##  一、Termux 中的 python 环境
**目标**：构建开发环境，打通 Android 系统交互接口。

```bash
pkg update && pkg upgrade -y
pkg install python android-tools termux-api clang make binutils libffi openssl libjpeg-turbo -y
pip install pydantic==1.10.12
pip install fastapi
pip install uvicorn==0.22.0

# 检查python脚本环境完整性
python -c "import fastapi; import uvicorn; print(f'FastAPI: {fastapi.__version__}\nUvicorn: {uvicorn.__version__}')"

# 运行脚本
python gui_client_android.py
```

## 二、 底层驱动与硬件握手
由于 Android 11+ 的安全机制，无法直接连接端口，我们需要分两步完成设备层面的权限获取：
1. **鉴权配对**：在 Termux 环境中，通过 `adb pair 192.168.66.40:41513` 配合动态 6 位配对码（657284）完成了设备的信任绑定。
2. **职责接管**：认证通过后，执行 `adb connect 192.168.66.40:38881` 建立正式的无线调试隧道，并通过 `adb devices` 确认设备在线。
3. **物理验证**：直接下发 `adb shell input keyevent 3` 成功让手机退回桌面，确认环境具备了最高级别的系统级控制权。

## 三、检查手机是否可以控制
### 检查 adb shell 
在termux中运行
```bash
adb shell input keyevent 3
```
(回到主屏幕)

### 检查客户端API接口
在termux中运行
```bash
curl -X POST "http://127.0.0.1:8000/execute" \
     -H "Content-Type: application/json" \
     -d '{
           "action": "click",
           "coords": [540, 1200],
           "session_id": "ains_test_001"
         }'
```
(回到主屏幕)

