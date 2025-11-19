"""
LangGraph工作流编排
实现CoA (Chain of Agents) 完整流程
"""

from typing import Literal
from langgraph.graph import StateGraph, END
from .state import GraphState, create_initial_state
from .nodes import (
    ClassifyNode,
    RetrieveNode,
    ReRankNode,
)
# 使用增强版节点
from .nodes.intent_enhanced import EnhancedIntentNode as IntentNode
from .nodes.exception_enhanced import EnhancedExceptionNode as ExceptionNode
from .nodes.decompose_enhanced import EnhancedDecomposeNode as DecomposeNode
# 【Phase 2】使用两阶段增量式总结节点V2（替换原有的EnhancedSummarizeNode）
from .nodes.summarize_incremental_v2 import IncrementalSummarizeNodeV2 as SummarizeNode
from .nodes.extract_enhanced import EnhancedExtractNode as ExtractNode
from ..utils.logger import logger
from ..utils.performance_monitor import get_performance_monitor, performance_timer


class QuestionAnswerWorkflow:
    """
    问答工作流（增强版）
    
    【新增功能】
    - 问题合法性检查（元问题、不相关、信息不足、超出范围）
    - 中德双语支持
    - 细粒度异常处理
    
    流程:
    1. Intent - 意图判断 (包含合法性检查 + 简单/复杂判断)
       - 特殊情况直接返回（元问题、不相关等）
       - 正常问题继续后续流程
    2. Classify - 问题分类 (变化类/总结类/对比类/事实查询/趋势分析)
    3. Extract - 参数提取 (时间/党派/议员/主题)
    4. Decompose - 问题拆解 (模板化/自由拆解)
    5. Retrieve - 数据检索 (混合检索)
    6. ReRank - 文档重排序 (Cohere重排)
    7. Summarize - 总结 (单问题/多问题)
    8. Exception - 异常处理 (无材料/LLM错误/检索错误等)
    
    路由规则:
    - Intent -> END (特殊情况) 或 Classify/Extract (正常问题)
    - Classify -> Extract
    - Extract -> Decompose (需要拆解) 或 Retrieve (不需要拆解)
    - Decompose -> Retrieve
    - Retrieve -> ReRank (找到材料) 或 Exception (未找到材料)
    - ReRank -> Summarize (重排成功) 或 Exception (重排失败)
    - Summarize -> END
    - Exception -> END
    """
    
    def __init__(self):
        """初始化工作流"""
        logger.info("[Workflow] 开始初始化工作流...")

        try:
            # 创建LLM客户端
            logger.info("[Workflow] 创建LLM客户端...")
            from ..llm.client import GeminiLLMClient

            # Flash模型客户端 (用于简单任务: Intent/Classify/Extract)
            flash_client = GeminiLLMClient(model_name="gemini-2.5-flash", temperature=0.0)
            logger.info("[Workflow] ⚡ Flash客户端已创建: gemini-2.5-flash (用于Intent/Classify/Extract)")

            # Pro模型客户端 (用于复杂任务: Decompose/Summarize)
            # 节点会在初始化时自动创建Pro客户端,无需显式传入

            # 创建节点
            logger.info("[Workflow] 创建节点...")
            self.intent_node = IntentNode(llm_client=flash_client)
            self.classify_node = ClassifyNode(llm_client=flash_client)
            self.extract_node = ExtractNode(llm_client=flash_client)
            self.decompose_node = DecomposeNode()  # 使用默认Pro模型
            self.retrieve_node = RetrieveNode()  # 会自动创建MilvusRetriever
            self.rerank_node = ReRankNode()  # 会自动创建CohereRerank
            self.summarize_node = SummarizeNode()  # 使用默认Pro模型
            self.exception_node = ExceptionNode()
            
            logger.info("[Workflow] 所有节点创建成功")
            
            # 构建工作流图
            logger.info("[Workflow] 构建工作流图...")
            self.graph = self._build_graph()
            
            logger.info("[Workflow] 工作流初始化完成")
            
        except Exception as e:
            logger.error(f"[Workflow] 工作流初始化失败: {str(e)}")
            raise
        
    def _build_graph(self) -> StateGraph:
        """
        构建工作流图
        
        Returns:
            StateGraph对象
        """
        # 创建状态图
        workflow = StateGraph(GraphState)
        
        # 添加节点
        workflow.add_node("intent_analysis", self.intent_node)
        workflow.add_node("classify", self.classify_node)
        workflow.add_node("extract", self.extract_node)
        workflow.add_node("decompose", self.decompose_node)
        workflow.add_node("retrieve", self.retrieve_node)
        workflow.add_node("rerank", self.rerank_node)
        workflow.add_node("summarize", self.summarize_node)
        workflow.add_node("exception", self.exception_node)
        
        # 设置入口点
        workflow.set_entry_point("intent_analysis")
        
        # 添加边 (节点间的连接)
        
        # Intent -> Classify 或 Extract
        workflow.add_conditional_edges(
            "intent_analysis",
            self._route_after_intent,
            {
                "classify": "classify",
                "extract": "extract",
                "exception": "exception",
            }
        )
        
        # Classify -> Extract
        workflow.add_conditional_edges(
            "classify",
            self._route_after_classify,
            {
                "extract": "extract",
                "exception": "exception",
            }
        )
        
        # Extract -> Decompose 或 Retrieve
        workflow.add_conditional_edges(
            "extract",
            self._route_after_extract,
            {
                "decompose": "decompose",
                "retrieve": "retrieve",
                "exception": "exception",
            }
        )
        
        # Decompose -> Retrieve
        workflow.add_conditional_edges(
            "decompose",
            self._route_after_decompose,
            {
                "retrieve": "retrieve",
                "exception": "exception",
            }
        )
        
        # 【Phase 4修改】Retrieve -> Summarize (跳过ReRank，直接使用BGE-M3检索结果)
        # ReRank过滤掉了检索Top 1的文档，反而降低精准度
        workflow.add_conditional_edges(
            "retrieve",
            self._route_after_retrieve,
            {
                "summarize": "summarize",  # 直接到Summarize
                "exception": "exception",
            }
        )
        
        # ReRank -> Summarize 或 Exception
        workflow.add_conditional_edges(
            "rerank",
            self._route_after_rerank,
            {
                "summarize": "summarize",
                "exception": "exception",
            }
        )
        
        # Summarize -> END
        workflow.add_edge("summarize", END)
        
        # Exception -> END
        workflow.add_edge("exception", END)
        
        return workflow.compile()
    
    # ========== 路由函数 ==========
    
    def _route_after_intent(self, state: GraphState) -> Literal["classify", "extract", "exception"]:
        """
        Intent节点后的路由
        
        Args:
            state: 当前状态
            
        Returns:
            下一个节点名称
        """
        if state.get("error"):
            return "exception"
        
        intent = state.get("intent")
        
        if intent == "complex":
            return "classify"
        else:
            return "extract"
    
    def _route_after_classify(self, state: GraphState) -> Literal["extract", "exception"]:
        """
        Classify节点后的路由
        
        Args:
            state: 当前状态
            
        Returns:
            下一个节点名称
        """
        if state.get("error"):
            return "exception"
        
        return "extract"
    
    def _route_after_extract(self, state: GraphState) -> Literal["decompose", "retrieve", "exception"]:
        """
        Extract节点后的路由
        
        Args:
            state: 当前状态
            
        Returns:
            下一个节点名称
        """
        if state.get("error"):
            return "exception"
        
        is_decomposed = state.get("is_decomposed", False)
        
        if is_decomposed:
            return "decompose"
        else:
            return "retrieve"
    
    def _route_after_decompose(self, state: GraphState) -> Literal["retrieve", "exception"]:
        """
        Decompose节点后的路由
        
        Args:
            state: 当前状态
            
        Returns:
            下一个节点名称
        """
        if state.get("error"):
            return "exception"
        
        return "retrieve"
    
    def _route_after_retrieve(self, state: GraphState) -> Literal["summarize", "exception"]:
        """
        Retrieve节点后的路由

        【Phase 4修改】直接到Summarize，跳过ReRank
        理由：Cohere ReRank在德语议会语境下反而过滤了最相关文档

        Args:
            state: 当前状态

        Returns:
            下一个节点名称
        """
        if state.get("error"):
            return "exception"

        no_material_found = state.get("no_material_found", False)

        if no_material_found:
            return "exception"
        else:
            return "summarize"  # 直接到Summarize，跳过ReRank
    
    def _route_after_rerank(self, state: GraphState) -> Literal["summarize", "exception"]:
        """
        ReRank节点后的路由
        
        Args:
            state: 当前状态
            
        Returns:
            下一个节点名称
        """
        if state.get("error"):
            return "exception"
        
        # 检查重排序结果是否存在
        reranked_results = state.get("reranked_results", [])
        
        if not reranked_results:
            return "exception"
        else:
            return "summarize"
    
    # ========== 工作流执行 ==========
    
    def run(self, question: str, verbose: bool = True, enable_performance_monitor: bool = True) -> GraphState:
        """
        运行工作流
        
        Args:
            question: 用户问题
            verbose: 是否打印详细日志
            enable_performance_monitor: 是否启用性能监控
            
        Returns:
            最终状态
        """
        logger.info(f"[Workflow] 开始处理问题: {question}")
        
        # 初始化性能监控
        monitor = None
        if enable_performance_monitor:
            monitor = get_performance_monitor()
            monitor.start_session()
        
        # 创建初始状态
        initial_state = create_initial_state(question)
        
        # 运行工作流
        try:
            final_state = self.graph.invoke(initial_state)
            
            if verbose:
                self._print_result(final_state)
            
            logger.info(f"[Workflow] 处理完成")
            
            # 结束性能监控并打印报告
            if monitor:
                monitor.end_session()
                if verbose:
                    monitor.print_session_report()
            
            return final_state
            
        except Exception as e:
            logger.error(f"[Workflow] 工作流执行失败: {str(e)}")
            raise
    
    def stream(self, question: str):
        """
        流式运行工作流(用于调试)
        
        Args:
            question: 用户问题
            
        Yields:
            每个节点的状态
        """
        logger.info(f"[Workflow] 流式处理问题: {question}")
        
        # 创建初始状态
        initial_state = create_initial_state(question)
        
        # 流式运行
        for state in self.graph.stream(initial_state):
            yield state
    
    def _print_result(self, state: GraphState):
        """
        打印结果
        
        Args:
            state: 最终状态
        """
        print("\n" + "="*80)
        print("问答结果")
        print("="*80)
        
        print(f"\n问题: {state['question']}")
        
        if state.get("intent"):
            print(f"意图: {state['intent']}")
        
        if state.get("question_type"):
            print(f"类型: {state['question_type']}")
        
        if state.get("parameters"):
            print(f"参数: {state['parameters']}")
        
        if state.get("sub_questions"):
            print(f"\n子问题 ({len(state['sub_questions'])}个):")
            for i, sq in enumerate(state['sub_questions'], 1):
                print(f"  {i}. {sq}")
        
        if state.get("sub_answers"):
            print(f"\n子答案:")
            for i, sa in enumerate(state['sub_answers'], 1):
                print(f"\n  [{i}] {sa['question']}")
                print(f"      {sa['answer'][:100]}...")
        
        print(f"\n最终答案:")
        print(f"{state.get('final_answer', '无答案')}")
        
        if state.get("error"):
            print(f"\n错误: {state['error']}")
        
        print("\n" + "="*80)


if __name__ == "__main__":
    # 测试工作流
    
    # 测试简单问题
    print("=== 测试1: 简单问题 ===")
    workflow = QuestionAnswerWorkflow()
    
    simple_question = "2019年德国联邦议院讨论了哪些主要议题?"
    
    print(f"问题: {simple_question}")
    print("\n注意: 需要先启动Milvus服务并构建索引才能完整运行")
    print("如需测试完整流程,请:")
    print("1. 启动Milvus服务")
    print("2. 运行 build_index.py 构建索引")
    print("3. 运行 python -m src.graph.workflow")
    
    # 测试复杂问题
    print("\n=== 测试2: 复杂问题 ===")
    complex_question = "在2015年到2018年期间,德国联邦议会中不同党派在难民家庭团聚问题上的讨论发生了怎样的变化?"
    
    print(f"问题: {complex_question}")
    
    # 如果要实际运行,取消下面的注释
    # result = workflow.run(complex_question)
