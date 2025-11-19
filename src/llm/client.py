"""
LLM客户端模块
封装Gemini 2.5 Pro的调用
"""

from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from typing import List, Dict, Any, Optional
from src.config import settings
from src.utils import logger


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
        self.max_tokens = max_tokens
        
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
            default_headers={"Accept-Encoding": "identity"}  # 禁用压缩避免zstandard问题
        )
        
        logger.info(
            f"初始化LLM客户端: model={self.model_name}, "
            f"temperature={self.temperature}"
        )
    
    def invoke(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        调用LLM获取回复（简化版，直接传字符串）
        
        Args:
            prompt: 用户提示词（字符串）
            system_prompt: 系统提示词(可选)
        
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
        
        try:
            # 调用LLM
            response = self.llm.invoke(chat_messages)
            
            # 提取回复内容
            reply = response.content
            
            logger.debug(f"LLM调用成功,回复长度: {len(reply)} 字符")
            
            return reply
            
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            raise
    
    def invoke_with_messages(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None
    ) -> str:
        """
        调用LLM获取回复（多轮对话版本）
        
        Args:
            messages: 消息列表,每条消息包含role和content
            system_prompt: 系统提示词(可选)
        
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
        
        try:
            # 调用LLM
            response = self.llm.invoke(chat_messages)
            
            # 提取回复内容
            reply = response.content
            
            logger.debug(f"LLM调用成功,回复长度: {len(reply)} 字符")
            
            return reply
            
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            raise
    
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
