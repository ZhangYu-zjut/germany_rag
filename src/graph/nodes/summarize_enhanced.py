"""
增强版总结节点
支持分层总结和模块化输出
"""

from typing import List, Dict, Optional, Tuple
from ...llm.client import GeminiLLMClient
from ...llm.prompts_summarize import SummarizePrompts
from ...utils.logger import logger
from ..state import GraphState, update_state


class EnhancedSummarizeNode:
    """
    增强版总结节点
    
    核心改进:
    1. 根据问题类型选择定制化Prompt
    2. 模块化德文输出（speaker/statement/evidence/source）
    3. 分层总结（单子问题 → 多子问题整合）
    4. 德文系统Prompt
    
    支持的问题类型:
    - 变化类: 时间序列分析 + 转折点识别
    - 对比类: 对比表格 + 差异分析
    - 总结类: 主题分组 + 核心观点
    - 趋势分析: 阶段划分 + 趋势识别
    """
    
    def __init__(self, llm_client: GeminiLLMClient = None):
        """
        初始化增强版总结节点
        
        Args:
            llm_client: LLM客户端
        """
        self.llm = llm_client or GeminiLLMClient()
        self.prompts = SummarizePrompts()
        
    def __call__(self, state: GraphState) -> GraphState:
        """
        执行总结
        
        Args:
            state: 当前状态
            
        Returns:
            更新后的状态
        """
        question = state["question"]
        question_type = state.get("question_type", "")
        # 获取重排序后的检索结果（优先）或原始检索结果（降级）
        reranked_results = state.get("reranked_results", [])
        retrieval_results = state.get("retrieval_results", [])
        
        # 优先使用重排序结果，如果不存在则使用原始检索结果
        if reranked_results:
            logger.info(f"[EnhancedSummarizeNode] 使用重排序结果 ({len(reranked_results)} 个)")
            processing_results = reranked_results
        else:
            logger.info(f"[EnhancedSummarizeNode] 重排序结果不存在，使用原始检索结果 ({len(retrieval_results)} 个)")
            processing_results = retrieval_results
            
        sub_questions = state.get("sub_questions")
        is_decomposed = state.get("is_decomposed", False)
        
        logger.info(f"[EnhancedSummarizeNode] 开始总结")
        logger.info(f"[EnhancedSummarizeNode] 问题类型: {question_type}")
        logger.info(f"[EnhancedSummarizeNode] 处理结果数: {len(processing_results)}")
        logger.info(f"[EnhancedSummarizeNode] 是否拆解: {is_decomposed}")
        
        try:
            # 检查是否有材料
            if not processing_results or len(processing_results) == 0:
                logger.warning("[EnhancedSummarizeNode] 无检索结果")
                return update_state(
                    state,
                    error="未找到相关材料",
                    error_type="NO_MATERIAL",
                    no_material_found=True,
                    current_node="summarize",
                    next_node="exception"
                )
            
            # 判断是单问题还是多问题总结
            if is_decomposed and len(processing_results) > 1:
                # 多问题总结
                final_answer, sub_answers = self._multi_question_summarize(
                    question=question,
                    question_type=question_type,
                    retrieval_results=processing_results
                )
            else:
                # 单问题总结
                final_answer, sub_answers = self._single_question_summarize(
                    question=question,
                    retrieval_result=processing_results[0] if processing_results else None
                )
            
            logger.info(f"[EnhancedSummarizeNode] 总结完成")
            logger.info(f"[EnhancedSummarizeNode] 答案长度: {len(final_answer)} 字符")
            
            # 更新状态
            return update_state(
                state,
                final_answer=final_answer,
                sub_answers=sub_answers,
                current_node="summarize",
                next_node="end"
            )
            
        except Exception as e:
            logger.error(f"[EnhancedSummarizeNode] 总结失败: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return update_state(
                state,
                error=f"总结失败: {str(e)}",
                error_type="LLM_ERROR",
                current_node="summarize",
                next_node="exception"
            )
    
    def _single_question_summarize(
        self,
        question: str,
        retrieval_result: Optional[Dict]
    ) -> Tuple[str, Optional[List[Dict]]]:
        """
        单问题总结（使用模块化输出）
        
        Args:
            question: 问题
            retrieval_result: 检索结果
            
        Returns:
            (final_answer, sub_answers)
        """
        logger.info("[EnhancedSummarizeNode] 单问题总结（模块化输出）")
        
        if not retrieval_result or not retrieval_result.get("chunks"):
            logger.warning("[EnhancedSummarizeNode] 检索结果为空")
            return "Entschuldigung, es wurden keine relevanten Materialien gefunden.", None
        
        chunks = retrieval_result.get("chunks", [])
        logger.info(f"[EnhancedSummarizeNode] 材料数量: {len(chunks)}")
        
        # 格式化上下文
        context = self._format_context(chunks)
        
        # 构建Prompt（使用模块化输出模板）
        prompt = self.prompts.SINGLE_QUESTION_MODULAR.format(
            question=question,
            context=context
        )
        
        # 添加德文系统Prompt
        full_prompt = f"{self.prompts.SYSTEM_PROMPT_DE}\n\n{prompt}"
        
        # 调用LLM
        logger.debug("[EnhancedSummarizeNode] 调用LLM...")
        answer = self.llm.invoke(full_prompt)
        
        logger.debug(f"[EnhancedSummarizeNode] 答案预览: {answer[:200]}...")
        
        return answer, None
    
    def _multi_question_summarize(
        self,
        question: str,
        question_type: str,
        retrieval_results: List[Dict]
    ) -> Tuple[str, List[Dict]]:
        """
        多问题分层总结
        
        流程:
        1. 为每个子问题生成模块化答案
        2. 根据问题类型选择合适的整合模板
        3. 生成最终的结构化答案
        
        Args:
            question: 原始问题
            question_type: 问题类型
            retrieval_results: 检索结果列表
            
        Returns:
            (final_answer, sub_answers)
        """
        logger.info(f"[EnhancedSummarizeNode] 多问题分层总结")
        logger.info(f"[EnhancedSummarizeNode] 子问题数: {len(retrieval_results)}")
        
        # Step 1: 为每个子问题生成答案
        sub_answers = []
        
        for i, result in enumerate(retrieval_results, 1):
            sub_question = result["question"]
            chunks = result.get("chunks", [])
            
            logger.info(f"[EnhancedSummarizeNode] 处理子问题 {i}/{len(retrieval_results)}: {sub_question}")
            
            if chunks and len(chunks) > 0:
                # 格式化上下文
                context = self._format_context(chunks)
                
                # 构建Prompt
                prompt = self.prompts.SINGLE_QUESTION_MODULAR.format(
                    question=sub_question,
                    context=context
                )
                
                full_prompt = f"{self.prompts.SYSTEM_PROMPT_DE}\n\n{prompt}"
                
                # 调用LLM
                sub_answer = self.llm.invoke(full_prompt)
                
                # 提取来源
                sources = self._extract_sources(chunks)
            else:
                logger.warning(f"[EnhancedSummarizeNode] 子问题 {i} 无材料")
                sub_answer = "Keine relevanten Materialien gefunden."
                sources = []
            
            sub_answers.append({
                "question": sub_question,
                "answer": sub_answer,
                "sources": sources
            })
            
            logger.debug(f"[EnhancedSummarizeNode] 子答案 {i} 长度: {len(sub_answer)}")
        
        # Step 2: 根据问题类型选择整合模板
        summary_template = self.prompts.select_summary_template(question_type)
        
        logger.info(f"[EnhancedSummarizeNode] 使用模板类型: {question_type}")
        
        # Step 3: 格式化子问题答案对
        sub_qa_text = self.prompts.format_sub_qa_pairs(sub_answers)
        
        # Step 4: 构建最终Prompt
        final_prompt = summary_template.format(
            original_question=question,
            sub_qa_pairs=sub_qa_text
        )
        
        full_final_prompt = f"{self.prompts.SYSTEM_PROMPT_DE}\n\n{final_prompt}"
        
        # Step 5: 调用LLM生成最终答案
        logger.info("[EnhancedSummarizeNode] 生成最终整合答案...")
        final_answer = self.llm.invoke(full_final_prompt)
        
        logger.info(f"[EnhancedSummarizeNode] 最终答案长度: {len(final_answer)}")
        
        return final_answer, sub_answers
    
    def _format_context(self, chunks: List[Dict]) -> str:
        """
        格式化检索到的chunks为上下文
        
        Args:
            chunks: 检索结果chunks
            
        Returns:
            格式化的上下文字符串
        """
        context_parts = []
        
        for i, chunk in enumerate(chunks, 1):
            metadata = chunk.get("metadata", {})
            text = chunk.get("text", "")
            score = chunk.get("score", 0.0)
            
            # 提取元数据
            speaker = metadata.get("speaker", "Unbekannt")
            group = metadata.get("group", "Unbekannt")
            year = metadata.get("year", "")
            month = metadata.get("month", "")
            day = metadata.get("day", "")
            text_id = metadata.get("text_id", "")
            
            # 格式化日期
            date = f"{year}-{month}-{day}" if year else "Unbekannt"
            
            # 格式化单个chunk
            context_part = f"""
[Material {i}] (Relevanz: {score:.2f})
Redner: {speaker} ({group})
Datum: {date}
Quelle: {text_id}
Inhalt: {text}
"""
            context_parts.append(context_part)
        
        return "\n".join(context_parts)
    
    def _extract_sources(self, chunks: List[Dict]) -> List[Dict]:
        """
        从chunks中提取来源信息
        
        Args:
            chunks: 检索结果chunks
            
        Returns:
            来源信息列表
        """
        sources = []
        
        # 只保留前5个来源
        for chunk in chunks[:5]:
            metadata = chunk.get("metadata", {})
            
            source = {
                "speaker": metadata.get("speaker", "Unbekannt"),
                "group": metadata.get("group", "Unbekannt"),
                "date": f"{metadata.get('year', '')}-{metadata.get('month', '')}-{metadata.get('day', '')}",
                "text_id": metadata.get("text_id", ""),
                "score": chunk.get("score", 0.0)
            }
            
            sources.append(source)
        
        return sources


# 为了保持向后兼容，创建一个别名
SummarizeNode = EnhancedSummarizeNode


if __name__ == "__main__":
    # 测试增强版总结节点
    from ..state import create_initial_state, update_state
    
    print("="*60)
    print("增强版SummarizeNode测试")
    print("="*60)
    
    # 测试1: 单问题总结
    print("\n【测试1: 单问题总结】")
    question1 = "2019年德国议会讨论了哪些主要议题？"
    
    # 模拟检索结果
    mock_result1 = {
        "question": question1,
        "chunks": [
            {
                "text": "Heute diskutieren wir über Klimaschutz, Digitalisierung und soziale Gerechtigkeit...",
                "metadata": {
                    "speaker": "Angela Merkel",
                    "group": "CDU/CSU",
                    "year": "2019",
                    "month": "03",
                    "day": "15",
                    "text_id": "pp_19_100_00001"
                },
                "score": 0.95
            },
            {
                "text": "Die digitale Transformation ist eine der größten Herausforderungen...",
                "metadata": {
                    "speaker": "Olaf Scholz",
                    "group": "SPD",
                    "year": "2019",
                    "month": "05",
                    "day": "20",
                    "text_id": "pp_19_110_00002"
                },
                "score": 0.88
            }
        ]
    }
    
    state1 = create_initial_state(question1)
    state1 = update_state(
        state1,
        retrieval_results=[mock_result1],
        is_decomposed=False
    )
    
    print(f"问题: {question1}")
    print(f"材料数: {len(mock_result1['chunks'])}")
    print("✅ 模拟数据准备完成（实际需要LLM）")
    
    # 测试2: 多问题总结
    print("\n【测试2: 多问题总结 - 变化类】")
    question2 = "2015-2018年不同党派在难民政策上的立场变化？"
    
    # 模拟多个子问题的检索结果
    mock_results2 = [
        {
            "question": "2015年CDU/CSU在难民政策上的立场？",
            "chunks": [
                {
                    "text": "Wir schaffen das! Deutschland muss humanitär handeln...",
                    "metadata": {
                        "speaker": "Angela Merkel",
                        "group": "CDU/CSU",
                        "year": "2015",
                        "month": "09",
                        "day": "01",
                        "text_id": "pp_18_120_00001"
                    },
                    "score": 0.92
                }
            ]
        },
        {
            "question": "2018年CDU/CSU在难民政策上的立场？",
            "chunks": [
                {
                    "text": "Wir müssen die Zuwanderung besser steuern und kontrollieren...",
                    "metadata": {
                        "speaker": "Horst Seehofer",
                        "group": "CDU/CSU",
                        "year": "2018",
                        "month": "06",
                        "day": "15",
                        "text_id": "pp_19_045_00001"
                    },
                    "score": 0.89
                }
            ]
        }
    ]
    
    state2 = create_initial_state(question2)
    state2 = update_state(
        state2,
        question_type="变化类",
        retrieval_results=mock_results2,
        sub_questions=["2015年CDU/CSU...", "2018年CDU/CSU..."],
        is_decomposed=True
    )
    
    print(f"问题: {question2}")
    print(f"问题类型: 变化类")
    print(f"子问题数: {len(mock_results2)}")
    print("✅ 模拟数据准备完成（实际需要LLM）")
    
    print("\n" + "="*60)
    print("注意: 完整测试需要启动LLM服务（Gemini API）")
    print("="*60)
    
    print("\n【核心功能】")
    print("✅ 单问题模块化总结")
    print("✅ 多问题分层总结")
    print("✅ 根据问题类型选择Prompt")
    print("✅ 德文结构化输出")
    print("✅ 来源信息提取")

