"""
LLM客户端模块
封装Gemini 2.5 Pro的调用
支持速率限制保护，防止API被限流返回404
"""

import time
import threading
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from typing import List, Dict, Any, Optional
from src.config import settings
from src.utils import logger

# 全局速率限制器（所有客户端实例共享）
class RateLimiter:
    """API请求速率限制器，防止触发Evolink速率限制"""

    def __init__(self, min_interval: float = 1.5):
        """
        初始化速率限制器

        Args:
            min_interval: 请求之间的最小间隔（秒）
        """
        self.min_interval = min_interval
        self.last_request_time = 0.0
        self._lock = threading.Lock()

    def wait_if_needed(self):
        """在发送请求前调用，必要时等待以遵守速率限制"""
        with self._lock:
            current_time = time.time()
            elapsed = current_time - self.last_request_time

            if elapsed < self.min_interval:
                wait_time = self.min_interval - elapsed
                logger.debug(f"[RateLimiter] 等待 {wait_time:.2f}s 以避免速率限制")
                time.sleep(wait_time)

            self.last_request_time = time.time()

# 全局单例
_rate_limiter = RateLimiter(min_interval=1.5)  # 每1.5秒最多1个请求


class GeminiLLMClient:
    """
    Gemini LLM客户端
    
    功能:
    1. 封装Gemini 2.5 Pro调用
    2. 支持系统提示词
    3. 支持流式输出
    4. 错误处理和重试
    """
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None
    ):
        """
        初始化LLM客户端
        
        Args:
            model_name: 模型名称,默认从配置读取
            temperature: 温度参数,控制随机性
            max_tokens: 最大token数
        """
        self.model_name = model_name or settings.third_party_model_name
        self.temperature = temperature
        # 如果未指定max_tokens，使用配置中的默认值（防止输出截断）
        self.max_tokens = max_tokens or settings.llm_max_tokens
        
        # 检查 API key 是否配置
        if not settings.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY 未配置。请设置环境变量 OPENAI_API_KEY 或在 .env 文件中配置。\n"
                "注意：如果只测试 embedding，可以跳过 LLM 相关测试。"
            )
        
        # 初始化ChatOpenAI(兼容Gemini API)
        self.llm = ChatOpenAI(
            model=self.model_name,
            api_key=settings.openai_api_key,
            base_url=settings.third_party_base_url,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            default_headers={"Accept-Encoding": "identity"},  # 禁用压缩避免zstandard问题
            timeout=120,  # 2分钟超时，防止无限等待
            max_retries=2  # 失败时重试2次
        )
        
        logger.info(
            f"初始化LLM客户端: model={self.model_name}, "
            f"temperature={self.temperature}"
        )
    
    def invoke(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_retries: int = 3
    ) -> str:
        """
        调用LLM获取回复（简化版，直接传字符串）

        Args:
            prompt: 用户提示词（字符串）
            system_prompt: 系统提示词(可选)
            max_retries: 遇到速率限制时的最大重试次数

        Returns:
            LLM的回复文本
        """
        # 构建消息列表
        chat_messages = []

        # 添加系统提示词
        if system_prompt:
            chat_messages.append(SystemMessage(content=system_prompt))

        # 添加用户消息
        chat_messages.append(HumanMessage(content=prompt))

        # 带重试的调用逻辑
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                # 应用速率限制
                _rate_limiter.wait_if_needed()

                # 调用LLM
                response = self.llm.invoke(chat_messages)

                # 提取回复内容
                reply = response.content

                logger.debug(f"LLM调用成功,回复长度: {len(reply)} 字符")

                return reply

            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                # 检查是否是速率限制相关的错误（404或rate limit）
                is_rate_limit = "404" in error_str or "rate" in error_str or "limit" in error_str

                if is_rate_limit and attempt < max_retries:
                    # 指数退避：2^attempt * 2秒
                    wait_time = (2 ** attempt) * 2
                    logger.warning(
                        f"[RateLimiter] 检测到速率限制错误 (attempt {attempt + 1}/{max_retries + 1}), "
                        f"等待 {wait_time}s 后重试: {e}"
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"LLM调用失败: {e}")
                    raise

        # 所有重试都失败
        logger.error(f"LLM调用在 {max_retries + 1} 次尝试后仍然失败: {last_error}")
        raise last_error
    
    def invoke_with_messages(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        max_retries: int = 3
    ) -> str:
        """
        调用LLM获取回复（多轮对话版本）

        Args:
            messages: 消息列表,每条消息包含role和content
            system_prompt: 系统提示词(可选)
            max_retries: 遇到速率限制时的最大重试次数

        Returns:
            LLM的回复文本
        """
        # 构建消息列表
        chat_messages = []

        # 添加系统提示词
        if system_prompt:
            chat_messages.append(SystemMessage(content=system_prompt))

        # 添加用户消息
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')

            if role == 'system':
                chat_messages.append(SystemMessage(content=content))
            elif role == 'user':
                chat_messages.append(HumanMessage(content=content))
            elif role == 'assistant':
                chat_messages.append(AIMessage(content=content))

        # 带重试的调用逻辑
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                # 应用速率限制
                _rate_limiter.wait_if_needed()

                # 调用LLM
                response = self.llm.invoke(chat_messages)

                # 提取回复内容
                reply = response.content

                logger.debug(f"LLM调用成功,回复长度: {len(reply)} 字符")

                return reply

            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                # 检查是否是速率限制相关的错误（404或rate limit）
                is_rate_limit = "404" in error_str or "rate" in error_str or "limit" in error_str

                if is_rate_limit and attempt < max_retries:
                    # 指数退避：2^attempt * 2秒
                    wait_time = (2 ** attempt) * 2
                    logger.warning(
                        f"[RateLimiter] 检测到速率限制错误 (attempt {attempt + 1}/{max_retries + 1}), "
                        f"等待 {wait_time}s 后重试: {e}"
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"LLM调用失败: {e}")
                    raise

        # 所有重试都失败
        logger.error(f"LLM调用在 {max_retries + 1} 次尝试后仍然失败: {last_error}")
        raise last_error
    
    def invoke_with_prompt(
        self,
        user_message: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        简化调用接口:单条用户消息（与invoke相同，保留for向后兼容）
        
        Args:
            user_message: 用户消息
            system_prompt: 系统提示词(可选)
        
        Returns:
            LLM的回复文本
        """
        return self.invoke(user_message, system_prompt)
    
    def stream_invoke(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ):
        """
        流式调用LLM（字符串版本）
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词(可选)
        
        Yields:
            LLM的流式回复片段
        """
        # 构建消息列表
        chat_messages = []
        
        if system_prompt:
            chat_messages.append(SystemMessage(content=system_prompt))
        
        chat_messages.append(HumanMessage(content=prompt))
        
        try:
            # 流式调用
            for chunk in self.llm.stream(chat_messages):
                if hasattr(chunk, 'content'):
                    yield chunk.content
            
            logger.debug("流式LLM调用完成")
            
        except Exception as e:
            logger.error(f"流式LLM调用失败: {e}")
            raise


if __name__ == "__main__":
    # 测试LLM客户端
    client = GeminiLLMClient()
    
    # 测试1: 简单调用
    print("\n=== 测试1: 简单调用 ===")
    response = client.invoke_with_prompt(
        user_message="什么是LangChain?请用一句话回答。",
        system_prompt="你是一个helpful的AI助手。"
    )
    print(f"回复: {response}")
    
    # 测试2: 多轮对话
    print("\n=== 测试2: 多轮对话 ===")
    messages = [
        {'role': 'user', 'content': '德国有哪些主要政党?'},
        {'role': 'assistant', 'content': '德国的主要政党包括基民盟(CDU)、社民党(SPD)、绿党等。'},
        {'role': 'user', 'content': '请详细介绍一下社民党。'}
    ]
    response = client.invoke_with_messages(
        messages=messages,
        system_prompt="你是一个了解德国政治的专家。"
    )
    print(f"回复: {response}")
    
    # 测试3: 流式输出
    print("\n=== 测试3: 流式输出 ===")
    print("回复: ", end="", flush=True)
    for chunk in client.stream_invoke(
        prompt='用一句话介绍德国联邦议院。'
    ):
        print(chunk, end="", flush=True)
    print()
