from langchain_openai import ChatOpenAI  # <-- 关键改变：导入 ChatOpenAI

import os  # 导入 Python 内置的 'os' 模块来访问环境变量
from dotenv import load_dotenv  # <-- 这是你问的语句

load_dotenv()
# --- 从你的第三方 API 网站获取这些信息 ---
THIRD_PARTY_BASE_URL = "https://api.evolink.ai/v1" # 替换成你的
THIRD_PARTY_API_KEY = os.getenv("OPENAI_API_KEY")
THIRD_PARTY_MODEL_NAME = "gemini-2.5-pro"                        # 确认第三方使用的模型名

# --- 修改 LLM 初始化 ---
llm = ChatOpenAI(
    model=THIRD_PARTY_MODEL_NAME,
    api_key=THIRD_PARTY_API_KEY,
    base_url=THIRD_PARTY_BASE_URL,
    temperature=0
)
print(llm.model_name)
res = llm.invoke("What is LangChain?")
print(res)
# ... 后续的 rag_prompt, format_docs, rag_chain 等代码...
# ... 完全保持不变，它们可以正常工作！...