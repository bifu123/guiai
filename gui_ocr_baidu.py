# encoding:utf-8
import os
import requests
import base64
import pyautogui
from io import BytesIO

class BaiduTextAnchorService:
    """基于百度OCR的精准文字定位服务，提供与 QwenDetector 相同的接口"""
    def __init__(self, client_id='nc5WIHMwSorB469QbREyf8ZY', client_secret='ANPo5ZYGed4VK94k4qSuuqk9VXhtVgLd'):
        self.client_id = client_id
        self.client_secret = client_secret
        self.request_url = "https://aip.baidubce.com/rest/2.0/ocr/v1/accurate"
        self.access_token = self._get_token()

    def _get_token(self):
        """获取百度API的access_token"""
        url = 'https://aip.baidubce.com/oauth/2.0/token'
        params = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                return response.json().get("access_token")
            else:
                print(f"获取token失败: {response.text}")
                return None
        except Exception as e:
            print(f"请求获取token发生异常: {e}")
            return None

    def get_target_coords(self, image_source, target_name, max_retries=None):
        """
        核心业务：定位目标并换算坐标 (与 ocr_service.py 接口保持一致)
        :param image_source: 可以是本地路径，也可以是 Base64 字符串
        :param target_name: 想要寻找的文字
        :param max_retries: 兼容参数，百度OCR通常不需要重试解析格式
        """
        if not self.access_token:
            print("未获取到access_token，无法进行OCR识别")
            return None

        if not image_source:
            print("错误：传入的 image_source 为空")
            return None

        # 1. 统一处理图片源
        try:
            if isinstance(image_source, str) and not image_source.startswith(('data:', 'iVBO')):
                # 说明是文件路径
                if not os.path.exists(image_source):
                    print(f"错误：找不到文件 {image_source}")
                    return None
                with open(image_source, "rb") as f:
                    img_base64 = base64.b64encode(f.read()).decode('utf-8')
            else:
                # 说明是 Base64 字符串
                img_base64 = image_source.replace('data:image/png;base64,', '')
        except Exception as e:
            print(f"处理图片源失败: {e}")
            return None

        # 2. 调用百度OCR API
        params = {
            "image": img_base64,
            "vertexes_location": "true"  # 返回文字位置信息
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        
        try:
            print(f"正在请求 百度OCR 定位: {target_name} ...")
            response = requests.post(
                self.request_url + "?access_token=" + self.access_token, 
                data=params, 
                headers=headers
            )
            result = response.json()
            
            # 3. 解析结果并查找目标
            if 'words_result' in result:
                for item in result['words_result']:
                    text = item.get('words', '')
                    location = item.get('location')
                    
                    # 模糊匹配目标文字
                    if target_name in text and location:
                        # 计算中心点坐标
                        center_x = int(location['left'] + location['width'] / 2)
                        center_y = int(location['top'] + location['height'] / 2)
                        
                        return {
                            "x": center_x,
                            "y": center_y,
                            "debug": f"百度OCR匹配到文字: '{text}', 区域: {location}"
                        }
                
                print(f"模型报告：在图片中未找到目标 '{target_name}'")
                return None
            else:
                print(f"OCR识别失败或无结果: {result}")
                return None
                
        except Exception as e:
            print(f"调用百度OCR API发生异常: {e}")
            return None

    def get_screen_text_map(self):
        """
        获取当前屏幕文字与物理坐标的映射业务 (保留原有功能)
        Returns: { "文字内容": [中心x, 中心y], ... }
        """
        text_map = {}
        if not self.access_token:
            print("未获取到access_token，无法进行OCR识别")
            return text_map

        # 1. 截取屏幕
        screenshot = pyautogui.screenshot()
        
        # 2. 将截图转换为base64
        img_byte_arr = BytesIO()
        screenshot.save(img_byte_arr, format='PNG')
        img_bytes = img_byte_arr.getvalue()
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')

        # 3. 调用百度OCR API
        params = {
            "image": img_base64,
            "vertexes_location": "true"  # 返回文字位置信息
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        
        try:
            response = requests.post(
                self.request_url + "?access_token=" + self.access_token, 
                data=params, 
                headers=headers
            )
            result = response.json()
            
            # 4. 解析结果并计算中心坐标
            if 'words_result' in result:
                for item in result['words_result']:
                    text = item.get('words', '')
                    location = item.get('location')
                    
                    if text and location:
                        # 计算中心点坐标
                        center_x = int(location['left'] + location['width'] / 2)
                        center_y = int(location['top'] + location['height'] / 2)
                        
                        # 存入映射表，如果有重复文字，保留第一个
                        if text not in text_map:
                            text_map[text] = [center_x, center_y]
            else:
                print(f"OCR识别失败或无结果: {result}")
                
        except Exception as e:
            print(f"调用百度OCR API发生异常: {e}")
            
        return text_map

# --- 完整测试入口 ---
if __name__ == "__main__":
    # 初始化检测器
    detector = BaiduTextAnchorService()
    
    # 测试图片路径（请确保目录下有 test.png）
    test_image = "test.png" 
    target = "此电脑"
    
    result = detector.get_target_coords(test_image, target)
    
    if result:
        print("\n" + "="*30)
        print(f"目标【{target}】定位成功！")
        print(f"物理像素坐标: X={result['x']}, Y={result['y']}")
        print(f"调试信息: {result['debug']}")
        print("="*30)
        print(f"现在你可以直接执行: pyautogui.click({result['x']}, {result['y']})")
    else:
        print("\n定位失败，请检查网络、API Key 或图片内容。")
