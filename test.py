import requests
import time
import os
from dotenv import load_dotenv

load_dotenv()

# 默认使用环境变量中的 URL，如果没有则使用默认值
GUI_CLIENT_URL = os.getenv("GUI_CLIENT_URL_ANDROID", "http://192.168.66.40:8000/execute")

def test_action(action, text):
    print(f"\n[{time.strftime('%H:%M:%S')}] 正在测试指令: {action} -> {text} ...")
    payload = {
        "action": action,
        "coords": [0, 0],
        "text": text,
        "session_id": "test_session_001"
    }
    
    try:
        # 设置 10 秒超时，因为服务端执行命令和截图需要时间
        response = requests.post(GUI_CLIENT_URL, json=payload, timeout=10)
        if response.status_code == 200:
            res_json = response.json()
            print(f"✅ 测试成功! 状态: {res_json.get('status')}")
            if res_json.get('screenshot'):
                print("📸 成功获取到截图数据 (Base64)")
        else:
            print(f"❌ 测试失败! 状态码: {response.status_code}, 详情: {response.text}")
    except requests.exceptions.Timeout:
        print("❌ 请求超时! 服务端可能卡死或网络不通。")
    except Exception as e:
        print(f"❌ 请求异常: {e}")

if __name__ == "__main__":
    commands = [
        ("window_control", "home"),
        ("window_control", "back"),
        ("window_control", "recents"),
        ("window_control", "power"),
        ("window_control", "unlock"),
        ("window_control", "wake_and_unlock"),
        ("window_control", "volume_up"),
        ("window_control", "volume_down"),
        ("window_control", "mute"),
        ("window_control", "expand_notifications"),
        ("window_control", "collapse_notifications"),
        ("call", "10086"),
        ("send_sms", "10086:测试短信")
    ]
    
    print("========================================")
    print(f"📱 Android 系统控制指令测试工具")
    print(f"🔗 目标服务器: {GUI_CLIENT_URL}")
    print("========================================")
    print("可用的测试指令:")
    for i, (action, text) in enumerate(commands):
        print(f"{i+1}. [{action}] {text}")
    print("0. 退出")
    print("a. 测试所有指令 (每个间隔3秒)")
    print("========================================")
    
    while True:
        choice = input("\n请输入要测试的指令编号: ").strip().lower()
        if choice == '0':
            print("退出测试。")
            break
        elif choice == 'a':
            for action, text in commands:
                test_action(action, text)
                time.sleep(3)
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(commands):
                    action, text = commands[idx]
                    test_action(action, text)
                else:
                    print("⚠️ 无效的编号，请重新输入。")
            except ValueError:
                print("⚠️ 请输入有效的数字编号或 'a'。")
