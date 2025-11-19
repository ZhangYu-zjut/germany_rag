"""
总结节点
基于检索结果生成答案
"""

from typing import List, Dict, Optional
from ...llm.client import GeminiLLMClient
from ...llm.prompts import PromptTemplates
from ...utils.logger import logger
from ..state import GraphState, update_state


class SummarizeNode:
    """
    总结节点
    
    功能:
    1. 单问题总结: 基于检索材料回答问题
    2. 多问题总结: 综合多个子答案形成完整答案
    3. 引用来源信息
    
    输出:
    - final_answer: 最终答案
    - sub_answers: 子问题答案列表(如果有)
    """
    
    def __init__(self, llm_client: GeminiLLMClient = None):
        """
        初始化总结节点
        
        Args:
            llm_client: LLM客户端
        """
        self.llm = llm_client or GeminiLLMClient()
        self.prompts = PromptTemplates()
        
    def __call__(self, state: GraphState) -> GraphState:
        """
        执行总结
        
        Args:
            state: 当前状态
            
        Returns:
            更新后的状态
        """
        retrieval_results = state.get("retrieval_results", [])
        sub_questions = state.get("sub_questions")
        
        logger.info(f"[SummarizeNode] 开始总结,共 {len(retrieval_results)} 个检索结果")
        
        try:
            if sub_questions and len(retrieval_results) > 1:
                # 多问题总结
                final_answer, sub_answers = self._multi_question_summarize(
                    state["question"],
                    retrieval_results
                )
            else:
                # 单问题总结
                final_answer, sub_answers = self._single_question_summarize(
                    state["question"],
                    retrieval_results[0] if retrieval_results else None
                )
            
            logger.info(f"[SummarizeNode] 总结完成,答案长度: {len(final_answer)}")
            
            # 更新状态
            return update_state(
                state,
                final_answer=final_answer,
                sub_answers=sub_answers,
                current_node="summarize",
                next_node="end"
            )
            
        except Exception as e:
            logger.error(f"[SummarizeNode] 总结失败: {str(e)}")
            return update_state(
                state,
                error=f"总结失败: {str(e)}",
                final_answer="抱歉,生成答案时发生错误。",
                current_node="summarize",
                next_node="end"
            )
    
    def _single_question_summarize(
        self,
        question: str,
        retrieval_result: Optional[Dict]
    ) -> tuple[str, Optional[List[Dict]]]:
        """
        单问题总结
        
        Args:
            question: 问题
            retrieval_result: 检索结果
            
        Returns:
            (final_answer, sub_answers)
        """
        logger.info("[SummarizeNode] 单问题总结")
        
        if not retrieval_result or not retrieval_result.get("chunks"):
            return "抱歉,未找到相关材料。", None
        
        # 格式化上下文
        context = self._format_context(retrieval_result["chunks"])
        
        # 构建Prompt
        prompt = self.prompts.format_summarize_prompt(
            question=question,
            context=context
        )
        
        # 调用LLM
        answer = self.llm.invoke(prompt)
        
        logger.debug(f"[SummarizeNode] 答案: {answer[:200]}...")
        
        return answer, None
    
    def _format_date(self, metadata: Dict) -> str:
        """
        智能格式化日期，避免显示None

        规则:
        1. 如果year/month/day都有: "2017-01-15"
        2. 如果只有year: "2017"
        3. 优先降级显示非None字段

        Args:
            metadata: 元数据字典

        Returns:
            格式化的日期字符串
        """
        year = metadata.get('year')
        month = metadata.get('month')
        day = metadata.get('day')

        # 收集所有非None的部分
        parts = []
        if year:
            parts.append(str(year))
        if month:
            parts.append(str(month))
        if day:
            parts.append(str(day))

        # 如果都有，使用标准格式
        if len(parts) == 3:
            return f"{year}-{month}-{day}"
        # 否则用连字符连接所有非None部分
        elif parts:
            return "-".join(parts)
        # 如果全都是None，返回"Unknown"
        else:
            return "Unknown"

    def _multi_question_summarize(
        self,
        original_question: str,
        retrieval_results: List[Dict]
    ) -> tuple[str, List[Dict]]:
        """
        多问题总结

        Args:
            original_question: 原始问题
            retrieval_results: 检索结果列表

        Returns:
            (final_answer, sub_answers)
        """
        logger.info(f"[SummarizeNode] 多问题总结,共 {len(retrieval_results)} 个子问题")

        # 第一步: 为每个子问题生成答案
        sub_answers = []

        for result in retrieval_results:
            sub_question = result["question"]
            chunks = result.get("chunks", [])

            if chunks:
                # 格式化上下文
                context = self._format_context(chunks)

                # 构建Prompt
                prompt = self.prompts.format_summarize_prompt(
                    question=sub_question,
                    context=context
                )

                # 调用LLM
                sub_answer = self.llm.invoke(prompt)

                # 提取来源 - 使用智能日期格式化
                sources = [
                    {
                        "speaker": chunk["metadata"].get("speaker"),
                        "group": chunk["metadata"].get("group_chinese") or chunk["metadata"].get("group"),
                        "date": self._format_date(chunk["metadata"])
                    }
                    for chunk in chunks[:3]  # 只保留前3个来源
                ]
            else:
                sub_answer = "未找到相关材料。"
                sources = []

            sub_answers.append({
                "question": sub_question,
                "answer": sub_answer,
                "sources": sources
            })

            logger.debug(f"[SummarizeNode] 子问题答案: {sub_question} -> {sub_answer[:100]}...")
        
        # 第二步: 综合所有子答案
        prompt = self.prompts.format_summarize_prompt(
            question=original_question,
            sub_qa_pairs=sub_answers
        )
        
        # 调用LLM
        final_answer = self.llm.invoke(prompt)
        
        logger.debug(f"[SummarizeNode] 最终答案: {final_answer[:200]}...")
        
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
            
            # 格式化单个chunk
            speaker = metadata.get("speaker", "未知")
            group = metadata.get("group_chinese") or metadata.get("group", "未知")
            date = f"{metadata.get('year')}-{metadata.get('month')}-{metadata.get('day')}"
            
            context_part = f"""
[材料 {i}]
发言人: {speaker} ({group})
日期: {date}
内容: {text}
"""
            context_parts.append(context_part)
        
        return "\n".join(context_parts)


if __name__ == "__main__":
    # 测试总结节点
    from ..state import create_initial_state, update_state
    
    # 测试单问题总结
    question = "2019年德国联邦议院讨论了哪些主要议题?"
    
    # 模拟检索结果
    mock_retrieval_results = [
        {
            "question": question,
            "chunks": [
                {
                    "text": "我们今天讨论的主要议题包括气候保护、数字化转型和社会公平...",
                    "metadata": {
                        "speaker": "Merkel",
                        "group": "CDU/CSU",
                        "group_chinese": "基民盟/基社盟",
                        "year": "2019",
                        "month": "03",
                        "day": "15"
                    },
                    "score": 0.95
                }
            ]
        }
    ]
    
    state = create_initial_state(question)
    state = update_state(
        state,
        retrieval_results=mock_retrieval_results
    )
    
    node = SummarizeNode()
    result = node(state)
    
    print("=== 单问题总结测试 ===")
    print(f"问题: {question}")
    print(f"\n答案:\n{result['final_answer']}")
    print(f"\n下一节点: {result['next_node']}")
