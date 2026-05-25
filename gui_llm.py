from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("LLM_API_KEY")
model = os.getenv("LLM_MODEL", "deepseek-v4-flash")
base_url = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")

if not api_key:
    raise ValueError("未找到 LLM_API_KEY 环境变量，请在 .env 文件中配置")

llm = ChatOpenAI(
    model=model,
    api_key=api_key,
    base_url=base_url
)
