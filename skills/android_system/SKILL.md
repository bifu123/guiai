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
