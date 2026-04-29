# gui_ocr.py
import os
import pyautogui
from io import BytesIO
from PIL import Image
# 如果没有安装，请执行: pip install paddlepaddle paddleocr
from paddleocr import PaddleOCR

class TextAnchorService:
    """负责精准文字定位的职责端"""
    def __init__(self):
        # 首次初始化会下载模型，建议开启手机热点或确保网络通畅
        self.ocr_engine = PaddleOCR(use_angle_cls=True, lang="ch")

    def get_screen_text_map(self):
        """
        获取当前屏幕文字与物理坐标的映射业务
        Returns: { "文字内容": [中心x, 中心y], ... }
        """
        screenshot = pyautogui.screenshot()
        # 将 PIL Image 转为字节流供 Paddle 使用
        img_byte_arr = BytesIO()
        screenshot.save(img_byte_arr, format='PNG')
        img_bytes = img_byte_arr.getvalue()
        
        # 执行 OCR 识别
        result = self.ocr_engine.ocr(img_bytes)
        
        text_map = {}
        if not result or not result[0]:
            return text_map

        for line in result[0]:
            coords = line[0]  # 四角坐标: [左上, 右上, 右下, 左下]
            text = line[1][0] # 识别到的文字
            
            # 计算文字中心点的业务逻辑
            center_x = int((coords[0][0] + coords[2][0]) / 2)
            center_y = int((coords[0][1] + coords[2][1]) / 2)
            
            # 存入映射表，如果有重复文字，保留第一个（通常桌面图标从左往右扫描）
            if text not in text_map:
                text_map[text] = [center_x, center_y]
        
        return text_map

# 调试代码
if __name__ == "__main__":
    service = TextAnchorService()
    print("正在扫描屏幕文字业务...")
    m = service.get_screen_text_map()
    for k, v in m.items():
        print(f"找到文字: {k} -> 坐标: {v}")
