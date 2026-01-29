"""
增强版问题拆解节点
使用模板化拆解策略，提高拆解质量和一致性

【Day 4增强】集成知识图谱扩展
- 支持条件触发的知识图谱扩展
- 为Q7类问题生成额外的扩展查询
"""

from typing import List, Dict, Optional
from ...llm.client import GeminiLLMClient
from ...llm.prompts import PromptTemplates
from ...utils.logger import logger
from ..state import GraphState, update_state
from ..templates import TemplateSelector
from ..knowledge_graph import get_knowledge_graph_manager


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
    
    def __init__(self, llm_client: GeminiLLMClient = None, enable_kg_expansion: bool = True):
        """
        初始化增强版问题拆解节点

        Args:
            llm_client: LLM客户端,如果为None则自动创建
            enable_kg_expansion: 是否启用知识图谱扩展（默认True）
        """
        self.llm = llm_client or GeminiLLMClient()
        self.prompts = PromptTemplates()
        self.template_selector = TemplateSelector()

        # 【Day 4增强】知识图谱扩展
        self.enable_kg_expansion = enable_kg_expansion
        self.kg_manager = None
        if enable_kg_expansion:
            try:
                self.kg_manager = get_knowledge_graph_manager()
                logger.info("[EnhancedDecomposeNode] 知识图谱管理器已初始化")
            except Exception as e:
                logger.warning(f"[EnhancedDecomposeNode] 知识图谱初始化失败: {e}，将跳过KG扩展")
        
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
            logger.info(f"[EnhancedDecomposeNode] 模板拆解后子问题数: {len(sub_questions)}")

            # Step 3: 如果模板拆解失败，使用LLM拆解
            if not sub_questions or len(sub_questions) == 0:
                logger.warning("[EnhancedDecomposeNode] 模板拆解失败，使用LLM拆解")
                sub_questions = self._llm_decompose(question, question_type, parameters)

            # Step 3.5: 统一格式化子问题（支持字符串和字典两种格式）
            sub_questions = self._normalize_sub_questions(sub_questions, parameters)

            # Step 4: 验证子问题质量（传入state用于智能限制计算）
            sub_questions = self._validate_sub_questions(sub_questions, question, state)

            logger.info(f"[EnhancedDecomposeNode] 拆解完成，生成 {len(sub_questions)} 个子问题")
            for i, sq in enumerate(sub_questions, 1):
                question_text = sq if isinstance(sq, str) else sq.get("question", sq)
                logger.info(f"  子问题{i}: {question_text}")

            # 【Day 4增强】Step 5: 知识图谱扩展
            # 【优化】变化类/对比类问题模板已完整覆盖所有时间点，禁用KG扩展避免冗余
            kg_expansion_info = None
            skip_kg_types = ["变化类", "对比类"]  # 这些类型模板已生成完整的年份×党派子问题

            if self.enable_kg_expansion and self.kg_manager and question_type not in skip_kg_types:
                intent = state.get("intent", "complex")
                kg_queries, kg_expansion_info = self._apply_knowledge_graph_expansion(
                    question, intent, question_type, parameters
                )
                if kg_queries:
                    # 将知识图谱扩展查询作为额外的子问题添加
                    sub_questions = self._merge_kg_queries(sub_questions, kg_queries)
                    logger.info(f"[EnhancedDecomposeNode] 知识图谱扩展后，总子问题数: {len(sub_questions)}")
            elif question_type in skip_kg_types:
                logger.info(f"[EnhancedDecomposeNode] {question_type}问题跳过KG扩展（模板已完整覆盖）")

            # 更新状态
            return update_state(
                state,
                sub_questions=sub_questions,
                is_decomposed=True,
                current_node="decompose",
                next_node="retrieve",
                metadata={
                    **(state.get("metadata", {}) or {}),
                    "kg_expansion": kg_expansion_info
                } if kg_expansion_info else state.get("metadata", {})
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
        判断是否需要拆解（增强版：基于维度分析）

        核心原则：简单问题 = 单一时间 + 单一对象 + 无变化/对比

        Args:
            question_type: 问题类型
            parameters: 提取的参数

        Returns:
            是否需要拆解
        """
        time_range = parameters.get("time_range", {})
        parties = parameters.get("parties", [])
        speakers = parameters.get("speakers", [])
        specific_years = time_range.get("specific_years", [])
        start_year = time_range.get("start_year")
        end_year = time_range.get("end_year")

        # ========== 维度分析 ==========

        # 时间维度：计算年份数量
        year_count = len(specific_years) if specific_years else 0
        if not year_count and start_year and end_year:
            try:
                year_count = int(end_year) - int(start_year) + 1
            except:
                year_count = 1
        elif not year_count and start_year:
            year_count = 1

        # 对象维度：计算对象数量
        party_count = len(parties) if parties else 0
        # "ALL_PARTIES" 算作多对象
        if parties and "ALL_PARTIES" in parties:
            party_count = 6  # 假设有6个主要政党
        speaker_count = len(speakers) if speakers else 0
        object_count = max(party_count, speaker_count, 1)

        logger.info(f"[_need_decompose] 维度分析: 年份数={year_count}, 对象数={object_count}, 问题类型={question_type}")

        # ========== 快速判断：简单问题不拆解 ==========

        # 条件：单一时间（<=1年） + 单一对象（<=1个） + 非变化/对比类
        is_single_time = year_count <= 1
        is_single_object = object_count <= 1
        is_fact_query = question_type in ["事实查询", "总结类", None, ""]

        if is_single_time and is_single_object and is_fact_query:
            logger.info(f"[_need_decompose] → 不拆解（单一时间+单一对象+事实查询）")
            return False

        # ========== 复杂问题拆解条件 ==========

        # 变化类、对比类、趋势分析：始终拆解
        if question_type in ["变化类", "对比类", "趋势分析"]:
            logger.info(f"[_need_decompose] → 需要拆解（{question_type}类问题）")
            return True

        # 多年份（>2年）：需要拆解
        if year_count > 2:
            logger.info(f"[_need_decompose] → 需要拆解（年份数={year_count} > 2）")
            return True

        # 多对象（>1个）：需要拆解
        if object_count > 1:
            logger.info(f"[_need_decompose] → 需要拆解（对象数={object_count} > 1）")
            return True

        # 默认不拆解
        logger.info(f"[_need_decompose] → 不拆解（默认）")
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

    def _calculate_max_sub_questions(
        self,
        question_type: str,
        parameters: Dict
    ) -> int:
        """
        根据问题类型和参数动态计算子问题上限

        策略：
        - 变化类：年份数 × 党派数 + 1（总结问题），最多30
        - 对比类：年份数 × 党派数 + 1（对比问题），最多20
        - 总结类/事实查询：固定5个
        - 其他：默认10个

        Args:
            question_type: 问题类型
            parameters: 问题参数

        Returns:
            子问题数量上限
        """
        time_range = parameters.get("time_range", {})
        parties = parameters.get("parties", [])
        specific_years = time_range.get("specific_years", [])

        # 计算年份数量
        year_count = len(specific_years) if specific_years else 1
        if not year_count:
            start = time_range.get("start_year")
            end = time_range.get("end_year")
            if start and end:
                try:
                    year_count = int(end) - int(start) + 1
                except:
                    year_count = 1

        # 计算党派数量
        party_count = len(parties) if parties else 1

        # 根据问题类型动态计算
        if question_type == "变化类":
            # 变化类：每年每党派1个 + 1个总结问题
            max_q = year_count * party_count + 1
            max_q = min(max_q, 30)  # 上限30
            logger.info(f"[_calculate_max] 变化类: {year_count}年 × {party_count}党派 + 1 = {max_q}")
            return max_q

        elif question_type == "对比类":
            # 对比类：每年每党派1个 + 对比问题
            max_q = year_count * party_count + year_count  # 每年一个对比问题
            max_q = min(max_q, 20)  # 上限20
            logger.info(f"[_calculate_max] 对比类: {year_count}年 × {party_count}党派 = {max_q}")
            return max_q

        elif question_type in ["总结类", "事实查询", ""]:
            # 简单问题：固定5个
            logger.info(f"[_calculate_max] {question_type or '默认'}: 固定5个")
            return 5

        else:
            # 趋势分析等其他类型：默认10个
            logger.info(f"[_calculate_max] {question_type}: 默认10个")
            return 10

    def _validate_sub_questions(
        self,
        sub_questions: List,
        original_question: str,
        state: Dict = None
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

        # 【智能限制】根据问题类型动态调整子问题上限
        # - 变化类/对比类：按年份×党派生成，需要更多子问题
        # - 总结类/事实查询：保持较少子问题
        if state:
            max_sub_questions = self._calculate_max_sub_questions(
                state.get("question_type", ""),
                state.get("parameters", {})
            )
        else:
            max_sub_questions = 10  # 默认值

        if len(unique_questions) > max_sub_questions:
            logger.warning(f"[EnhancedDecomposeNode] 子问题过多({len(unique_questions)})，截取前{max_sub_questions}个")
            unique_questions = unique_questions[:max_sub_questions]

        logger.info(f"[EnhancedDecomposeNode] 验证后子问题数: {len(unique_questions)}")

        return unique_questions

    # ========== 【Day 4增强】知识图谱扩展相关方法 ==========

    def _apply_knowledge_graph_expansion(
        self,
        question: str,
        intent: str,
        question_type: str,
        parameters: Dict
    ) -> tuple:
        """
        应用知识图谱扩展

        Args:
            question: 原问题
            intent: 问题意图
            question_type: 问题类型
            parameters: 问题参数

        Returns:
            (扩展查询列表, 扩展信息字典)
        """
        if not self.kg_manager:
            return [], None

        try:
            logger.info("[EnhancedDecomposeNode] 开始知识图谱扩展...")

            # 调用知识图谱扩展
            use_kg, expansion_queries, kg_info = self.kg_manager.expand_query(
                question=question,
                intent=intent,
                question_type=question_type,
                parameters=parameters
            )

            if use_kg and expansion_queries:
                logger.info(f"[EnhancedDecomposeNode] 知识图谱触发成功:")
                logger.info(f"  - 扩展级别: {kg_info.get('expansion_level', 'unknown')}")
                logger.info(f"  - 评分: {kg_info.get('score', 0)}")
                logger.info(f"  - 触发原因: {kg_info.get('reasons', [])}")
                logger.info(f"  - 扩展查询数: {len(expansion_queries)}")

                # 记录前5个扩展查询
                for i, eq in enumerate(expansion_queries[:5], 1):
                    logger.debug(f"    扩展查询{i}: {eq}")
                if len(expansion_queries) > 5:
                    logger.debug(f"    ... 共{len(expansion_queries)}个扩展查询")

                return expansion_queries, kg_info
            else:
                logger.info(f"[EnhancedDecomposeNode] 知识图谱未触发: {kg_info.get('reasons', [])}")
                return [], kg_info

        except Exception as e:
            logger.error(f"[EnhancedDecomposeNode] 知识图谱扩展失败: {e}")
            return [], {"error": str(e)}

    def _merge_kg_queries(
        self,
        sub_questions: List[Dict],
        kg_queries: List[str]
    ) -> List[Dict]:
        """
        将知识图谱扩展查询合并到子问题列表中

        Args:
            sub_questions: 原子问题列表
            kg_queries: 知识图谱扩展查询列表

        Returns:
            合并后的子问题列表
        """
        # 去重：检查扩展查询是否已存在于子问题中
        existing_questions = set()
        for sq in sub_questions:
            q_text = sq.get("question", "") if isinstance(sq, dict) else str(sq)
            existing_questions.add(q_text.lower().strip())

        # 添加不重复的扩展查询
        new_kg_questions = []
        for query in kg_queries:
            if query.lower().strip() not in existing_questions:
                new_kg_questions.append({
                    "question": query,
                    "target_year": None,
                    "target_party": None,
                    "retrieval_strategy": "kg_expansion",  # 标记为知识图谱扩展
                    "source": "knowledge_graph"  # 标记来源
                })
                existing_questions.add(query.lower().strip())

        # 合并：原子问题 + 知识图谱扩展查询
        merged = sub_questions + new_kg_questions

        # 【优化】KG扩展只用于总结类/事实查询，限制合理数量（15个）
        # 变化类/对比类已在调用处跳过，不会进入此方法
        max_total = 15  # 原子问题 + KG扩展的合理上限
        if len(merged) > max_total:
            logger.warning(f"[EnhancedDecomposeNode] 合并后子问题过多({len(merged)})，截取前{max_total}个")
            # 优先保留原子问题，KG扩展作为补充
            if len(sub_questions) >= max_total:
                merged = sub_questions[:max_total]
            else:
                # 保留所有原子问题，截取部分KG扩展
                remaining = max_total - len(sub_questions)
                merged = sub_questions + new_kg_questions[:remaining]

        logger.info(f"[EnhancedDecomposeNode] 知识图谱合并: 原{len(sub_questions)}个 + KG扩展{len(new_kg_questions)}个 = {len(merged)}个")

        return merged


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

