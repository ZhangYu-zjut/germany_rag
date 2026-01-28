"""
增强版意图判断节点
包含问题合法性检查、双语支持、异常处理
"""

import re
from typing import Dict, Tuple, Optional
from ...llm.client import GeminiLLMClient
from ...llm.prompts import PromptTemplates
from ...llm.prompts_fallback import FallbackPrompts
from ...utils.logger import logger
from ...utils.language_detect import detect_language, get_system_capabilities
from ...utils.performance_monitor import get_performance_monitor
from ..state import GraphState, update_state


class EnhancedIntentNode:
    """
    增强版意图判断节点
    
    新增功能:
    1. 问题合法性检查（在意图判断之前）
    2. 语言检测
    3. 处理特殊情况:
       - 元问题（"你会做什么？"）
       - 不相关问题
       - 模糊不清的问题
       - 超出数据范围的问题
    4. 双语支持（中文/德文）
    
    原有功能:
    1. 分析问题复杂度
    2. 判断是否需要拆解
    3. 决定后续处理路径
    """
    
    def __init__(self, llm_client: GeminiLLMClient = None):
        """
        初始化增强版意图判断节点
        
        Args:
            llm_client: LLM客户端,如果为None则自动创建
        """
        self.llm = llm_client or GeminiLLMClient()
        self.prompts = PromptTemplates()
        self.fallback_prompts = FallbackPrompts()
        
    def __call__(self, state: GraphState) -> GraphState:
        """
        执行增强版意图判断
        
        流程:
        1. 检测语言
        2. 问题合法性检查
        3. 如果是特殊情况，直接返回对应响应
        4. 否则继续正常的意图判断
        
        Args:
            state: 当前状态
            
        Returns:
            更新后的状态
        """
        # 性能监控开始
        import time
        start_time = time.time()
        monitor = get_performance_monitor()
        
        logger.info(f"[EnhancedIntentNode] 开始处理问题: {state}")
        
        # 提取问题文本并进行类型检查
        question = state["question"]
        logger.info(f"[EnhancedIntentNode] 提取的question类型: {type(question)}, 值: {repr(question)}")
        
        # 确保 question 是字符串
        if not isinstance(question, str):
            logger.error(f"[EnhancedIntentNode] question不是字符串: {type(question)} = {repr(question)}")
            return update_state(
                state,
                error=f"问题格式错误: 期望字符串，得到 {type(question).__name__}",
                error_type="VALIDATION_ERROR",
                current_node="intent_analysis",
                next_node="exception"
            )
        
        try:
            # Step 1: 检测语言
            language = detect_language(question)
            logger.info(f"[EnhancedIntentNode] 检测到语言: {language}")
            
            # Step 2: 问题合法性检查
            validation_result = self._validate_question(question)
            
            logger.info(f"[EnhancedIntentNode] 合法性检查结果: {validation_result['建议处理方式']}")
            
            # Step 3: 处理特殊情况
            if validation_result["建议处理方式"] != "正常处理":
                return self._handle_special_case(
                    state, 
                    validation_result, 
                    language
                )
            
            # Step 4: 正常的意图判断
            return self._normal_intent_classification(state)
            
        except Exception as e:
            logger.error(f"[EnhancedIntentNode] 处理失败: {str(e)}")
            return update_state(
                state,
                error=f"问题处理失败: {str(e)}",
                error_type="UNKNOWN",
                current_node="intent",
                next_node="exception"
            )
    
    def _validate_question(self, question: str) -> Dict:
        """
        问题合法性检查
        
        Args:
            question: 用户问题
            
        Returns:
            验证结果字典
        """
        try:
            # 构建Prompt
            prompt = self.fallback_prompts.format_validation_prompt(question)
            
            # 调用LLM
            response = self.llm.invoke(prompt)
            
            logger.debug(f"[EnhancedIntentNode] 合法性检查响应: {response[:200]}...")
            
            # 解析响应
            validation = self._parse_validation_response(response)
            
            return validation
            
        except Exception as e:
            logger.error(f"[EnhancedIntentNode] 合法性检查失败: {str(e)}")
            # 失败时默认认为是正常问题
            return {
                "问题类型": "德国议会相关",
                "建议处理方式": "正常处理",
                "是否可处理": "是"
            }
    
    def _parse_validation_response(self, response: str) -> Dict:
        """
        解析合法性检查响应
        
        Args:
            response: LLM响应
            
        Returns:
            解析后的字典
        """
        result = {
            "问题类型": "德国议会相关",
            "信息完整性": "完整",
            "数据范围": "在范围内",
            "是否可处理": "是",
            "建议处理方式": "正常处理",
            "理由": ""
        }
        
        lines = response.strip().split('\n')
        for line in lines:
            line = line.strip()
            if ':' in line or '：' in line:
                key, value = line.split(':', 1) if ':' in line else line.split('：', 1)
                key = key.strip().replace('**', '').replace('【', '').replace('】', '')
                value = value.strip().replace('[', '').replace(']', '')
                
                if key in result:
                    result[key] = value
        
        return result
    
    def _handle_special_case(
        self, 
        state: GraphState, 
        validation: Dict, 
        language: str
    ) -> GraphState:
        """
        处理特殊情况
        
        Args:
            state: 当前状态
            validation: 验证结果
            language: 语言
            
        Returns:
            更新后的状态
        """
        question = state["question"]
        处理方式 = validation["建议处理方式"]
        
        logger.info(f"[EnhancedIntentNode] 处理特殊情况: {处理方式}")
        
        # 1. 系统功能查询
        if 处理方式 == "系统功能说明":
            message = get_system_capabilities(language=language, question=question)
            
            return update_state(
                state,
                final_answer=message,
                error_type="系统功能查询",
                language=language,
                current_node="intent",
                next_node="end"  # 直接结束，不需要exception节点
            )
        
        # 2. 不相关问题
        elif 处理方式 == "拒绝回答" and validation["问题类型"] == "完全不相关":
            message = self.fallback_prompts.format_irrelevant_response(question)
            
            return update_state(
                state,
                final_answer=message,
                error="不相关问题",
                error_type="不相关",
                language=language,
                current_node="intent",
                next_node="end"
            )
        
        # 3. 信息不足 - 【修复】改为继续尝试检索，而不是直接结束
        elif 处理方式 == "引导补充信息":
            # 【Phase 4 修复】即使LLM判断信息不足，仍然尝试检索
            # 因为问题中可能包含speaker名称等有效信息
            # 如果检索结果为空，会在exception节点处理
            logger.info(f"[EnhancedIntentNode] 问题可能信息不足，但继续尝试检索: {question[:50]}...")

            # 继续进入正常的意图分类流程
            return self._normal_intent_classification(state)
        
        # 4. 超出范围
        elif 处理方式 == "拒绝回答" and validation["数据范围"] == "超出范围":
            # 简化处理：通用的超出范围消息
            message = """抱歉，您询问的内容超出了本系统的数据范围。

【系统数据范围】
本系统收录德国联邦议院演讲记录，时间范围：**1949年至2025年**

【建议】
请确保您询问的时间在1949-2025年之间。

如有其他在数据范围内的问题，欢迎继续提问！"""
            
            return update_state(
                state,
                final_answer=message,
                error="超出数据范围",
                error_type="超出范围",
                language=language,
                current_node="intent",
                next_node="end"
            )
        
        # 5. 其他情况，尝试继续处理
        else:
            logger.warning(f"[EnhancedIntentNode] 未知处理方式: {处理方式}，继续正常流程")
            return self._normal_intent_classification(state)
    
    def _normal_intent_classification(self, state: GraphState) -> GraphState:
        """
        正常的意图判断流程（原有逻辑）
        
        Args:
            state: 当前状态
            
        Returns:
            更新后的状态
        """
        question = state["question"]
        logger.info(f"[_normal_intent_classification] question类型: {type(question)}, 值: {repr(question)}")
        
        try:
            # 后处理规则1: 如果问题明显是简单问题，先检查
            intent_by_rule = self._check_simple_by_rule(question)
            if intent_by_rule == "simple":
                logger.info(f"[EnhancedIntentNode] 规则判断为simple: {question[:50]}...")
                return update_state(
                    state,
                    intent="simple",
                    complexity_analysis="规则判断：单一时间点 + 单一对象，属于简单问题",
                    current_node="intent",
                    next_node="extract"
                )
            
            # 构建Prompt
            prompt = self.prompts.format_intent_prompt(question)
            
            # 调用LLM
            response = self.llm.invoke(prompt)
            
            logger.debug(f"[EnhancedIntentNode] 意图判断响应: {response[:200]}...")
            
            # 解析响应
            intent, complexity_analysis = self._parse_intent_response(response)
            
            # 后处理规则2: 如果LLM判断为complex，但问题明显是simple，强制纠正
            if intent == "complex":
                rule_check = self._check_simple_by_rule(question)
                if rule_check == "simple":
                    logger.warning(f"[EnhancedIntentNode] LLM判断为complex，但规则判断为simple，强制纠正: {question[:50]}...")
                    intent = "simple"
                    complexity_analysis = f"强制纠正：{complexity_analysis} [规则：单一时间点+单一对象=简单]"
            
            logger.info(f"[EnhancedIntentNode] 意图判断结果: {intent}")
            
            # 更新状态
            return update_state(
                state,
                intent=intent,
                complexity_analysis=complexity_analysis,
                current_node="intent",
                next_node="classify" if intent == "complex" else "extract"
            )
            
        except Exception as e:
            logger.error(f"[EnhancedIntentNode] 意图判断失败: {str(e)}")
            return update_state(
                state,
                error=f"意图判断失败: {str(e)}",
                error_type="LLM_ERROR",
                current_node="intent",
                next_node="exception"
            )
    
    def _check_simple_by_rule(self, question: str) -> Optional[str]:
        """
        基于语义规则的简单/复杂问题检查（支持中德双语）

        核心原则：简单问题 = 单一时间 + 单一对象 + 无变化/对比

        检查维度：
        1. 时间维度：单一年份 vs 多年份/时间跨度
        2. 对象维度：单一党派/人物 vs 多个党派/人物
        3. 分析类型：陈述事实 vs 变化/对比/趋势分析

        Args:
            question: 用户问题（中文或德文）

        Returns:
            "simple" - 明确是简单问题
            "complex" - 明确是复杂问题
            None - 不确定，让LLM判断
        """
        import re

        # 类型检查和转换
        if not isinstance(question, str):
            logger.error(f"[_check_simple_by_rule] question不是字符串类型: {type(question)}, 值: {repr(question)}")
            try:
                question = str(question)
            except Exception as e:
                logger.error(f"[_check_simple_by_rule] 转换失败: {e}")
                return None

        # ========== 维度1: 时间分析 ==========
        # 提取所有年份（支持多种格式）
        years_cn = re.findall(r'(\d{4})年', question)  # 中文：2019年
        years_de = re.findall(r'(?:im Jahr(?:e)?|in|von|bis|seit)\s*(\d{4})', question, re.IGNORECASE)  # 德语
        years_standalone = re.findall(r'\b((?:19|20)\d{2})\b', question)  # 独立年份

        # 合并去重
        all_years = list(set(years_cn + years_de + years_standalone))
        year_count = len(all_years)

        logger.debug(f"[_check_simple_by_rule] 检测到年份: {all_years} (共{year_count}个)")

        # 复杂时间模式检测（中德双语）
        complex_time_patterns = [
            # 中文时间跨度
            r'\d{4}.*到.*\d{4}', r'从.*\d{4}.*到', r'期间', r'跨度', r'以来',
            # 德语时间跨度
            r'seit\s+\d{4}', r'von\s+\d{4}\s+bis', r'zwischen\s+\d{4}\s+und',
            r'im Zeitraum', r'in den Jahren', r'über die Jahre',
        ]
        has_time_span = any(re.search(p, question, re.IGNORECASE) for p in complex_time_patterns)

        # ========== 维度2: 对象分析 ==========
        # 德国主要政党识别逻辑
        # 注意：CDU/CSU 应该被视为一个党派

        mentioned_parties = set()

        # 特殊处理：先检查CDU/CSU复合名称
        has_cdu_csu_combined = bool(re.search(r'CDU\s*/\s*CSU', question, re.IGNORECASE))

        if has_cdu_csu_combined:
            # 如果有CDU/CSU，只算一个党派
            mentioned_parties.add('CDU/CSU')
        else:
            # 如果没有CDU/CSU，分别检查CDU和CSU
            if re.search(r'\bCDU\b', question, re.IGNORECASE):
                mentioned_parties.add('CDU')
            if re.search(r'\bCSU\b', question, re.IGNORECASE):
                mentioned_parties.add('CSU')

        # 其他党派检测
        other_party_patterns = [
            (r'\bSPD\b', 'SPD'),
            (r'\bFDP\b', 'FDP'),
            (r'Grüne|GRÜNE|Bündnis\s*90|BÜNDNIS\s*90', 'Grüne'),
            (r'DIE\s+LINKE|\bLINKE\b', 'LINKE'),
            (r'\bAfD\b', 'AfD'),
            (r'基民盟|基社盟', 'CDU/CSU'),
            (r'社民党', 'SPD'),
            (r'绿党', 'Grüne'),
            (r'自民党', 'FDP'),
            (r'左翼党', 'LINKE'),
        ]

        for pattern, party_name in other_party_patterns:
            if re.search(pattern, question, re.IGNORECASE):
                mentioned_parties.add(party_name)

        party_count = len(mentioned_parties)

        logger.debug(f"[_check_simple_by_rule] 检测到党派: {mentioned_parties} (共{party_count}个)")

        # 多对象模式检测（中德双语）
        multi_object_patterns = [
            # 中文多对象
            r'不同党派', r'多个党派', r'各党派', r'各个党派',
            r'.*与.*对比', r'.*和.*差异', r'.*与.*相比',
            # 德语多对象
            r'verschiedene[nr]?\s+Parteien', r'die Parteien', r'alle[nr]?\s+Parteien',
            r'unterschiedliche[nr]?', r'im Vergleich zu', r'verglichen mit',
            r'der Parteien',  # 各党派的
        ]
        has_multi_object = any(re.search(p, question, re.IGNORECASE) for p in multi_object_patterns)

        # ========== 维度3: 分析类型 ==========
        # 变化/对比/趋势模式（中德双语）
        change_patterns = [
            # 中文
            r'变化', r'演变', r'趋势', r'发展', r'转变', r'对比', r'比较', r'差异',
            # 德语名词
            r'Veränderung', r'Wandel', r'Entwicklung', r'Trend',
            r'Vergleich', r'Unterschied', r'Differenz',
            # 德语动词（各种变位形式）
            r'veränder',  # verändert, veränderten, verändere, etc.
            r'gewandelt', r'entwickel',
            r'vergleich', r'unterscheid',
            # 德语句式
            r'wie hat sich.*verändert', r'was hat sich.*geändert',
            r'hat sich.*gewandelt', r'haben sich.*verändert',
        ]
        has_change_analysis = any(re.search(p, question, re.IGNORECASE) for p in change_patterns)

        # ========== 综合判断 ==========

        # 明确是复杂问题的情况
        if has_time_span or year_count > 2:
            logger.info(f"[_check_simple_by_rule] → COMPLEX (时间跨度: {has_time_span}, 年份数: {year_count})")
            return "complex"

        if has_multi_object or party_count > 1:
            logger.info(f"[_check_simple_by_rule] → COMPLEX (多对象: {has_multi_object}, 党派数: {party_count})")
            return "complex"

        if has_change_analysis:
            logger.info(f"[_check_simple_by_rule] → COMPLEX (变化/对比分析)")
            return "complex"

        # 明确是简单问题的情况：单一时间 + 单一对象 + 无变化分析
        if year_count <= 1 and party_count <= 1 and not has_change_analysis:
            # 额外检查：确保问的是事实/立场/观点类问题（中德双语）
            fact_patterns = [
                # 中文
                r'主要议题', r'主要观点', r'立场', r'说了什么', r'讨论了什么',
                r'观点是什么', r'什么立场', r'什么观点', r'有哪些',
                # 德语
                r'Position', r'Standpunkt', r'Haltung', r'Meinung', r'Ansicht',
                r'was war', r'was waren', r'was ist', r'was sind',
                r'welche.*Position', r'welche.*Themen', r'welche.*Punkte',
            ]
            is_fact_question = any(re.search(p, question, re.IGNORECASE) for p in fact_patterns)

            if is_fact_question:
                logger.info(f"[_check_simple_by_rule] → SIMPLE (单一时间+单一对象+事实查询)")
                return "simple"

            # 即使没有明确的事实模式词，单一时间+单一对象也倾向于简单
            # 但让LLM最终确认
            logger.info(f"[_check_simple_by_rule] → 倾向SIMPLE (单一时间+单一对象)，让LLM确认")
            return "simple"

        # 其他情况让LLM判断
        logger.debug(f"[_check_simple_by_rule] → None (让LLM判断)")
        return None
    
    def _parse_intent_response(self, response: str) -> Tuple[str, str]:
        """
        解析意图判断响应
        
        Args:
            response: LLM响应
            
        Returns:
            (intent, complexity_analysis)
        """
        # 默认值
        intent = "simple"
        complexity_analysis = response
        
        # 规则解析
        response_lower = response.lower()
        
        # 优先级1: 直接查找"复杂度:"行（Prompt要求的标准格式）
        if "复杂度:" in response:
            # 提取复杂度行
            for line in response.split('\n'):
                if "复杂度:" in line:
                    # 提取冒号后的内容，避免"复杂度"中的"复杂"干扰
                    # 匹配"复杂度:"后面的内容（可能包含空格）
                    match = re.search(r'复杂度:\s*([^\n]+)', line)
                    if match:
                        value = match.group(1).strip().lower()
                        if "简单" in value or "simple" in value:
                            intent = "simple"
                        elif "复杂" in value or "complex" in value:
                            intent = "complex"
                    else:
                        # 如果没有匹配到，使用原始逻辑但先检查简单
                        line_lower = line.lower()
                        if ": 简单" in line or ":简单" in line or ("simple" in line_lower and "complex" not in line_lower):
                            intent = "simple"
                        elif ": 复杂" in line or ":复杂" in line:
                            intent = "complex"
                    break
        
        # 优先级2: 查找明确的"简单"或"复杂"标记（仅在优先级1未匹配时执行）
        # 注意：如果优先级1匹配到了"复杂度:"，会break，不会到这里
        # 所以这里只处理没有"复杂度:"行的响应
        elif "简单" in response or "simple" in response_lower:
            intent = "simple"
        elif "复杂" in response or "complex" in response_lower:
            intent = "complex"
        
        # 优先级3: 根据明确的复杂特征关键词判断（排除"分析"这个太宽泛的词）
        else:
            # 只使用明确的复杂特征关键词
            complex_keywords = [
                "时间跨度", 
                "多个对象", 
                "多个党派",
                "不同党派",
                "对比", 
                "趋势", 
                "变化",
                "演变",
                "差异",
                "异同"
            ]
            # 检查是否包含复杂关键词
            has_complex_keyword = any(kw in response for kw in complex_keywords)
            
            # 同时检查是否明确说明是简单问题
            simple_indicators = ["单一时间点", "单一对象", "单一党派", "事实查询", "观点总结"]
            has_simple_indicator = any(indicator in response for indicator in simple_indicators)
            
            if has_complex_keyword and not has_simple_indicator:
                intent = "complex"
            elif has_simple_indicator:
                intent = "simple"
            # 否则保持默认的simple
        
        logger.debug(f"[EnhancedIntentNode] 解析结果: intent={intent}, 响应片段={response[:100]}")
        
        return intent, complexity_analysis


# 为了保持向后兼容，创建一个别名
IntentNode = EnhancedIntentNode


if __name__ == "__main__":
    # 测试增强版意图判断节点
    from ..state import create_initial_state
    
    print("=== 增强版IntentNode测试 ===\n")
    
    # 测试1: 元问题
    print("【测试1: 元问题】")
    question = "你会做什么？"
    state = create_initial_state(question)
    node = EnhancedIntentNode()
    result = node(state)
    print(f"问题: {question}")
    print(f"结果: {result.get('error_type', 'NORMAL')}")
    print(f"下一节点: {result['next_node']}")
    if result.get('final_answer'):
        print(f"回答预览: {result['final_answer'][:100]}...")
    print()
    
    # 测试2: 正常简单问题
    print("【测试2: 正常简单问题】")
    question = "2019年德国议会讨论了哪些主要议题？"
    state = create_initial_state(question)
    result = node(state)
    print(f"问题: {question}")
    print(f"意图: {result.get('intent', 'N/A')}")
    print(f"下一节点: {result['next_node']}")
    print()
    
    # 测试3: 正常复杂问题
    print("【测试3: 正常复杂问题】")
    question = "在2015-2018年期间，不同党派在难民政策上的立场有何变化？"
    state = create_initial_state(question)
    result = node(state)
    print(f"问题: {question}")
    print(f"意图: {result.get('intent', 'N/A')}")
    print(f"下一节点: {result['next_node']}")
    print()
    
    print("注意: 完整测试需要启动Milvus和LLM服务")

