"""
LangGraph状态定义
定义工作流中的状态数据结构
"""

from typing import TypedDict, List, Dict, Optional, Literal


class GraphState(TypedDict):
    """
    工作流状态定义
    
    包含:
    - 原始问题和处理后的问题
    - 问题分类和参数
    - 检索结果和中间答案
    - 最终答案和错误信息
    """
    
    # ========== 问题相关 ==========
    question: str  # 原始用户问题
    cleaned_question: Optional[str]  # 清洗后的问题
    
    # ========== 意图和分类 ==========
    intent: Optional[Literal["simple", "complex"]]  # 意图: 简单/复杂
    question_type: Optional[str]  # 问题类型: 变化类/总结类/对比类/事实查询/趋势分析
    complexity_analysis: Optional[str]  # 复杂度分析结果
    
    # ========== 参数提取 ==========
    parameters: Optional[Dict]  # 提取的参数
    # parameters结构:
    # {
    #     "time_range": {"start_year": "2015", "end_year": "2018", "specific_years": ["2015", "2016"]},
    #     "parties": ["CDU/CSU", "SPD"],
    #     "speakers": ["Merkel", "Schulz"],
    #     "topics": ["难民", "家庭团聚"],
    #     "keywords": ["Familiennachzug", "Flüchtlinge"]
    # }
    
    # ========== 问题拆解 ==========
    is_decomposed: bool  # 是否需要拆解
    sub_questions: Optional[List[str]]  # 拆解后的子问题列表

    # ========== Query扩展（新架构） ==========
    expanded_queries_map: Optional[Dict[str, List[str]]]  # Query扩展映射
    # expanded_queries_map结构:
    # {
    #     "子问题1": ["扩展查询1", "扩展查询2", "扩展查询3", ...],
    #     "子问题2": ["扩展查询1", "扩展查询2", ...]
    # }
    original_question: Optional[str]  # 原始用户问题（用于Query扩展）
    extracted_params: Optional[Dict]  # 提取的参数（用于Query扩展）
    # extracted_params结构:
    # {
    #     "year": ["2015"],
    #     "group": ["CDU/CSU"],
    #     "topic": ["难民政策"]
    # }

    # ========== 检索和答案 ==========
    retrieval_results: Optional[List[Dict]]  # 检索结果
    # retrieval_results结构:
    # [
    #     {
    #         "question": "子问题1",
    #         "chunks": [{"text": "...", "metadata": {...}, "score": 0.95}],
    #         "answer": "子答案1"
    #     }
    # ]
    
    reranked_results: Optional[List[Dict]]  # 重排序后的检索结果
    # reranked_results结构:
    # [
    #     {
    #         "question": "子问题1", 
    #         "chunks": [{"text": "...", "metadata": {...}, "score": 0.95, "rerank_score": 0.92, "rerank_position": 1}],
    #         "answer": "子答案1",
    #         "rerank_scores": [0.92, 0.88, 0.85],
    #         "original_count": 20,
    #         "reranked_count": 10
    #     }
    # ]
    
    sub_answers: Optional[List[Dict]]  # 子问题的答案
    # sub_answers结构:
    # [
    #     {"question": "子问题1", "answer": "答案1", "sources": [...]},
    #     {"question": "子问题2", "answer": "答案2", "sources": [...]}
    # ]
    
    final_answer: Optional[str]  # 最终答案
    
    # ========== 元数据和错误处理 ==========
    no_material_found: bool  # 是否未找到材料
    error: Optional[str]  # 错误信息
    metadata: Optional[Dict]  # 其他元数据
    
    # ========== 流程控制 ==========
    current_node: Optional[str]  # 当前节点名称
    next_node: Optional[str]  # 下一个节点名称

    # ========== 深度分析模式 ==========
    deep_thinking_mode: bool  # 是否启用深度分析模式
    # 深度模式特性:
    # - 强制启用知识图谱扩展（tag级别）
    # - 生成更详细的分析报告
    # - 显示推理过程
    # - 预计耗时: 3-5分钟

    kg_expansion_info: Optional[Dict]  # 知识图谱扩展信息
    # kg_expansion_info结构:
    # {
    #     "triggered": True,
    #     "level": "tag",
    #     "score": 3,
    #     "reasons": ["主题匹配: Flüchtlingspolitik"],
    #     "expanded_queries": ["AfD Georgien Visum 2018", ...],
    #     "matched_tags": ["Georgien", "Visum", ...]
    # }

    reasoning_steps: Optional[List[str]]  # 推理步骤（深度模式显示）
    # reasoning_steps结构:
    # [
    #     "1. 识别问题类型: 单年单党派观点查询",
    #     "2. 提取参数: 年份=2018, 党派=AfD, 主题=难民政策",
    #     "3. 知识图谱扩展: 触发Flüchtlingspolitik主题，扩展22个查询",
    #     "4. 检索结果: 找到150个相关文档",
    #     "5. 重排序: 筛选出15个最相关文档"
    # ]


# ========== 辅助函数 ==========

def create_initial_state(question: str, deep_thinking_mode: bool = False) -> GraphState:
    """
    创建初始状态

    Args:
        question: 用户问题
        deep_thinking_mode: 是否启用深度分析模式（默认False）
            - 深度模式会强制启用知识图谱扩展
            - 生成更详细的分析报告
            - 预计耗时: 3-5分钟

    Returns:
        初始化的GraphState
    """
    return GraphState(
        question=question,
        cleaned_question=None,
        intent=None,
        question_type=None,
        complexity_analysis=None,
        parameters=None,
        is_decomposed=False,
        sub_questions=None,
        retrieval_results=None,
        reranked_results=None,
        sub_answers=None,
        final_answer=None,
        no_material_found=False,
        error=None,
        metadata={},
        current_node="start",
        next_node=None,
        # 深度分析模式
        deep_thinking_mode=deep_thinking_mode,
        kg_expansion_info=None,
        reasoning_steps=[],
    )


def update_state(state: GraphState, **kwargs) -> GraphState:
    """
    更新状态
    
    Args:
        state: 当前状态
        **kwargs: 要更新的字段
        
    Returns:
        更新后的状态
    """
    new_state = state.copy()
    new_state.update(kwargs)
    return new_state


if __name__ == "__main__":
    # 测试状态创建
    state = create_initial_state("在2015年到2018年期间,德国联邦议会中不同党派在难民家庭团聚问题上的讨论发生了怎样的变化?")
    
    print("初始状态:")
    print(f"问题: {state['question']}")
    print(f"当前节点: {state['current_node']}")
    print(f"是否拆解: {state['is_decomposed']}")
    
    # 测试状态更新
    state = update_state(
        state,
        intent="complex",
        question_type="变化类",
        current_node="classify"
    )
    
    print("\n更新后状态:")
    print(f"意图: {state['intent']}")
    print(f"问题类型: {state['question_type']}")
    print(f"当前节点: {state['current_node']}")
