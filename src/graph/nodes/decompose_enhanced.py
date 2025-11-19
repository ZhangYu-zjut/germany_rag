"""
增强版问题拆解节点
使用模板化拆解策略，提高拆解质量和一致性
"""

from typing import List, Dict, Optional
from ...llm.client import GeminiLLMClient
from ...llm.prompts import PromptTemplates
from ...utils.logger import logger
from ..state import GraphState, update_state
from ..templates import TemplateSelector


class EnhancedDecomposeNode:
    """
    增强版问题拆解节点
    
    核心改进:
    1. 使用专门设计的拆解模板（变化类/总结类/对比类/趋势分析）
    2. 模板化拆解优先，LLM拆解作为backup
    3. 支持复杂的多维拆解策略
    
    工作流程:
    1. 判断问题类型
    2. 选择对应的拆解模板
    3. 根据提取的参数生成子问题
    4. 如果模板不适用，使用LLM自由拆解
    """
    
    def __init__(self, llm_client: GeminiLLMClient = None):
        """
        初始化增强版问题拆解节点
        
        Args:
            llm_client: LLM客户端,如果为None则自动创建
        """
        self.llm = llm_client or GeminiLLMClient()
        self.prompts = PromptTemplates()
        self.template_selector = TemplateSelector()
        
    def __call__(self, state: GraphState) -> GraphState:
        """
        执行问题拆解
        
        Args:
            state: 当前状态
            
        Returns:
            更新后的状态
        """
        question = state["question"]
        question_type = state.get("question_type", "")
        parameters = state.get("parameters", {})
        
        logger.info(f"[EnhancedDecomposeNode] 开始拆解问题")
        logger.info(f"[EnhancedDecomposeNode] 问题类型: {question_type}")
        logger.info(f"[EnhancedDecomposeNode] 参数: {parameters}")
        
        try:
            # Step 1: 判断是否需要拆解
            if not self._need_decompose(question_type, parameters):
                logger.info("[EnhancedDecomposeNode] 问题无需拆解，直接检索")
                return update_state(
                    state,
                    sub_questions=[question],
                    is_decomposed=False,
                    current_node="decompose",
                    next_node="retrieve"
                )
            
            # Step 2: 尝试模板化拆解
            sub_questions = self._template_decompose(question_type, parameters)

            # Step 3: 如果模板拆解失败，使用LLM拆解
            if not sub_questions or len(sub_questions) == 0:
                logger.warning("[EnhancedDecomposeNode] 模板拆解失败，使用LLM拆解")
                sub_questions = self._llm_decompose(question, question_type, parameters)

            # Step 3.5: 统一格式化子问题（支持字符串和字典两种格式）
            sub_questions = self._normalize_sub_questions(sub_questions, parameters)

            # Step 4: 验证子问题质量
            sub_questions = self._validate_sub_questions(sub_questions, question)

            logger.info(f"[EnhancedDecomposeNode] 拆解完成，生成 {len(sub_questions)} 个子问题")
            for i, sq in enumerate(sub_questions, 1):
                question_text = sq if isinstance(sq, str) else sq.get("question", sq)
                logger.info(f"  子问题{i}: {question_text}")
            
            # 更新状态
            return update_state(
                state,
                sub_questions=sub_questions,
                is_decomposed=True,
                current_node="decompose",
                next_node="retrieve"
            )
            
        except Exception as e:
            logger.error(f"[EnhancedDecomposeNode] 拆解失败: {str(e)}")
            # 失败时使用原问题
            return update_state(
                state,
                sub_questions=[question],
                is_decomposed=False,
                error=f"拆解失败: {str(e)}",
                current_node="decompose",
                next_node="retrieve"
            )
    
    def _need_decompose(self, question_type: str, parameters: Dict) -> bool:
        """
        判断是否需要拆解
        
        Args:
            question_type: 问题类型
            parameters: 提取的参数
            
        Returns:
            是否需要拆解
        """
        # 简单的事实查询不需要拆解
        if question_type == "事实查询":
            time_range = parameters.get("time_range", {})
            parties = parameters.get("parties", [])
            
            # 单一时间点 + 单一党派 = 不拆解
            if not time_range.get("end_year") and len(parties) <= 1:
                return False
        
        # 变化类、对比类、趋势分析一定要拆解
        if question_type in ["变化类", "对比类", "趋势分析"]:
            return True
        
        # 总结类根据复杂度判断
        if question_type == "总结类":
            time_range = parameters.get("time_range", {})
            start_year = time_range.get("start_year")
            end_year = time_range.get("end_year")
            
            # 时间跨度>2年，需要拆解
            if start_year and end_year:
                if int(end_year) - int(start_year) > 2:
                    return True
            
            # 多个党派或议员，需要拆解
            if len(parameters.get("parties", [])) > 1 or len(parameters.get("speakers", [])) > 1:
                return True
            
            # 多个主题，需要拆解
            if len(parameters.get("topics", [])) > 1:
                return True
        
        # 默认不拆解
        return False
    
    def _template_decompose(self, question_type: str, parameters: Dict) -> List[str]:
        """
        使用模板拆解
        
        Args:
            question_type: 问题类型
            parameters: 提取的参数
            
        Returns:
            子问题列表
        """
        logger.info(f"[EnhancedDecomposeNode] 使用模板拆解: {question_type}")
        
        try:
            sub_questions = self.template_selector.decompose(question_type, parameters)
            
            logger.info(f"[EnhancedDecomposeNode] 模板拆解成功，生成 {len(sub_questions)} 个子问题")
            
            return sub_questions
            
        except Exception as e:
            logger.error(f"[EnhancedDecomposeNode] 模板拆解失败: {str(e)}")
            return []
    
    def _llm_decompose(
        self, 
        question: str, 
        question_type: str, 
        parameters: Dict
    ) -> List[str]:
        """
        使用LLM自由拆解
        
        Args:
            question: 原问题
            question_type: 问题类型
            parameters: 提取的参数
            
        Returns:
            子问题列表
        """
        logger.info("[EnhancedDecomposeNode] 使用LLM自由拆解")
        
        try:
            # 构建Prompt
            prompt = self.prompts.format_decomposition_prompt(
                question=question,
                question_type=question_type,
                parameters=parameters,
                use_template=False
            )
            
            # 调用LLM
            response = self.llm.invoke(prompt)
            
            logger.debug(f"[EnhancedDecomposeNode] LLM响应: {response[:200]}...")
            
            # 解析子问题
            sub_questions = self._parse_sub_questions(response)
            
            logger.info(f"[EnhancedDecomposeNode] LLM拆解成功，生成 {len(sub_questions)} 个子问题")
            
            return sub_questions
            
        except Exception as e:
            logger.error(f"[EnhancedDecomposeNode] LLM拆解失败: {str(e)}")
            return []
    
    def _parse_sub_questions(self, response: str) -> List[str]:
        """
        从LLM响应中解析子问题列表
        
        支持格式:
        - 1. 问题
        - 1) 问题
        - - 问题
        - • 问题
        - 问题（直接一行）
        
        Args:
            response: LLM响应
            
        Returns:
            子问题列表
        """
        sub_questions = []
        
        # 按行分割
        lines = response.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            
            # 跳过空行和标题行
            if not line or line.startswith('#') or line.startswith('【'):
                continue
            
            # 移除序号和标记
            # 支持: "1. ", "1) ", "- ", "• ", "* "
            import re
            line = re.sub(r'^\d+[\.\)]\s*', '', line)  # 数字序号
            line = re.sub(r'^[-•*]\s*', '', line)  # 列表符号
            line = line.strip()
            
            # 过滤太短的行（可能是标题或无效内容）
            if line and len(line) > 10:
                # 确保是问句（以？或问号结尾）
                if not (line.endswith('？') or line.endswith('?')):
                    line += '？'
                
                sub_questions.append(line)
        
        return sub_questions

    def _normalize_sub_questions(
        self,
        sub_questions: List,
        parameters: Dict
    ) -> List[Dict]:
        """
        统一格式化子问题，支持字符串和字典两种格式

        将旧格式（List[str]）和新格式（List[Dict]）统一转换为Dict格式，
        并智能提取target_year等元数据

        Args:
            sub_questions: 子问题列表（可能是字符串或字典）
            parameters: 全局参数（用于提取默认值）

        Returns:
            统一格式化后的子问题列表（List[Dict]）
        """
        import re

        normalized = []

        for sq in sub_questions:
            # 情况1: 已经是字典格式（新格式，来自ChangeAnalysisTemplate）
            if isinstance(sq, dict):
                normalized.append(sq)
                continue

            # 情况2: 字符串格式（旧格式，来自其他Template或LLM）
            # 需要智能提取target_year
            question_text = sq

            # 尝试从问题文本中提取年份
            # 匹配模式: "2015年", "2015-2017年", "2015年CDU/CSU..."
            year_pattern = r'(\d{4})年'
            year_matches = re.findall(year_pattern, question_text)

            # 提取党派信息
            party_pattern = r'(CDU/CSU|SPD|Grüne/Bündnis 90|FDP|DIE LINKE|AfD|ALL_PARTIES)'
            party_matches = re.findall(party_pattern, question_text)

            # 判断是否是单年问题
            target_year = None
            retrieval_strategy = "multi_year"  # 默认多年检索

            if len(year_matches) == 1:
                # 只提到一个年份 → 单年检索
                target_year = year_matches[0]
                retrieval_strategy = "single_year"
            elif len(year_matches) > 1:
                # 多个年份（如"2015年与2017年对比"） → 多年检索
                retrieval_strategy = "multi_year"

            # 构造字典格式
            normalized.append({
                "question": question_text,
                "target_year": target_year,
                "target_party": party_matches[0] if party_matches else None,
                "retrieval_strategy": retrieval_strategy
            })

        logger.info(f"[EnhancedDecomposeNode] 格式化完成: {len(normalized)}个子问题")
        for i, sq in enumerate(normalized, 1):
            if sq.get("target_year"):
                logger.debug(f"  子问题{i}: target_year={sq['target_year']}, strategy={sq['retrieval_strategy']}")

        return normalized

    def _validate_sub_questions(
        self,
        sub_questions: List,
        original_question: str
    ) -> List:
        """
        验证子问题质量（支持Dict格式）

        Args:
            sub_questions: 子问题列表（Dict格式）
            original_question: 原问题

        Returns:
            验证后的子问题列表
        """
        # 如果子问题为空，返回原问题（包装成Dict格式）
        if not sub_questions:
            logger.warning("[EnhancedDecomposeNode] 子问题为空，使用原问题")
            return [{
                "question": original_question,
                "target_year": None,
                "target_party": None,
                "retrieval_strategy": "multi_year"
            }]

        # 去重（基于question文本）
        unique_questions = []
        seen = set()
        for sq in sub_questions:
            # 兼容字符串和字典格式
            q_text = sq.get("question", sq) if isinstance(sq, dict) else sq
            q_normalized = q_text.strip().lower()

            if q_normalized not in seen:
                unique_questions.append(sq)
                seen.add(q_normalized)

        # 限制子问题数量（避免检索负担过重）
        max_sub_questions = 15  # 增加到15，因为单年检索更快
        if len(unique_questions) > max_sub_questions:
            logger.warning(f"[EnhancedDecomposeNode] 子问题过多({len(unique_questions)})，截取前{max_sub_questions}个")
            unique_questions = unique_questions[:max_sub_questions]

        logger.info(f"[EnhancedDecomposeNode] 验证后子问题数: {len(unique_questions)}")

        return unique_questions


# 为了保持向后兼容，创建一个别名
DecomposeNode = EnhancedDecomposeNode


if __name__ == "__main__":
    # 测试增强版问题拆解节点
    from ..state import create_initial_state, update_state
    
    print("="*60)
    print("增强版DecomposeNode测试")
    print("="*60)
    
    # 测试1: 变化类问题
    print("\n【测试1: 变化类问题】")
    question1 = "在2015-2018年期间，不同党派在难民政策上的立场有何变化？"
    state1 = create_initial_state(question1)
    state1 = update_state(
        state1,
        question_type="变化类",
        parameters={
            "time_range": {"start_year": "2015", "end_year": "2018"},
            "parties": ["CDU/CSU", "SPD"],
            "topics": ["难民政策"]
        }
    )
    
    node = EnhancedDecomposeNode()
    result1 = node(state1)
    
    print(f"原问题: {question1}")
    print(f"是否拆解: {result1.get('is_decomposed', False)}")
    print(f"子问题数: {len(result1['sub_questions'])}")
    for i, sq in enumerate(result1['sub_questions'], 1):
        print(f"  {i}. {sq}")
    
    # 测试2: 总结类问题（简单，不需要拆解）
    print("\n【测试2: 总结类问题（简单）】")
    question2 = "2021年绿党在气候保护方面的主要观点？"
    state2 = create_initial_state(question2)
    state2 = update_state(
        state2,
        question_type="总结类",
        parameters={
            "time_range": {"start_year": "2021"},
            "parties": ["绿党"],
            "topics": ["气候保护"]
        }
    )
    
    result2 = node(state2)
    
    print(f"原问题: {question2}")
    print(f"是否拆解: {result2.get('is_decomposed', False)}")
    print(f"子问题数: {len(result2['sub_questions'])}")
    for i, sq in enumerate(result2['sub_questions'], 1):
        print(f"  {i}. {sq}")
    
    # 测试3: 对比类问题
    print("\n【测试3: 对比类问题】")
    question3 = "对比CDU/CSU、SPD和FDP在2019年数字化政策上的立场差异"
    state3 = create_initial_state(question3)
    state3 = update_state(
        state3,
        question_type="对比类",
        parameters={
            "time_range": {"start_year": "2019"},
            "parties": ["CDU/CSU", "SPD", "FDP"],
            "topics": ["数字化政策"]
        }
    )
    
    result3 = node(state3)
    
    print(f"原问题: {question3}")
    print(f"是否拆解: {result3.get('is_decomposed', False)}")
    print(f"子问题数: {len(result3['sub_questions'])}")
    for i, sq in enumerate(result3['sub_questions'], 1):
        print(f"  {i}. {sq}")
    
    print("\n" + "="*60)
    print("测试完成！")

