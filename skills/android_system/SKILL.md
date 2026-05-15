---
name: android_system
description: 当用户意图包含对Android手机进行系统级控制（如回到主屏幕、返回上一级、查看最近任务）时，请使用此技能。
---

## 手机系统控制指令

在控制 Android 手机时，如果需要执行系统级别的导航操作，请使用 `window_control` 动作，并根据需求传入对应的 `text` 参数：

- **回到主屏幕 (Home)**：
  当需要让手机回到桌面/主屏幕时，请调用 `window_control` 动作，并将 `text` 参数设置为 `home`。
  *(底层实现：`adb shell input keyevent 3`)*

- **返回上一级 (Back)**：
  当需要返回上一级页面、退出当前应用或关闭弹窗时，请调用 `window_control` 动作，并将 `text` 参数设置为 `back`。
  *(底层实现：`adb shell input keyevent 4`)*

- **查看最近任务 (Recents)**：
  当需要打开多任务/最近应用列表时，请调用 `window_control` 动作，并将 `text` 参数设置为 `recents`。
  *(底层实现：`adb shell input keyevent 187`)*

- **唤醒并解锁 (Wake and Unlock)**：
  **【重要】当手机处于黑屏状态需要解锁时，请务必使用此指令！**
  因为单纯点亮屏幕后，如果 Agent 思考时间过长，屏幕会在几秒内再次自动熄灭，导致无限循环。此指令会在底层连续执行“绝对唤醒屏幕 -> 等待 -> 向上滑动解锁”，一步到位。
  调用 `window_control` 动作，并将 `text` 参数设置为 `wake_and_unlock`。
  *(底层实现：连续执行 `adb shell input keyevent 224` (绝对唤醒，防止误关屏幕) 和 `adb shell input swipe 500 1500 500 200 300`)*

- **电源键 (Power)**：
  当需要单纯地熄灭屏幕或点亮屏幕（不需要解锁）时，请调用 `window_control` 动作，并将 `text` 参数设置为 `power`。
  *(底层实现：`adb shell input keyevent 26`)*

- **向上滑动解锁 (Unlock)**：
  当屏幕**已经点亮**但处于锁屏状态，需要向上滑动解锁时，请调用 `window_control` 动作，并将 `text` 参数设置为 `unlock`。
  *(底层实现：`adb shell input swipe 500 1500 500 200 300`)*

- **音量控制 (Volume)**：
  - 增加音量：调用 `window_control` 动作，`text` 参数设置为 `volume_up`。*(底层实现：`adb shell input keyevent 24`)*
  - 减小音量：调用 `window_control` 动作，`text` 参数设置为 `volume_down`。*(底层实现：`adb shell input keyevent 25`)*
  - 静音：调用 `window_control` 动作，`text` 参数设置为 `mute`。*(底层实现：`adb shell input keyevent 164`)*

- **通知栏控制 (Notifications)**：
  - 展开通知栏：调用 `window_control` 动作，`text` 参数设置为 `expand_notifications`。*(底层实现：`adb shell cmd statusbar expand-notifications`)*
  - 收起通知栏：调用 `window_control` 动作，`text` 参数设置为 `collapse_notifications`。*(底层实现：`adb shell cmd statusbar collapse`)*

## 通讯指令 (电话/短信)

当用户意图包含拨打电话或发送短信时，请使用以下专门的动作：

- **拨打电话**：
  调用 `call` 动作，并将 `text` 参数设置为需要拨打的电话号码（例如 `10086`）。
  *(底层实现：`adb shell am start -a android.intent.action.CALL -d tel:<电话号码>`)*

- **发送短信**：
  调用 `send_sms` 动作，并将 `text` 参数设置为 `手机号:短信内容` 的格式（例如 `10086:查询话费`）。
  *(底层实现：通过 `adb shell am start -a android.intent.action.SENDTO` 调起短信界面并填充内容，随后模拟按键发送)*
