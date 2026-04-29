from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="deepseek-chat",
    api_key="sk-fa809b363fd64e27b3bdcaa8194057f5",
    base_url="https://api.deepseek.com/v1"
)