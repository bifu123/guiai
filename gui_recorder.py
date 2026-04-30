import json
import time
import threading
import queue
import tkinter as tk
from tkinter import simpledialog
from pynput import mouse, keyboard

def get_user_input(title, prompt, default=""):
    """使用 tkinter 弹窗获取用户输入，避免控制台焦点问题"""
    root = tk.Tk()
    root.withdraw() # 隐藏主窗口
    # 确保弹窗在最前面
    root.attributes('-topmost', True)
    result = simpledialog.askstring(title, prompt, initialvalue=default, parent=root)
    root.destroy()
    return result if result is not None else default

class GUIRecorder:
    def __init__(self):
        self.flow_list = []
        self.recording = True
        self.action_queue = queue.Queue()
        
        self.mouse_controller = mouse.Controller()
        self.drag_start_coords = None

    def on_press(self, key):
        if not self.recording:
            return False
            
        try:
            if key == keyboard.Key.esc:
                self.action_queue.put(("stop", None))
                return False
                
            elif key == keyboard.Key.f8:
                # Click
                pos = self.mouse_controller.position
                self.action_queue.put(("click", pos))
                
            elif key == keyboard.Key.f9:
                # Double click
                pos = self.mouse_controller.position
                self.action_queue.put(("double_click", pos))
                
            elif key == keyboard.Key.f10:
                # Type
                self.action_queue.put(("type", None))
                
            elif key == keyboard.Key.f11:
                # Scroll
                pos = self.mouse_controller.position
                self.action_queue.put(("scroll", pos))
                
            elif key == keyboard.Key.f12:
                # Drag
                pos = self.mouse_controller.position
                self.action_queue.put(("drag", pos))
                
        except Exception as e:
            pass

    def start(self):
        print("========== 开始录制 GUI 操作 ==========")
        print("快捷键说明:")
        print("  [F8]  录制单击 (记录当前鼠标位置)")
        print("  [F9]  录制双击 (记录当前鼠标位置)")
        print("  [F10] 录制键盘输入")
        print("  [F11] 录制滚动 (记录当前鼠标位置)")
        print("  [F12] 录制拖拽 (按第一次记录起点，按第二次记录终点)")
        print("  [Esc] 结束录制并保存")
        print("=======================================")
        
        listener = keyboard.Listener(on_press=self.on_press)
        listener.start()
        
        while self.recording:
            try:
                action_type, data = self.action_queue.get(timeout=0.5)
            except queue.Empty:
                continue
                
            if action_type == "stop":
                self.recording = False
                break
                
            elif action_type == "click":
                print(f"\n[单击] 已记录坐标 {data}")
                desc = get_user_input("输入注释", "请输入此步骤的注释:", f"在坐标 {data} 处点击左键")
                self.add_step("click", data, "", "", desc)
                print(f"-> 记录成功: {desc}")
                
            elif action_type == "double_click":
                print(f"\n[双击] 已记录坐标 {data}")
                desc = get_user_input("输入注释", "请输入此步骤的注释:", f"在坐标 {data} 处双击左键")
                self.add_step("double_click", data, "", "", desc)
                print(f"-> 记录成功: {desc}")
                
            elif action_type == "type":
                print(f"\n[输入]")
                text_to_type = get_user_input("输入文本", "请输入要让机器输入的文本:")
                if text_to_type:
                    desc = get_user_input("输入注释", "请输入此步骤的注释:", f"输入文本: '{text_to_type}'")
                    self.add_step("type", [0, 0], text_to_type, "", desc)
                    print(f"-> 记录成功: {desc}")
                else:
                    print("-> 取消输入")
                
            elif action_type == "scroll":
                print(f"\n[滚动] 已记录坐标 {data}")
                direction = get_user_input("滚动方向", "请输入滚动方向 (up/down):", "down")
                if direction not in ["up", "down"]:
                    direction = "down"
                desc = get_user_input("输入注释", "请输入此步骤的注释:", f"在坐标 {data} 处向{direction}滚动")
                self.add_step("scroll", data, direction, "", desc)
                print(f"-> 记录成功: {desc}")
                
            elif action_type == "drag":
                if self.drag_start_coords is None:
                    self.drag_start_coords = data
                    print(f"\n[拖拽-起点] 已记录起点坐标 {data}")
                    print("请将鼠标移动到终点，并再次按下 F12")
                else:
                    end_coords = data
                    print(f"\n[拖拽-终点] 已记录终点坐标 {end_coords}")
                    desc = get_user_input("输入注释", "请输入此步骤的注释:", f"从 {self.drag_start_coords} 拖拽到 {end_coords}")
                    
                    text_val = f"{int(end_coords[0])},{int(end_coords[1])}"
                    self.add_step("drag", self.drag_start_coords, text_val, "", desc)
                    self.drag_start_coords = None
                    print(f"-> 记录成功: {desc}")
                    
        listener.stop()
        
        # 退出前弹窗询问文件名
        filename = get_user_input("保存录制", "请输入要保存的 JSON 文件名:", "record_flow.json")
        if filename:
            if not filename.endswith('.json'):
                filename += '.json'
            self.save_to_json(filename)
        else:
            print("\n❌ 取消保存。")

    def add_step(self, action, coords, text, key, desc):
        step = {
            "auto": {
                "action": action,
                "coords": [int(coords[0]), int(coords[1])],
                "text": text,
                "key": key
            },
            "description": desc
        }
        self.flow_list.append(step)

    def save_to_json(self, filename="record_flow.json"):
        import os
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.flow_list, f, ensure_ascii=False, indent=4)
        abs_path = os.path.abspath(filename)
        print(f"\n✅ 录制完成！已保存 {len(self.flow_list)} 个步骤。")
        print(f"📁 文件路径: {abs_path}")

if __name__ == "__main__":
    recorder = GUIRecorder()
    recorder.start()
