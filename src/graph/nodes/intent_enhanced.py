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
        基于规则的简单问题检查（后处理兜底）
        
        检查条件：
        1. 单一时间点（只有一个年份，如"2019年"、"2021年"）
        2. 单一对象（没有"不同党派"、"多个党派"、"XX与XX"等）
        3. 问的是"主要议题"、"主要观点"、"立场"、"说了什么"等
        
        如果满足条件，返回"simple"，否则返回None（让LLM判断）
        
        Args:
            question: 用户问题
            
        Returns:
            "simple" 或 None
        """
        import re
        
        # 类型检查和转换
        if not isinstance(question, str):
            logger.error(f"[_check_simple_by_rule] question不是字符串类型: {type(question)}, 值: {repr(question)}")
            # 尝试转换为字符串
            try:
                question = str(question)
                logger.info(f"[_check_simple_by_rule] 成功转换为字符串: {question}")
            except Exception as e:
                logger.error(f"[_check_simple_by_rule] 转换失败: {e}")
                return None
        
        # 检查1: 时间维度
        # 查找所有年份
        years = re.findall(r'\d{4}年', question)
        
        # 如果包含时间跨度关键词，直接返回None（让LLM判断为complex）
        if re.search(r'\d{4}.*到.*\d{4}|从.*\d{4}.*到|期间|跨度', question):
            return None
        
        # 如果包含"变化"、"演变"、"趋势"，返回None（让LLM判断为complex）
        if re.search(r'变化|演变|趋势|对比', question):
            return None
        
        # 如果只有一个年份或没有年份
        if len(years) <= 1:
            # 检查2: 对象维度
            # 如果包含多个对象的标识
            if re.search(r'不同党派|多个党派|.*与.*|.*和.*对比|.*和.*差异', question):
                return None
            
            # 检查3: 问题类型
            # 如果问的是"主要议题"、"主要观点"、"立场"、"说了什么"、"讨论了什么"
            if re.search(r'主要议题|主要观点|立场|说了什么|讨论了什么|观点是什么', question):
                # 满足条件：单一时间点 + 单一对象 + 问主要议题/主要观点
                logger.debug(f"[EnhancedIntentNode] 规则匹配：单一时间点+单一对象+主要议题/观点 → simple")
                return "simple"
        
        # 其他情况让LLM判断
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

