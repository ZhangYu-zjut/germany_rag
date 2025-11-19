"""
兜底策略Prompt模板
处理异常、边界情况和特殊问题
"""


class FallbackPrompts:
    """兜底策略Prompt管理器"""
    
    # ========== 问题合法性检查Prompt ==========
    
    QUESTION_VALIDATION = """你是一个问题合法性检查专家。请判断以下问题是否适合本系统处理。

【系统功能说明】
本系统是德国联邦议院演讲记录智能问答系统，能够：
1. 回答关于德国联邦议院（1949-2025年）演讲记录的问题
2. 分析党派立场、议员发言、政策变化等
3. 提供基于原始材料的引用和总结

【重要】用户可能使用中文或德文提问，请都能正确处理。

【用户问题】
{question}

【检查维度】

1. **问题类型判断**
   - 系统功能查询：用户询问系统能做什么（如"你会做什么？"）
   - 德国议会相关：问题与德国联邦议院、议员、党派、政策相关
   - 完全不相关：与德国议会无关的问题
   - 模糊不清：缺少关键信息的问题

2. **信息完整性判断**
   - 完整：包含足够的时间、对象或主题信息
   - 部分缺失：缺少部分关键信息但可以处理
   - 严重缺失：缺少太多信息无法处理

3. **数据范围判断**
   - 在范围内：时间在1949-2025年之间
   - 超出范围：时间在1949年之前或2025年之后
   - 未指定：没有明确时间

【输出格式】

问题类型: [系统功能查询/德国议会相关/完全不相关/模糊不清]
信息完整性: [完整/部分缺失/严重缺失]
数据范围: [在范围内/超出范围/未指定]
是否可处理: [是/否]
建议处理方式: [正常处理/引导补充信息/系统功能说明/拒绝回答]
理由: [一句话说明]

【示例1：正常问题】
问题: "2019年CDU/CSU在气候保护方面的立场是什么？"
问题类型: 德国议会相关
信息完整性: 完整
数据范围: 在范围内
是否可处理: 是
建议处理方式: 正常处理
理由: 问题明确，信息完整，在数据范围内

【示例2：系统功能查询】
问题: "你会做什么？"
问题类型: 系统功能查询
信息完整性: 完整
数据范围: 未指定
是否可处理: 是
建议处理方式: 系统功能说明
理由: 用户询问系统功能，应提供功能介绍

【示例3：不相关问题】
问题: "今天天气怎么样？"
问题类型: 完全不相关
信息完整性: 完整
数据范围: 未指定
是否可处理: 否
建议处理方式: 拒绝回答
理由: 问题与德国议会无关

【示例4：模糊问题】
问题: "他们怎么说的？"
问题类型: 模糊不清
信息完整性: 严重缺失
数据范围: 未指定
是否可处理: 否
建议处理方式: 引导补充信息
理由: 缺少时间、人物、主题等关键信息

【示例5：超出范围】
问题: "2030年德国议会对气候政策的立场？"
问题类型: 德国议会相关
信息完整性: 完整
数据范围: 超出范围
是否可处理: 否
建议处理方式: 拒绝回答
理由: 时间超出数据范围（2030年 > 2025年）

现在请检查用户的问题。只输出检查结果，不要包含其他内容。
"""
    
    # ========== 系统功能说明 ==========
    
    SYSTEM_CAPABILITIES = """您好！我是德国联邦议院演讲记录智能问答系统。

【我能做什么】

1. **回答关于德国联邦议院的问题**
   - 时间范围：1949年至2025年
   - 数据来源：德国联邦议院官方演讲记录
   - 语言：中文或德文提问，德文回答

2. **支持的问题类型**

   ✅ **事实查询**
   - 示例："2019年德国联邦议院讨论了哪些主要议题？"
   - 示例："2020年3月15日Merkel说了什么？"

   ✅ **立场总结**
   - 示例："请总结2021年绿党在气候保护方面的主要主张"
   - 示例："2019年CDU/CSU对难民政策的立场是什么？"

   ✅ **政策变化分析**
   - 示例："在2015年到2018年期间，不同党派在难民问题上的立场有何变化？"
   - 示例："福岛核事故前后，德国议会对核能的态度有何变化？"

   ✅ **党派对比**
   - 示例："请对比CDU/CSU和SPD在2019年对数字化政策的看法"
   - 示例："2020年各党派在气候保护方面的立场有何不同？"

   ✅ **趋势分析**
   - 示例："2010-2020年议会对气候政策的态度有何演变？"

3. **我的优势**
   - ✅ 基于真实材料，不编造内容
   - ✅ 提供详细引用（发言人、时间、text_id）
   - ✅ 结构化德文输出
   - ✅ 处理复杂的多维度问题

【数据覆盖范围】

- **时间**：1949年至2025年
- **党派**：CDU/CSU、SPD、FDP、绿党、左翼党、AfD及历史党派
- **内容**：议会演讲、辩论记录、政策讨论

【提问建议】

✅ **好的问题示例**：
- 包含明确的时间（年份或时间范围）
- 指定党派或议员（可选）
- 明确主题或议题
- 表述清晰完整

❌ **不适合的问题**：
- 与德国议会无关的问题
- 时间超出1949-2025年范围
- 缺少关键信息的模糊问题
- 要求预测未来的问题

【如何开始】

您可以直接提问，例如：
- "2019年德国联邦议院讨论了哪些主要议题？"
- "在2015-2018年期间，不同党派在难民政策上的立场有何变化？"
- "请总结2021年绿党议员在气候保护方面的主要发言内容"

有任何问题，请随时提问！
"""
    
    # ========== 系统功能说明（德文版）==========
    
    SYSTEM_CAPABILITIES_DE = """Guten Tag! Ich bin ein intelligentes Frage-Antwort-System für Reden des Deutschen Bundestages.

【Was kann ich tun?】

1. **Fragen zum Deutschen Bundestag beantworten**
   - Zeitraum: 1949 bis 2025
   - Datenquelle: Offizielle Redenprotokolle des Deutschen Bundestages
   - Sprache: Fragen auf Chinesisch oder Deutsch, Antworten auf Deutsch

2. **Unterstützte Fragetypen**

   ✅ **Sachfragen**
   - Beispiel: "Welche Hauptthemen wurden 2019 im Bundestag diskutiert?"

   ✅ **Positionszusammenfassungen**
   - Beispiel: "Bitte fassen Sie die Hauptpositionen der Grünen zum Klimaschutz 2021 zusammen"

   ✅ **Politische Veränderungsanalysen**
   - Beispiel: "Wie haben sich die Positionen verschiedener Parteien zur Flüchtlingsfrage zwischen 2015 und 2018 verändert?"

   ✅ **Parteivergleiche**
   - Beispiel: "Vergleichen Sie die Ansichten von CDU/CSU und SPD zur Digitalisierungspolitik 2019"

   ✅ **Trendanalysen**
   - Beispiel: "Wie hat sich die Haltung zur Klimapolitik zwischen 2010 und 2020 entwickelt?"

【Wie beginnen】

Sie können direkt Fragen stellen, zum Beispiel:
- "Welche Hauptthemen wurden 2019 im Bundestag diskutiert?"
- "Wie haben sich die Positionen zur Flüchtlingspolitik zwischen 2015 und 2018 verändert?"

Bei Fragen stehe ich Ihnen jederzeit zur Verfügung!
"""
    
    # ========== 不相关问题回复 ==========
    
    IRRELEVANT_QUESTION_RESPONSE = """抱歉，您的问题似乎与德国联邦议院无关。

【您的问题】
{question}

【我的专长领域】
我是专门用于分析德国联邦议院演讲记录的系统，只能回答与以下主题相关的问题：
- 德国联邦议院的演讲和辩论
- 德国政党的立场和政策
- 德国议员的发言和观点
- 德国议会讨论的政治议题

【建议】
如果您对德国议会有任何问题，欢迎提问。例如：
- "2019年德国议会讨论了哪些主要议题？"
- "CDU/CSU在2020年对气候政策的立场是什么？"
- "2015-2018年难民政策的讨论有何变化？"

如需了解系统功能，可以问："你会做什么？"
"""
    
    # ========== 信息不足引导 ==========
    
    INSUFFICIENT_INFO_GUIDANCE = """您的问题我大致理解了，但缺少一些关键信息，无法准确回答。

【您的问题】
{question}

【缺少的信息】
{missing_info}

【建议补充】

为了更好地回答您的问题，建议补充以下信息：

{suggestions}

【修改示例】

❌ 原问题："{question}"

✅ 改进后：{improved_question_example}

【其他建议】
如果您不确定具体信息，可以：
- 提供大致的时间范围（如"2015-2020年"）
- 不指定具体党派，让系统搜索所有相关内容
- 使用更通用的主题词

请提供更多信息后重新提问，我会尽力帮助您！
"""
    
    # ========== 超出范围回复 ==========
    
    OUT_OF_RANGE_RESPONSE = """抱歉，您询问的内容超出了本系统的数据范围。

【您的问题】
{question}

【识别的时间】
{requested_time}

【系统数据范围】
本系统收录的是德国联邦议院演讲记录，时间范围：**1949年至2025年**

【问题】
{issue}

【建议】
{suggestion}

如有其他在数据范围内的问题，欢迎继续提问！
"""
    
    # ========== 未分类问题处理 ==========
    
    UNCLASSIFIED_QUESTION_HANDLING = """你是一个问题处理专家。以下问题无法归入预定义的5类（变化类/总结类/对比类/事实查询/趋势分析），但与德国议会相关。

【用户问题】
{question}

【已提取的参数】
{parameters}

【任务】
请设计一个合理的检索和回答策略。

【输出格式】

问题理解: [用一句话说明用户想知道什么]
处理策略: [描述如何处理这个问题]
检索建议: [建议使用什么条件检索（时间/党派/主题/关键词）]
回答建议: [建议如何组织答案]

【示例】
问题: "德国议会中有哪些女性议员发挥了重要作用？"
参数: {{"parties": null, "speakers": null, "topics": null}}

问题理解: 用户想了解德国议会中重要的女性议员
处理策略: 这是一个开放性问题，无法穷举所有女性议员，建议转换为可操作的查询
检索建议: 可以检索近年来（如2015-2025）频繁发言或担任重要职位的女性议员
回答建议: 列举几位有代表性的女性议员及其主要贡献，说明这只是部分示例

现在请分析用户的问题并提供处理建议。
"""
    
    # ========== 异常情况友好提示 ==========
    
    @staticmethod
    def format_validation_prompt(question: str) -> str:
        """格式化问题合法性检查Prompt"""
        return FallbackPrompts.QUESTION_VALIDATION.format(question=question)
    
    @staticmethod
    def format_irrelevant_response(question: str) -> str:
        """格式化不相关问题回复"""
        return FallbackPrompts.IRRELEVANT_QUESTION_RESPONSE.format(question=question)
    
    @staticmethod
    def format_insufficient_info_guidance(
        question: str,
        missing_info: str,
        suggestions: str,
        improved_example: str
    ) -> str:
        """格式化信息不足引导"""
        return FallbackPrompts.INSUFFICIENT_INFO_GUIDANCE.format(
            question=question,
            missing_info=missing_info,
            suggestions=suggestions,
            improved_question_example=improved_example
        )
    
    @staticmethod
    def format_out_of_range_response(
        question: str,
        requested_time: str,
        issue: str,
        suggestion: str
    ) -> str:
        """格式化超出范围回复"""
        return FallbackPrompts.OUT_OF_RANGE_RESPONSE.format(
            question=question,
            requested_time=requested_time,
            issue=issue,
            suggestion=suggestion
        )
    
    @staticmethod
    def format_unclassified_handling(question: str, parameters: dict) -> str:
        """格式化未分类问题处理"""
        return FallbackPrompts.UNCLASSIFIED_QUESTION_HANDLING.format(
            question=question,
            parameters=str(parameters)
        )


# ========== 具体的引导消息生成器 ==========

class GuidanceGenerator:
    """引导消息生成器"""
    
    @staticmethod
    def generate_missing_time_guidance(question: str) -> str:
        """生成缺少时间信息的引导"""
        return FallbackPrompts.format_insufficient_info_guidance(
            question=question,
            missing_info="时间信息（年份或时间范围）",
            suggestions="""
1. 如果您关心某个具体年份，请指定年份
   - 例如："2019年"、"2020年"

2. 如果您关心一个时间段，请指定范围
   - 例如："2015-2018年"、"2010年到2020年"

3. 如果您关心某个事件前后，请指明事件和大致时间
   - 例如："福岛核事故前后（2009-2013年）"
""",
            improved_example=f'"{question}" → 在[具体年份或时间范围]，{question[question.find("，")+1:] if "，" in question else question}'
        )
    
    @staticmethod
    def generate_missing_topic_guidance(question: str) -> str:
        """生成缺少主题信息的引导"""
        return FallbackPrompts.format_insufficient_info_guidance(
            question=question,
            missing_info="主题或议题信息",
            suggestions="""
1. 请明确您关心的政策领域或议题
   - 例如："难民政策"、"气候保护"、"数字化"

2. 可以使用德文或中文主题词
   - 德文：Flüchtlingspolitik, Klimaschutz, Digitalisierung
   - 中文：难民政策、气候保护、数字化

3. 如果不确定具体主题，可以使用更宽泛的描述
   - 例如："社会政策"、"外交政策"、"经济政策"
""",
            improved_example=f'{question}在[具体议题/政策领域]上的...'
        )
    
    @staticmethod
    def generate_out_of_range_future(question: str, year: str) -> str:
        """生成未来时间的回复"""
        return FallbackPrompts.format_out_of_range_response(
            question=question,
            requested_time=f"{year}年",
            issue=f"您询问的时间（{year}年）在未来，系统数据只到2025年。",
            suggestion=f"""
1. 如果您想了解最近的情况，可以询问：
   - "2025年德国议会关于[议题]的讨论？"
   - "2023-2025年[党派]对[议题]的立场？"

2. 如果您想了解趋势，可以询问：
   - "2020-2025年德国议会对[议题]的态度有何演变？"
"""
        )
    
    @staticmethod
    def generate_out_of_range_past(question: str, year: str) -> str:
        """生成过去时间的回复"""
        return FallbackPrompts.format_out_of_range_response(
            question=question,
            requested_time=f"{year}年",
            issue=f"您询问的时间（{year}年）在德意志联邦共和国成立（1949年）之前，系统没有相关数据。",
            suggestion=f"""
1. 德国联邦议院（Deutscher Bundestag）成立于1949年

2. 如果您想了解战后早期情况，可以询问：
   - "1949年德国联邦议院成立初期讨论了哪些议题？"
   - "1950年代德国议会的主要政党有哪些？"
"""
        )


# 测试代码
if __name__ == "__main__":
    fallback = FallbackPrompts()
    guidance = GuidanceGenerator()
    
    print("=== 测试1：问题合法性检查 ===")
    test_q1 = "你会做什么？"
    print(fallback.format_validation_prompt(test_q1))
    
    print("\n=== 测试2：系统功能说明 ===")
    print(fallback.SYSTEM_CAPABILITIES)
    
    print("\n=== 测试3：不相关问题 ===")
    test_q2 = "今天天气怎么样？"
    print(fallback.format_irrelevant_response(test_q2))
    
    print("\n=== 测试4：缺少时间信息 ===")
    test_q3 = "CDU/CSU对难民政策的立场是什么？"
    print(guidance.generate_missing_time_guidance(test_q3))
    
    print("\n=== 测试5：超出未来范围 ===")
    test_q4 = "2030年德国议会对气候政策的立场？"
    print(guidance.generate_out_of_range_future(test_q4, "2030"))

