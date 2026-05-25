# 怎样更换视觉模型 (VL) 和 OCR 模型

本项目将视觉模型（用于理解屏幕内容和判断任务状态）和 OCR 模型（用于精准定位屏幕上的文字坐标）进行了模块化解耦。所有的 API Key 和服务地址统一由 `.env` 文件管理。

## 1. 更换视觉模型 (VL)

视觉模型的核心职责是接收文本 Prompt 和屏幕截图，输出对屏幕的理解或判断结果。

### 1.1 配置文件位置
视觉模型的相关代码位于 `gui_vl.py` 中。

### 1.2 当前支持的模型
目前 `gui_vl.py` 中已经实现了以下模型的调用：
- **Ollama Qwen3-VL (本地部署)**: 函数名为 `ollama_qwen3_vl`
- **智谱 GLM-4V-Flash (云端 API)**: 函数名为 `glm_4_6v_flash`

### 1.3 切换步骤
1. 打开 `gui_vl.py` 文件。
2. 滚动到文件末尾，找到以下代码：
   ```python
   # 统一的视觉模型接口
   vlm = ollama_qwen3_vl
   ```
3. 将 `vlm` 赋值为您想要使用的模型函数。例如，要切换到智谱模型，修改为：
   ```python
   vlm = glm_4_6v_flash
   ```
4. 确保在 `.env` 文件中配置了相应的环境变量：
   - 如果使用 Ollama，配置 `OLLAMA_HOST`（例如：`OLLAMA_HOST=http://192.168.68.28:11434`）。
   - 如果使用智谱，配置 `ZHIPU_API_KEY`。

### 1.4 添加新的视觉模型
如果您想接入其他视觉模型（如 GPT-4o, Claude 3.5 Sonnet 等）：
1. 在 `gui_vl.py` 中新增一个函数，例如 `def my_new_vl_model(text, image_base64=None):`。
2. 在函数内部实现调用新模型 API 的逻辑。注意处理 `image_base64` 参数（可能需要去除 `data:image/png;base64,` 前缀）。
3. 确保函数返回模型输出的纯文本字符串。
4. 在 `.env` 中添加所需的 API Key，并在函数中使用 `os.getenv()` 读取。
5. 将文件末尾的 `vlm` 变量指向您的新函数。

---

## 2. 更换 OCR 模型

OCR 模型的核心职责是接收屏幕截图和目标文字，返回该文字在截图中的物理像素坐标 `(x, y)`。

### 2.1 配置文件位置
OCR 模型的相关代码位于 `gui_ocr.py` 中。

### 2.2 当前支持的模型
目前 `gui_ocr.py` 中已经实现了以下模型的调用：
- **百度 OCR (免费额度，精准度高)**: 类名为 `BaiduTextAnchorService`
- **阿里千问 VL-OCR (云端 API)**: 类名为 `QwenDetector`
- **Ollama Qwen3-VL (本地部署)**: 类名为 `OllamaDetector`

### 2.3 切换步骤
1. 打开 `gui_ocr.py` 文件。
2. 滚动到文件末尾，找到以下代码：
   ```python
   # ==========================================
   # 全局 OCR 实例配置
   # 以后更换 OCR 模型时，只需要在这里修改实例化的类即可
   # ==========================================
   ocr = BaiduTextAnchorService()
   ```
3. 将 `ocr` 实例化为您想要使用的类。例如，要切换到千问 OCR，修改为：
   ```python
   ocr = QwenDetector()
   ```
4. 确保在 `.env` 文件中配置了相应的环境变量：
   - 如果使用百度 OCR，配置 `BAIDU_OCR_CLIENT_ID` 和 `BAIDU_OCR_CLIENT_SECRET`。
   - 如果使用千问 OCR，配置 `QWEN_OCR_API_KEY`。
   - 如果使用 Ollama，配置 `OLLAMA_HOST`（例如：`OLLAMA_HOST=http://192.168.68.28:11434`）。

### 2.4 添加新的 OCR 模型
如果您想接入其他 OCR 服务：
1. 在 `gui_ocr.py` 中新增一个类，例如 `class MyNewOCRDetector:`。
2. 在类中实现 `get_target_coords(self, image_source, target_name, max_retries=None)` 方法。
3. 该方法必须返回一个字典，格式为 `{"x": 整数, "y": 整数, "debug": "调试信息"}`，如果未找到目标则返回 `None`。
4. 在 `.env` 中添加所需的 API Key，并在类的 `__init__` 方法中使用 `os.getenv()` 读取。
5. 将文件末尾的 `ocr` 变量实例化为您的新类。
