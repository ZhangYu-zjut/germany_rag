"""
增强版异常处理节点
支持多种异常类型的细粒度处理
"""

from ...llm.prompts import PromptTemplates
from ...llm.prompts_fallback import FallbackPrompts, GuidanceGenerator
from ...utils.logger import logger
from ..state import GraphState, update_state


class EnhancedExceptionNode:
    """
    增强版异常处理节点
    
    支持的异常类型:
    1. NO_MATERIAL - 未找到材料
    2. LLM_ERROR - LLM调用失败
    3. RETRIEVAL_ERROR - 检索失败
    4. PARSING_ERROR - 解析失败
    5. MILVUS_ERROR - Milvus连接失败
    6. UNKNOWN - 未知错误
    
    注意: 以下异常已在IntentNode处理:
    - 系统功能查询
    - 不相关问题
    - 信息不足
    - 超出范围
    """
    
    def __init__(self):
        """初始化增强版异常处理节点"""
        self.prompts = PromptTemplates()
        self.fallback_prompts = FallbackPrompts()
        
    def __call__(self, state: GraphState) -> GraphState:
        """
        处理异常
        
        Args:
            state: 当前状态
            
        Returns:
            更新后的状态
        """
        question = state["question"]
        error = state.get("error")
        error_type = state.get("error_type", "UNKNOWN")
        
        logger.warning(f"[EnhancedExceptionNode] 处理异常 - 类型: {error_type}")
        logger.warning(f"[EnhancedExceptionNode] 问题: {question}")
        
        if error:
            logger.error(f"[EnhancedExceptionNode] 错误详情: {error}")
        
        # 根据异常类型调用不同的处理方法
        if error_type == "NO_MATERIAL":
            final_answer = self._handle_no_material(state)
        elif error_type == "LLM_ERROR":
            final_answer = self._handle_llm_error(state)
        elif error_type == "RETRIEVAL_ERROR":
            final_answer = self._handle_retrieval_error(state)
        elif error_type == "PARSING_ERROR":
            final_answer = self._handle_parsing_error(state)
        elif error_type == "MILVUS_ERROR":
            final_answer = self._handle_milvus_error(state)
        else:
            final_answer = self._handle_unknown_error(state)
        
        # 更新状态
        return update_state(
            state,
            final_answer=final_answer,
            current_node="exception",
            next_node="end"
        )
    
    def _handle_no_material(self, state: GraphState) -> str:
        """
        处理未找到材料
        
        根据问题的参数，提供针对性的建议
        """
        question = state["question"]
        parameters = state.get("parameters", {})
        
        # 获取参数
        time_range = parameters.get("time_range", {})
        parties = parameters.get("parties", [])
        speakers = parameters.get("speakers", [])
        topics = parameters.get("topics", [])
        
        # 构建未找到材料的提示
        answer = f"""抱歉，未能在数据库中找到与您问题相关的演讲记录。

【您的问题】
{question}

【提取的参数】"""
        
        if time_range:
            start = time_range.get("start_year")
            end = time_range.get("end_year")
            if start and end:
                answer += f"\n- 时间范围: {start}年 至 {end}年"
            elif start:
                answer += f"\n- 时间: {start}年"
        
        if parties:
            answer += f"\n- 党派: {', '.join(parties)}"
        
        if speakers:
            answer += f"\n- 议员: {', '.join(speakers)}"
        
        if topics:
            answer += f"\n- 主题: {', '.join(topics)}"
        
        # 提供建议
        answer += "\n\n【可能的原因】\n"
        answer += "1. 您指定的时间范围内没有相关讨论\n"
        answer += "2. 您指定的党派或议员没有在该时期发言\n"
        answer += "3. 主题关键词可能与实际讨论用语不匹配\n"
        
        answer += "\n【建议】\n"
        answer += "1. 尝试扩大时间范围\n"
        answer += "2. 使用更通用的主题关键词\n"
        answer += "3. 去掉一些限制条件，如不指定特定党派\n"
        
        answer += "\n【示例问题】\n"
        answer += '- "2015-2020年德国议会关于气候保护的主要讨论是什么？"\n'
        answer += '- "CDU/CSU在2019年对数字化政策的立场？"\n'
        
        return answer
    
    def _handle_llm_error(self, state: GraphState) -> str:
        """处理LLM调用失败"""
        question = state["question"]
        error = state.get("error", "LLM调用失败")
        
        answer = f"""抱歉，在处理您的问题时，语言模型服务暂时不可用。

【您的问题】
{question}

【技术详情】
{error}

【建议】
1. 请稍后重试（可能是网络问题或服务暂时中断）
2. 如果问题持续，请联系系统管理员
3. 您可以尝试简化问题后重试

我们会尽快恢复服务。
"""
        return answer
    
    def _handle_retrieval_error(self, state: GraphState) -> str:
        """处理检索失败"""
        question = state["question"]
        error = state.get("error", "检索失败")
        
        answer = f"""抱歉，在检索相关材料时遇到了问题。

【您的问题】
{question}

【技术详情】
{error}

【建议】
1. 请稍后重试
2. 如果问题持续，可能是数据库连接问题
3. 您可以尝试更简单的问题

我们正在解决此问题。
"""
        return answer
    
    def _handle_parsing_error(self, state: GraphState) -> str:
        """处理解析失败"""
        question = state["question"]
        error = state.get("error", "解析失败")
        
        answer = f"""抱歉，在理解您的问题时遇到了困难。

【您的问题】
{question}

【技术详情】
{error}

【可能的原因】
1. 问题表述可能过于复杂或模糊
2. 包含了系统难以理解的表达
3. 缺少关键信息（如时间、主题等）

【建议】
请尝试：
1. 使用更简洁明确的表述
2. 确保包含时间信息（年份或时间段）
3. 明确指出您关注的主题或议题

【示例问题】
- "2019年德国议会讨论了哪些主要议题？"
- "CDU/CSU在2020年对气候保护的立场是什么？"
- "在2015-2018年，不同党派在难民政策上的立场有何变化？"
"""
        return answer
    
    def _handle_milvus_error(self, state: GraphState) -> str:
        """处理Milvus连接失败"""
        question = state["question"]
        error = state.get("error", "向量数据库连接失败")
        
        answer = f"""抱歉，向量数据库暂时不可用。

【您的问题】
{question}

【技术详情】
{error}

【建议】
1. 请稍后重试
2. 如果问题持续，请联系系统管理员
3. 可能是数据库服务正在维护

我们会尽快恢复服务。
"""
        return answer
    
    def _handle_unknown_error(self, state: GraphState) -> str:
        """处理未知错误"""
        question = state["question"]
        error = state.get("error", "未知错误")
        
        answer = f"""抱歉，处理您的问题时遇到了意外问题。

【您的问题】
{question}

【技术详情】
{error}

【建议】
1. 请尝试重新表述您的问题
2. 确保问题表述清晰完整
3. 可以尝试将复杂问题拆分为多个简单问题
4. 如果问题持续，请联系系统管理员

【示例问题】
- "2019年德国联邦议院讨论了哪些主要议题？"
- "CDU/CSU在2020年对气候保护的立场是什么？"
- "请总结Merkel在2019年关于欧盟一体化的主要观点"

我们会尽快修复此问题。
"""
        return answer


# 为了保持向后兼容，创建一个别名
ExceptionNode = EnhancedExceptionNode


if __name__ == "__main__":
    # 测试增强版异常处理节点
    from ..state import create_initial_state
    
    print("=== 增强版ExceptionNode测试 ===\n")
    
    # 测试1: 未找到材料
    print("【测试1: 未找到材料】")
    question = "1900年德国议会讨论了什么？"
    state = create_initial_state(question)
    state = update_state(
        state, 
        error="未找到相关材料",
        error_type="NO_MATERIAL",
        parameters={
            "time_range": {"start_year": "1900"},
            "topics": ["议会讨论"]
        }
    )
    
    node = EnhancedExceptionNode()
    result = node(state)
    print(f"问题: {question}")
    print(f"回答预览: {result['final_answer'][:200]}...")
    print()
    
    # 测试2: LLM错误
    print("【测试2: LLM错误】")
    question = "2019年CDU的立场是什么？"
    state = create_initial_state(question)
    state = update_state(
        state,
        error="Gemini API rate limit exceeded",
        error_type="LLM_ERROR"
    )
    
    result = node(state)
    print(f"问题: {question}")
    print(f"回答预览: {result['final_answer'][:200]}...")
    print()
    
    # 测试3: 解析错误
    print("【测试3: 解析错误】")
    question = "那个那个，就是那个..."
    state = create_initial_state(question)
    state = update_state(
        state,
        error="无法提取有效参数",
        error_type="PARSING_ERROR"
    )
    
    result = node(state)
    print(f"问题: {question}")
    print(f"回答预览: {result['final_answer'][:200]}...")
    print()
    
    print("测试完成！")

