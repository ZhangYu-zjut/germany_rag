"""
问题分类节点
对复杂问题进行类型分类
"""

from typing import Optional
from ...llm.client import GeminiLLMClient
from ...llm.prompts import PromptTemplates
from ...utils.logger import logger
from ..state import GraphState, update_state


class ClassifyNode:
    """
    问题分类节点
    
    功能:
    1. 对复杂问题进行分类
    2. 识别问题类型(变化类/总结类/对比类/事实查询/趋势分析)
    3. 为后续处理提供指导
    
    输出:
    - question_type: 问题类型
    """
    
    # 支持的问题类型
    QUESTION_TYPES = [
        "变化类",  # 询问某个议题在时间上的变化、演变
        "总结类",  # 要求总结某个时期、党派或议员的观点
        "对比类",  # 对比不同党派、时期或议员的立场
        "事实查询",  # 询问具体的事实、数据、引语等
        "趋势分析",  # 分析某个议题的发展趋势
    ]
    
    def __init__(self, llm_client: GeminiLLMClient = None):
        """
        初始化问题分类节点
        
        Args:
            llm_client: LLM客户端,如果为None则自动创建
        """
        self.llm = llm_client or GeminiLLMClient()
        self.prompts = PromptTemplates()
        
    def __call__(self, state: GraphState) -> GraphState:
        """
        执行问题分类
        
        Args:
            state: 当前状态
            
        Returns:
            更新后的状态
        """
        question = state["question"]
        intent = state.get("intent", "complex")
        
        logger.info(f"[ClassifyNode] 开始分类问题: {question}")
        
        # 如果是简单问题,跳过分类
        if intent == "simple":
            logger.info("[ClassifyNode] 简单问题,跳过分类")
            return update_state(
                state,
                question_type="事实查询",
                current_node="classify",
                next_node="extract"
            )
        
        try:
            # 构建Prompt
            prompt = self.prompts.format_classification_prompt(question)
            
            # 调用LLM
            response = self.llm.invoke(prompt)
            
            logger.debug(f"[ClassifyNode] LLM响应: {response[:200]}...")
            
            # 解析响应
            question_type = self._parse_response(response)
            
            logger.info(f"[ClassifyNode] 分类结果: {question_type}")
            
            # 更新状态
            return update_state(
                state,
                question_type=question_type,
                current_node="classify",
                next_node="extract"
            )
            
        except Exception as e:
            logger.error(f"[ClassifyNode] 问题分类失败: {str(e)}")
            return update_state(
                state,
                error=f"问题分类失败: {str(e)}",
                question_type="事实查询",  # 默认类型
                current_node="classify",
                next_node="extract"  # 继续流程
            )
    
    def _parse_response(self, response: str) -> str:
        """
        解析LLM响应,提取问题类型
        
        Args:
            response: LLM响应文本
            
        Returns:
            问题类型
        """
        # 查找响应中的问题类型
        for qtype in self.QUESTION_TYPES:
            if qtype in response:
                return qtype
        
        # 使用关键词匹配
        if "变化" in response or "演变" in response or "发展" in response:
            return "变化类"
        elif "总结" in response or "归纳" in response or "观点" in response:
            return "总结类"
        elif "对比" in response or "比较" in response or "差异" in response:
            return "对比类"
        elif "趋势" in response or "走向" in response:
            return "趋势分析"
        else:
            return "事实查询"  # 默认类型


if __name__ == "__main__":
    # 测试问题分类节点
    from ..state import create_initial_state, update_state
    
    # 测试变化类问题
    question1 = "在2015年到2018年期间,德国联邦议会中不同党派在难民家庭团聚问题上的讨论发生了怎样的变化?"
    state1 = create_initial_state(question1)
    state1 = update_state(state1, intent="complex")
    
    node = ClassifyNode()
    result1 = node(state1)
    
    print("=== 变化类问题测试 ===")
    print(f"问题: {question1}")
    print(f"分类: {result1['question_type']}")
    print(f"下一节点: {result1['next_node']}")
    
    # 测试对比类问题
    question2 = "CDU/CSU和SPD在2019年对气候保护政策的立场有什么不同?"
    state2 = create_initial_state(question2)
    state2 = update_state(state2, intent="complex")
    
    result2 = node(state2)
    
    print("\n=== 对比类问题测试 ===")
    print(f"问题: {question2}")
    print(f"分类: {result2['question_type']}")
    print(f"下一节点: {result2['next_node']}")
    
    # 测试总结类问题
    question3 = "请总结Merkel在2019年关于欧盟一体化的主要观点"
    state3 = create_initial_state(question3)
    state3 = update_state(state3, intent="complex")
    
    result3 = node(state3)
    
    print("\n=== 总结类问题测试 ===")
    print(f"问题: {question3}")
    print(f"分类: {result3['question_type']}")
    print(f"下一节点: {result3['next_node']}")
