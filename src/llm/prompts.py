"""
Prompt模板模块
定义各类任务的Prompt模板
"""

from typing import Dict, List, Optional


class PromptTemplates:
    """
    Prompt模板管理器
    
    包含:
    1. 系统Prompt
    2. 意图判断Prompt
    3. 问题分类Prompt
    4. 参数提取Prompt
    5. 问题拆解Prompt
    6. 总结Prompt
    """
    
    # ========== 系统Prompt ==========
    
    SYSTEM_PROMPT = """你是一个专业的德国议会文档分析助手。

你的职责是:
1. 帮助用户理解和分析德国联邦议院的演讲记录
2. 准确提取和总结相关信息
3. 基于提供的材料进行回答,不要编造内容
4. 如果材料中没有相关信息,明确告知用户

注意事项:
- 保持客观中立的立场
- 准确引用原文内容
- 必要时注明引用来源(发言人、时间、党派等)
- 避免主观臆断和过度推理
"""
    
    # ========== 意图判断Prompt ==========
    
    INTENT_CLASSIFICATION = """你是一个问题复杂度分析专家。请判断以下问题的复杂程度。

【重要】用户可能使用中文或德文提问，请都能正确处理。

用户问题: {question}

【⚠️ 必须首先理解的核心原则（违反此原则的判断都是错误的）】

**规则1: "主要议题"、"主要观点"这类问题，如果只有单一时间点和单一对象，永远判断为"简单"！**

❌ 错误理解：认为"主要议题"需要从多个议题中筛选，所以是复杂问题
✅ 正确理解：只要时间点和对象都是单一的，问"主要议题"、"主要观点"就是简单问题

**规则2: 只看维度数量，不看是否需要"总结"或"筛选"！**

即使问题中出现了"总结"、"主要"、"筛选"等词汇，只要：
- 只有一个时间点（如"2019年"、"2021年"）
- 只有一个对象（单一党派、单一议员、或整体议会）

那么这个问题的复杂度就是"简单"！

【判断流程（必须严格按照此流程）】

第一步：检查时间维度
- 查找问题中的时间表达
- 如果包含时间跨度（如"2015-2018年"、"从...到..."、"期间"）→ 直接判断为"复杂"，结束
- 如果包含"变化"、"演变"、"趋势"（这些词暗示需要对比时间点）→ 直接判断为"复杂"，结束
- 如果只有一个时间点（如"2019年"、"2021年"）或没有明确时间 → 继续第二步

第二步：检查对象维度
- 查找问题中的对象表达
- 如果提到"不同党派"、"多个党派"、"XX与XX"、"XX和XX对比" → 直接判断为"复杂"，结束
- 如果只有一个党派/议员/或整体议会 → 继续第三步

第三步：如果通过了前两步（单一时间点 + 单一对象）→ 必须判断为"简单"
- 无论问题问的是"主要议题"、"主要观点"、"立场"、"说了什么"、"讨论了什么"
- 无论问题中是否出现"总结"、"主要"、"筛选"等词汇
- 只要维度单一，就必须判断为"简单"！

【禁止性规则（这些理解是错误的）】

❌ 禁止：看到"主要议题"就认为需要综合分析 → 这是错误的！
❌ 禁止：看到"主要观点"就认为需要总结多个观点 → 这是错误的！
❌ 禁止：因为问题问"哪些议题"（复数）就认为需要对比 → 这是错误的！
✅ 正确：单一时间点 + 单一对象 + 问"主要议题/主要观点" = 简单问题

【标准答案示例（必须完全按照这些示例判断）】

示例1（必须判断为"简单"）:
问题: "2019年德国议会讨论了哪些主要议题?"
第一步: 单一时间点（2019年）✓
第二步: 单一对象（整体议会）✓
第三步: 简单（维度单一）
**标准答案: 复杂度: 简单**

示例2（必须判断为"简单"）:
问题: "2021年绿党在气候保护方面的主要观点是什么？"
第一步: 单一时间点（2021年）✓
第二步: 单一对象（绿党）✓
第三步: 简单（维度单一）
**标准答案: 复杂度: 简单**

示例3（判断为"复杂"）:
问题: "在2015年到2018年期间,不同党派在难民问题上的立场有何变化?"
第一步: 时间跨度（2015-2018年）→ 复杂
**标准答案: 复杂度: 复杂**

【输出格式（必须严格按照此格式）】

复杂度: [简单/复杂]
理由: [严格按照三步流程说明]

【重要提醒】

如果用户问题类似于示例1或示例2（单一时间点 + 单一对象 + "主要议题/主要观点"），
你必须严格按照示例1或示例2的判断，输出"复杂度: 简单"。

不要被"主要"、"总结"等词汇误导！维度单一就是简单问题！

现在请分析用户的问题，严格按照上述流程和示例判断。
"""
    
    # ========== 问题分类Prompt ==========
    
    QUESTION_CLASSIFICATION = """你是一个问题分类专家。请对以下问题进行精确分类。

【重要】用户可能使用中文或德文提问，请都能正确处理。

用户问题: {question}

【分类类型及特征】

1. **变化类**
   关键词: "变化"、"演变"、"如何发展"、"前后对比"
   特征: 关注同一对象在时间维度上的变化
   示例: "2015-2018年CDU对难民政策的立场有何变化?"

2. **总结类**
   关键词: "总结"、"主要观点"、"核心立场"、"主张"
   特征: 要求对某个时期/党派/议员的观点进行归纳
   示例: "请总结2019年绿党在气候保护方面的主要主张"

3. **对比类**
   关键词: "对比"、"比较"、"不同"、"差异"、"vs"
   特征: 对比不同党派/时期/议员的立场差异
   示例: "请对比CDU和SPD在2020年对数字化政策的看法"

4. **事实查询**
   关键词: "是什么"、"说了什么"、"讨论了什么"、"何时"
   特征: 查询具体事实、数据、引语
   示例: "2019年3月15日Merkel在议会上说了什么?"

5. **趋势分析**
   关键词: "趋势"、"发展"、"走向"、"态度演变"
   特征: 分析某个议题的整体发展趋势
   示例: "2010-2020年议会对核能的态度有何演变?"

【输出格式】

问题类型: [类型名称]
关键依据: [识别出的关键词或特征]
理由: [一句话说明分类依据]

【示例】
问题: "在2015年到2018年期间,不同党派在难民问题上的讨论发生了怎样的变化?"
问题类型: 变化类
关键依据: "2015年到2018年"（时间跨度）、"变化"（关键词）
理由: 询问多个党派在时间维度上的立场变化

现在请对用户的问题进行分类。只输出分类结果，不要包含其他内容。
"""
    
    # ========== 参数提取Prompt ==========
    
    PARAMETER_EXTRACTION = """你是一个信息提取专家。请从以下问题中提取结构化参数。

【最高优先级规则 - 必须严格遵守】
1. **绝对禁止翻译！** 问题中的所有词汇必须保持原样提取，不能翻译成其他语言！
2. **德语问题 → 德语关键词**：如果问题是德语（Flüchtlingspolitik, Veränderungen等），必须提取德语词汇
3. **中文问题 → 中文关键词**：如果问题是中文（难民政策、变化等），必须提取中文词汇
4. **示例**：
   - 问题含"Flüchtlingspolitik" → topics: ["Flüchtlingspolitik"]  ✅
   - 问题含"Flüchtlingspolitik" → topics: ["难民政策"]  ❌ 错误！禁止翻译！
   - 问题含"难民政策" → topics: ["难民政策"]  ✅
   - 问题含"难民政策" → topics: ["Flüchtlingspolitik"]  ❌ 错误！禁止翻译！

用户问题: {question}

【提取规则】

1. **时间范围**
   - 识别年份（如"2019年"、"2015-2018年"、"2010年到2020年" 或 "seit 2015", "von 2015 bis 2018"）
   - 识别月份/日期（如果有）
   - 识别时间表述（如"福岛核事故前后"需要标记为特殊时间点）

2. **党派**
   - 识别德语党派名称（CDU/CSU, SPD, FDP, BÜNDNIS 90/DIE GRÜNEN, DIE LINKE, AfD等）
   - 识别中文党派名称（联盟党、社会民主党、绿党、左翼党等）
   - **保持原始语言，不要翻译！**
   - 如果提到"所有党派" / "alle Parteien" / "verschiedene Parteien"，标记为: ["ALL_PARTIES"]
   - 如果未明确指定，设为: null

3. **议员**
   - 识别议员姓名（如"Merkel"、"Olaf Scholz"）
   - 保持原始格式（德文或中文）
   - 如果未提到，设为: null

4. **主题/议题**
   - 识别核心议题
   - **保持原始语言，不要翻译！**
   - 德文示例：Flüchtlingspolitik, Klimaschutz, Digitalisierung
   - 中文示例：难民政策、气候保护、数字化
   - 可以有多个主题

5. **关键词**
   - 提取其他重要关键词
   - **保持原始语言，不要翻译！**
   - 德文动作词：Veränderungen, Vergleich, Zusammenfassung
   - 中文动作词：变化、对比、总结

【输出格式】

请严格按照以下JSON格式返回，不要包含任何其他文字：

{{
    "time_range": {{
        "start_year": "YYYY或null",
        "end_year": "YYYY或null",
        "specific_date": "具体日期(如2019-03-15)或null",
        "time_expression": "特殊时间表述或null"
    }},
    "parties": ["党派1", "党派2"] 或 ["ALL_PARTIES"] 或 null,
    "speakers": ["议员1", "议员2"] 或 null,
    "topics": ["主题1", "主题2"] 或 null,
    "keywords": ["关键词1", "关键词2"]
}}

【示例1：中文问题】
问题: "在2015年到2018年期间,德国联邦议会中不同党派在难民家庭团聚问题上的讨论发生了怎样的变化?"

{{
    "time_range": {{
        "start_year": "2015",
        "end_year": "2018",
        "specific_date": null,
        "time_expression": null
    }},
    "parties": ["ALL_PARTIES"],
    "speakers": null,
    "topics": ["难民家庭团聚"],
    "keywords": ["变化", "讨论"]
}}

【示例2：德语问题 - 保持德语，不翻译！】
问题: "Bitte fassen Sie die wichtigsten Veränderungen in der Flüchtlingspolitik der CDU/CSU seit 2015 zusammen."

{{
    "time_range": {{
        "start_year": "2015",
        "end_year": "2025",
        "specific_date": null,
        "time_expression": "seit 2015"
    }},
    "parties": ["CDU/CSU"],
    "speakers": null,
    "topics": ["Flüchtlingspolitik"],
    "keywords": ["Veränderungen", "zusammenfassen"]
}}

【示例3：混合语言问题】
问题: "2019年3月15日Merkel在议会上说了什么?"

{{
    "time_range": {{
        "start_year": "2019",
        "end_year": "2019",
        "specific_date": "2019-03-15",
        "time_expression": null
    }},
    "parties": null,
    "speakers": ["Merkel"],
    "topics": null,
    "keywords": ["发言内容"]
}}

现在请提取用户问题的参数。只输出JSON，不要包含任何解释。
"""
    
    # ========== 问题拆解Prompt (模板化) ==========
    
    QUESTION_DECOMPOSITION_TEMPLATE = """根据以下参数,将复杂问题拆解为多个子问题。

原问题: {original_question}
问题类型: {question_type}
提取的参数: {parameters}

拆解策略:
- 变化类问题: 按年份×党派拆解
- 对比类问题: 按党派×时间段拆解
- 总结类问题: 按主题×时间拆解

请按照以下格式返回子问题列表:
1. [子问题1]
2. [子问题2]
3. [子问题3]
...

只返回子问题列表,每行一个子问题。
"""
    
    # ========== 问题拆解Prompt (自由拆解) ==========
    
    QUESTION_DECOMPOSITION_FREE = """请将以下复杂问题拆解为多个可独立回答的子问题。

原问题: {question}

拆解原则:
1. 每个子问题应该聚焦单一维度
2. 子问题之间应该相互独立
3. 子问题的答案组合起来能完整回答原问题
4. 尽量控制子问题数量在10个以内

请按照以下格式返回:
1. [子问题1]
2. [子问题2]
...

只返回子问题列表,不要包含解释。
"""
    
    # ========== 总结Prompt ==========
    
    SUMMARIZE_SINGLE_QUESTION = """请基于以下检索到的材料回答用户问题。

用户问题: {question}

检索材料:
{context}

要求:
1. 直接回答问题,不要偏题
2. 基于材料内容回答,不要编造
3. 引用关键信息时注明来源(发言人、时间等)
4. 如果材料不足以回答问题,明确说明

请提供简洁准确的回答。
"""
    
    SUMMARIZE_MULTIPLE_QUESTIONS = """请基于以下子问题的答案,综合回答原问题。

原问题: {original_question}

子问题及答案:
{sub_qa_pairs}

要求:
1. 综合所有子答案,形成完整回答
2. 保持逻辑清晰,结构合理
3. 突出变化、对比或趋势(根据问题类型)
4. 保留重要的引用和来源信息

请提供结构化的综合回答。
"""
    
    # ========== 格式化输出Prompt ==========
    
    FORMAT_OUTPUT_MODULAR = """请将以下回答按照指定格式进行格式化输出。

原始回答: {raw_answer}
问题类型: {question_type}

格式要求:
{format_template}

请严格按照格式要求重新组织回答内容。
"""
    
    # ========== 异常处理Prompt ==========
    
    NO_MATERIAL_FOUND = """根据检索结果,材料中未找到与您的问题相关的内容。

您的问题: {question}

可能的原因:
1. 您询问的时间范围在数据库之外
2. 您询问的主题在议会中未被讨论
3. 问题表述可能需要调整

建议:
- 尝试调整时间范围
- 使用不同的关键词重新提问
- 将问题简化或拆分

如果您需要帮助,可以尝试问一些更具体的问题,例如:
- "2019年德国联邦议院讨论了哪些主要议题?"
- "某某党派在某年对某议题的立场是什么?"
"""
    
    # ========== 工具方法 ==========
    
    @staticmethod
    def format_intent_prompt(question: str) -> str:
        """格式化意图判断Prompt"""
        return PromptTemplates.INTENT_CLASSIFICATION.format(question=question)
    
    @staticmethod
    def format_classification_prompt(question: str) -> str:
        """格式化问题分类Prompt"""
        return PromptTemplates.QUESTION_CLASSIFICATION.format(question=question)
    
    @staticmethod
    def format_extraction_prompt(question: str) -> str:
        """格式化参数提取Prompt"""
        return PromptTemplates.PARAMETER_EXTRACTION.format(question=question)
    
    @staticmethod
    def format_decomposition_prompt(
        question: str,
        question_type: str = None,
        parameters: Dict = None,
        use_template: bool = True
    ) -> str:
        """格式化问题拆解Prompt"""
        if use_template and question_type and parameters:
            return PromptTemplates.QUESTION_DECOMPOSITION_TEMPLATE.format(
                original_question=question,
                question_type=question_type,
                parameters=str(parameters)
            )
        else:
            return PromptTemplates.QUESTION_DECOMPOSITION_FREE.format(
                question=question
            )
    
    @staticmethod
    def format_summarize_prompt(
        question: str,
        context: str = None,
        sub_qa_pairs: List[Dict] = None
    ) -> str:
        """格式化总结Prompt"""
        if sub_qa_pairs:
            # 多问题总结
            qa_text = "\n\n".join([
                f"子问题{i+1}: {qa['question']}\n答案: {qa['answer']}"
                for i, qa in enumerate(sub_qa_pairs)
            ])
            return PromptTemplates.SUMMARIZE_MULTIPLE_QUESTIONS.format(
                original_question=question,
                sub_qa_pairs=qa_text
            )
        else:
            # 单问题总结
            return PromptTemplates.SUMMARIZE_SINGLE_QUESTION.format(
                question=question,
                context=context or ""
            )
    
    @staticmethod
    def format_no_material_prompt(question: str) -> str:
        """格式化无材料Prompt"""
        return PromptTemplates.NO_MATERIAL_FOUND.format(question=question)


if __name__ == "__main__":
    # 测试Prompt模板
    templates = PromptTemplates()
    
    test_question = "在2015年到2018年期间,德国联邦议会中不同党派在难民家庭团聚问题上的讨论发生了怎样的变化?"
    
    print("=== 意图判断Prompt ===")
    print(templates.format_intent_prompt(test_question))
    
    print("\n=== 问题分类Prompt ===")
    print(templates.format_classification_prompt(test_question))
    
    print("\n=== 参数提取Prompt ===")
    print(templates.format_extraction_prompt(test_question))
