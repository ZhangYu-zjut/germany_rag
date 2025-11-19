"""
问题拆解模板
为不同类型的复杂问题提供系统化的拆解策略
"""

from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class DecomposeTemplate:
    """拆解模板基类"""
    question_type: str  # 问题类型
    template_name: str  # 模板名称
    description: str  # 模板描述
    
    def generate_sub_questions(self, parameters: Dict[str, Any]) -> List[Dict]:
        """
        生成子问题列表（带元数据）

        Args:
            parameters: 提取的参数

        Returns:
            子问题列表，每个元素为字典:
            {
                "question": "子问题文本",
                "target_year": "2015",  # 可选，如果子问题明确针对某一年
                "target_party": "CDU/CSU",  # 可选
                "metadata": {...}  # 其他元数据
            }
        """
        raise NotImplementedError


class ChangeAnalysisTemplate(DecomposeTemplate):
    """
    变化类问题拆解模板
    
    典型问题: "在2015-2018年期间，不同党派在难民政策上的立场有何变化？"
    
    拆解策略:
    1. 按时间点拆解（起点、终点、可选中间点）
    2. 按党派拆解（如果指定多个党派）
    3. 生成对比子问题
    
    子问题结构:
    - 时间点A + 党派X + 主题 → "2015年CDU/CSU在难民政策上的立场"
    - 时间点B + 党派X + 主题 → "2018年CDU/CSU在难民政策上的立场"
    - ... (其他党派)
    - 对比问题 → "2015年与2018年在难民政策上的立场变化"
    """
    
    def __init__(self):
        super().__init__(
            question_type="变化类",
            template_name="时间序列变化分析",
            description="按时间点和对象拆解，分析立场变化"
        )

        # 🎯 Phase 4: 抽象主题映射表（扩展为具体维度）
        self.topic_expansion_map = {
            # 移民政策 → 具体措施维度
            "Migrationspolitik": [
                "Abschiebung und Rückführung",  # 遣返和回返
                "Integration und Aufnahme",      # 融合和接收
                "Grenzkontrollen und Sicherheit", # 边境控制和安全
                "Familiennachzug"                 # 家庭团聚
            ],
            "Flüchtlingspolitik": [
                "Abschiebung und Rückführung",
                "Integration",
                "Aufnahme von Flüchtlingen",
                "Familiennachzug"
            ],
            # 气候政策 → 具体措施维度
            "Klimapolitik": [
                "Emissionsreduktion",           # 减排
                "erneuerbare Energien",         # 可再生能源
                "Klimaschutzmaßnahmen",         # 气候保护措施
                "CO2-Bepreisung"                # 碳定价
            ],
            "Klimaschutz": [
                "Emissionsreduktion",
                "erneuerbare Energien",
                "Klimaschutzmaßnahmen"
            ]
        }

    def _is_abstract_topic(self, topic_str: str) -> bool:
        """
        判断主题是否为抽象概念（需要扩展为具体维度）

        Args:
            topic_str: 主题字符串

        Returns:
            True if abstract, False otherwise
        """
        # 检查是否包含已知抽象主题关键词
        abstract_keywords = self.topic_expansion_map.keys()
        for keyword in abstract_keywords:
            if keyword in topic_str:
                return True
        return False

    def _expand_topic_dimensions(self, topic_str: str) -> list:
        """
        将抽象主题扩展为具体维度

        Args:
            topic_str: 抽象主题（如"Migrationspolitik"）

        Returns:
            具体维度列表（如["Abschiebung und Rückführung", ...]）
        """
        # 查找匹配的扩展维度
        for abstract_topic, dimensions in self.topic_expansion_map.items():
            if abstract_topic in topic_str:
                return dimensions

        # 如果没有匹配的扩展规则，返回原主题
        return [topic_str]
    
    def generate_sub_questions(self, parameters: Dict[str, Any]) -> List[Dict]:
        """
        生成变化类子问题（带元数据）

        Args:
            parameters: {
                "time_range": {
                    "start_year": "2015",
                    "end_year": "2018",
                    "specific_years": ["2015", "2016", "2017", "2018"]  # ⚠️ 关键参数
                },
                "parties": ["CDU/CSU", "SPD"],
                "topics": ["难民政策", "家庭团聚"]
            }

        Returns:
            子问题列表（每个带target_year元数据）
        """
        sub_questions = []

        # 提取参数
        time_range = parameters.get("time_range", {})
        start_year = time_range.get("start_year")
        end_year = time_range.get("end_year")
        specific_years = time_range.get("specific_years", [])  # ⚠️ 新增：获取specific_years
        parties = parameters.get("parties", [])
        topics = parameters.get("topics", [])

        # 如果没有党派，使用"德国议会"作为整体
        if not parties:
            parties = ["Deutscher Bundestag"]

        # 主题描述
        topic_str = ", ".join(topics) if topics else "diesem Thema"

        # 策略1: 按党派 + 年份拆解
        # ⚠️ 关键修复：优先使用specific_years，避免自动填充中间年份
        # 🎯 Phase 4改进：针对抽象主题，自动扩展为具体子维度
        for party in parties:
            if specific_years:
                # ✅ 修复：如果有specific_years，直接使用（支持离散对比）
                for year in specific_years:
                    # 🎯 Phase 4: 检测是否为抽象主题，需要扩展为具体维度
                    if self._is_abstract_topic(topic_str):
                        # 生成具体维度查询
                        sub_dimensions = self._expand_topic_dimensions(topic_str)
                        for dimension in sub_dimensions:
                            sub_questions.append({
                                "question": f"Welche konkreten Maßnahmen und Positionen vertrat {party} im Jahr {year} zu {dimension}?",
                                "target_year": str(year),
                                "target_party": party,
                                "retrieval_strategy": "single_year",
                                "topic_dimension": dimension  # 标记具体维度
                            })
                    else:
                        # 保持原有逻辑（非抽象主题）
                        sub_questions.append({
                            "question": f"Was ist die Position von {party} zum Thema {topic_str} im Jahr {year}?",
                            "target_year": str(year),
                            "target_party": party,
                            "retrieval_strategy": "single_year"
                        })
            elif start_year and end_year:
                # 回退方案：如果没有specific_years，按传统方式生成连续范围
                start = int(start_year)
                end = int(end_year)
                span = end - start

                # 根据时间跨度决定拆解粒度
                if span <= 5:
                    # 短期（≤5年）：按每年拆解
                    for year in range(start, end + 1):
                        sub_questions.append({
                            "question": f"Was ist die Position von {party} zum Thema {topic_str} im Jahr {year}?",
                            "target_year": str(year),
                            "target_party": party,
                            "retrieval_strategy": "single_year"
                        })
                elif span <= 10:
                    # 中期（6-10年）：按2年拆解
                    for year in range(start, end + 1, 2):
                        if year <= end:
                            sub_questions.append({
                                "question": f"Was ist die Position von {party} zum Thema {topic_str} im Jahr {year}?",
                                "target_year": str(year),
                                "target_party": party,
                                "retrieval_strategy": "single_year"
                            })
                    # 确保包含终点年份
                    if end not in range(start, end + 1, 2):
                        sub_questions.append({
                            "question": f"Was ist die Position von {party} zum Thema {topic_str} im Jahr {end}?",
                            "target_year": str(end),
                            "target_party": party,
                            "retrieval_strategy": "single_year"
                        })
                else:
                    # 长期（>10年）：按3-4年采样
                    sample_years = [start]
                    step = max(3, span // 5)  # 分成大约5段
                    current = start + step
                    while current < end:
                        sample_years.append(current)
                        current += step
                    sample_years.append(end)  # 确保包含终点

                    for year in sample_years:
                        sub_questions.append({
                            "question": f"Was ist die Position von {party} zum Thema {topic_str} im Jahr {year}?",
                            "target_year": str(year),
                            "target_party": party,
                            "retrieval_strategy": "single_year"
                        })
            elif start_year:
                # 只有起始年份
                sub_questions.append({
                    "question": f"Was ist die Position von {party} zum Thema {topic_str} im Jahr {start_year}?",
                    "target_year": str(start_year),
                    "target_party": party,
                    "retrieval_strategy": "single_year"
                })
            elif end_year:
                # 只有结束年份
                sub_questions.append({
                    "question": f"Was ist die Position von {party} zum Thema {topic_str} im Jahr {end_year}?",
                    "target_year": str(end_year),
                    "target_party": party,
                    "retrieval_strategy": "single_year"
                })
        
        # 策略2: 添加变化对比问题
        # ⚠️ 修复：只为连续范围添加对比问题，离散对比（如"2019年与2017年相比"）不添加
        if start_year and end_year and specific_years:
            # 检测是否为连续范围
            years_int = sorted([int(y) for y in specific_years])
            is_continuous = (len(years_int) == (max(years_int) - min(years_int) + 1))

            # 只为连续范围添加总结性变化对比问题
            if is_continuous:
                if len(parties) == 1:
                    sub_questions.append({
                        "question": f"Wie hat sich die Position von {parties[0]} zum Thema {topic_str} von {start_year} bis {end_year} verändert?",
                        "target_year": None,  # 对比问题不限定单一年份
                        "target_party": parties[0],
                        "retrieval_strategy": "multi_year",  # 需要多年检索
                        "year_range": [start_year, end_year]
                    })
                else:
                    sub_questions.append({
                        "question": f"Welche Gemeinsamkeiten und Unterschiede gibt es in den Positionsänderungen verschiedener Parteien zum Thema {topic_str} von {start_year} bis {end_year}?",
                        "target_year": None,
                        "target_party": None,
                        "retrieval_strategy": "multi_year",
                        "year_range": [start_year, end_year]
                    })

        return sub_questions


class SummaryTemplate(DecomposeTemplate):
    """
    总结类问题拆解模板
    
    典型问题: "请总结2021年绿党在气候保护方面的主要观点"
    
    拆解策略:
    1. 按时间段拆解（如果时间跨度大）
    2. 按子主题拆解（如果主题复杂）
    3. 按议员拆解（如果指定多个议员）
    
    子问题结构:
    - 党派/议员 + 时间 + 主题 → "2021年绿党在气候保护方面的发言"
    - （可选）细分主题 → "2021年绿党在碳排放政策上的观点"
    """
    
    def __init__(self):
        super().__init__(
            question_type="总结类",
            template_name="主题总结",
            description="按对象和主题拆解，总结主要观点"
        )
    
    def generate_sub_questions(self, parameters: Dict[str, Any]) -> List[str]:
        """
        生成总结类子问题
        
        Args:
            parameters: {
                "time_range": {"start_year": "2021"},
                "parties": ["绿党"],
                "speakers": ["Baerbock"],
                "topics": ["气候保护", "碳排放"]
            }
            
        Returns:
            子问题列表
        """
        sub_questions = []
        
        # 提取参数
        time_range = parameters.get("time_range", {})
        start_year = time_range.get("start_year")
        end_year = time_range.get("end_year")
        parties = parameters.get("parties", [])
        speakers = parameters.get("speakers", [])
        topics = parameters.get("topics", [])
        
        # 时间描述
        if start_year and end_year and start_year != end_year:
            time_str = f"im Zeitraum von {start_year} bis {end_year} "
        elif start_year:
            time_str = f"im Jahr {start_year} "
        else:
            time_str = "im relevanten Zeitraum "

        # 主题描述
        topic_str = ", ".join(topics) if topics else "relevanten Themen"
        
        # 策略1: 按议员拆解（优先级最高）
        if speakers:
            for speaker in speakers:
                sub_questions.append(
                    f"Was sind die Hauptansichten und Aussagen von {speaker} {time_str}zu {topic_str}?"
                )

        # 策略2: 按党派拆解
        elif parties:
            for party in parties:
                sub_questions.append(
                    f"Was sind die Hauptansichten und Positionen von {party} {time_str}zu {topic_str}?"
                )
        
        # 策略3: 按主题拆解（如果有多个主题）
        else:
            if len(topics) > 1:
                for topic in topics:
                    sub_questions.append(
                        f"Was sind die Hauptdiskussionsinhalte des Deutschen Bundestags {time_str}zu {topic}?"
                    )
            else:
                sub_questions.append(
                    f"Was sind die Hauptdiskussionsinhalte des Deutschen Bundestags {time_str}zu {topic_str}?"
                )
        
        # 策略4: 如果时间跨度>2年，按年份拆解
        if start_year and end_year:
            start = int(start_year)
            end = int(end_year)
            if end - start > 2:
                # 清空之前的问题，按年份重新拆解
                sub_questions = []
                for year in range(start, end + 1):
                    if parties:
                        party_str = ", ".join(parties)
                        sub_questions.append(
                            f"Was sind die Hauptansichten von {party_str} im Jahr {year} zu {topic_str}?"
                        )
                    else:
                        sub_questions.append(
                            f"Was sind die Hauptdiskussionen des Deutschen Bundestags im Jahr {year} zu {topic_str}?"
                        )
        
        return sub_questions


class ComparisonTemplate(DecomposeTemplate):
    """
    对比类问题拆解模板
    
    典型问题: "对比CDU/CSU和SPD在2019年数字化政策上的立场差异"
    
    拆解策略:
    1. 为每个对比对象生成独立问题
    2. 生成对比分析问题
    
    子问题结构:
    - 对象A + 主题 → "CDU/CSU在数字化政策上的立场"
    - 对象B + 主题 → "SPD在数字化政策上的立场"
    - 对比问题 → "CDU/CSU与SPD在数字化政策上的主要差异"
    """
    
    def __init__(self):
        super().__init__(
            question_type="对比类",
            template_name="对象对比分析",
            description="按对比对象拆解，分析差异和相似"
        )
    
    def generate_sub_questions(self, parameters: Dict[str, Any]) -> List[str]:
        """
        生成对比类子问题

        Args:
            parameters: {
                "time_range": {"start_year": "2019"},
                "parties": ["CDU/CSU", "SPD"],
                "topics": ["数字化政策"]
            }

        Returns:
            子问题列表
        """
        sub_questions = []

        # 提取参数
        time_range = parameters.get("time_range", {})
        start_year = time_range.get("start_year")
        end_year = time_range.get("end_year")
        specific_years = time_range.get("specific_years", [])
        parties = parameters.get("parties", [])
        speakers = parameters.get("speakers", [])
        topics = parameters.get("topics", [])

        # 时间描述（修复：处理时间范围情况）
        if start_year and end_year and start_year != end_year:
            # 有时间范围：检查是否需要按年拆解
            if specific_years and len(specific_years) <= 5:
                # 时间跨度≤5年，按每年拆解
                years_to_process = specific_years
            else:
                # 时间跨度>5年，使用范围描述
                time_str = f"von {start_year} bis {end_year} "
                years_to_process = [time_str]
        elif start_year:
            # 单一年份
            time_str = f"im Jahr {start_year} "
            years_to_process = [time_str]
        else:
            time_str = ""
            years_to_process = [""]

        # 主题描述
        topic_str = ", ".join(topics) if topics else "diesem Thema"

        # 对比对象（党派优先，议员次之）
        compare_objects = parties if parties else speakers

        if len(compare_objects) < 2:
            # 如果对比对象少于2个，无法对比，退化为总结
            if compare_objects:
                for year_str in years_to_process:
                    sub_questions.append(
                        f"Was ist die Position von {compare_objects[0]} {year_str}zu {topic_str}?"
                    )
        else:
            # 策略1: 为每个对象 × 每年生成独立问题
            for year_str in years_to_process:
                for obj in compare_objects:
                    sub_questions.append(
                        f"Was sind die Position und Hauptansichten von {obj} {year_str}zu {topic_str}?"
                    )

            # 策略2: 生成对比问题
            for year_str in years_to_process:
                if len(compare_objects) == 2:
                    sub_questions.append(
                        f"Was sind die Hauptunterschiede zwischen {compare_objects[0]} und {compare_objects[1]} {year_str}zu {topic_str}?"
                    )
                else:
                    obj_str = ", ".join(compare_objects)
                    sub_questions.append(
                        f"Was sind die Gemeinsamkeiten und Unterschiede in den Positionen von {obj_str} {year_str}zu {topic_str}?"
                    )

        return sub_questions


class TrendAnalysisTemplate(DecomposeTemplate):
    """
    趋势分析类问题拆解模板
    
    典型问题: "2010-2020年德国议会对气候政策的态度演变趋势"
    
    拆解策略:
    1. 按时间段拆解（通常分为3-5个时间段）
    2. 为每个时间段生成特征描述问题
    3. 生成趋势总结问题
    
    子问题结构:
    - 时间段1 + 主题 → "2010-2012年德国议会对气候政策的态度"
    - 时间段2 + 主题 → "2013-2015年德国议会对气候政策的态度"
    - ...
    - 趋势问题 → "2010-2020年气候政策态度的整体演变趋势"
    """
    
    def __init__(self):
        super().__init__(
            question_type="趋势分析",
            template_name="时间序列趋势",
            description="按时间段拆解，分析演变趋势"
        )
    
    def generate_sub_questions(self, parameters: Dict[str, Any]) -> List[str]:
        """
        生成趋势分析类子问题
        
        Args:
            parameters: {
                "time_range": {"start_year": "2010", "end_year": "2020"},
                "topics": ["气候政策"]
            }
            
        Returns:
            子问题列表
        """
        sub_questions = []
        
        # 提取参数
        time_range = parameters.get("time_range", {})
        start_year = time_range.get("start_year")
        end_year = time_range.get("end_year")
        parties = parameters.get("parties", [])
        topics = parameters.get("topics", [])
        
        # 主题描述
        topic_str = ", ".join(topics) if topics else "relevanten Themen"

        # 对象描述
        if parties:
            obj_str = ", ".join(parties)
        else:
            obj_str = "Deutscher Bundestag"
        
        if not start_year or not end_year:
            # 如果没有明确时间范围，无法做趋势分析
            sub_questions.append(
                f"Was sind die Haltung und Position von {obj_str} zu {topic_str}?"
            )
            return sub_questions
        
        start = int(start_year)
        end = int(end_year)
        span = end - start
        
        # 根据时间跨度决定分段策略
        if span <= 2:
            # 短期：按年拆解
            for year in range(start, end + 1):
                sub_questions.append(
                    f"Was ist die Hauptposition von {obj_str} im Jahr {year} zu {topic_str}?"
                )
        elif span <= 5:
            # 中期：按2年拆解
            current = start
            while current <= end:
                period_end = min(current + 1, end)
                if current == period_end:
                    sub_questions.append(
                        f"Was ist die Hauptposition von {obj_str} im Jahr {current} zu {topic_str}?"
                    )
                else:
                    sub_questions.append(
                        f"Was ist die Hauptposition von {obj_str} im Zeitraum von {current} bis {period_end} zu {topic_str}?"
                    )
                current += 2
        else:
            # 长期：按3-4年拆解
            segment_size = (span + 3) // 4  # 分成4段
            current = start
            while current <= end:
                period_end = min(current + segment_size - 1, end)
                sub_questions.append(
                    f"Was ist die Hauptposition von {obj_str} im Zeitraum von {current} bis {period_end} zu {topic_str}?"
                )
                current += segment_size

        # 添加趋势总结问题
        sub_questions.append(
            f"Welchen Entwicklungstrend zeigt die Haltung von {obj_str} zu {topic_str} von {start_year} bis {end_year}?"
        )
        
        return sub_questions


class TemplateSelector:
    """模板选择器"""
    
    def __init__(self):
        self.templates = {
            "变化类": ChangeAnalysisTemplate(),
            "总结类": SummaryTemplate(),
            "对比类": ComparisonTemplate(),
            "趋势分析": TrendAnalysisTemplate(),
        }
    
    def select_template(self, question_type: str) -> DecomposeTemplate:
        """
        根据问题类型选择模板
        
        Args:
            question_type: 问题类型
            
        Returns:
            对应的模板对象
        """
        template = self.templates.get(question_type)
        
        if template is None:
            # 如果没有匹配的模板，默认使用总结类
            template = self.templates["总结类"]
        
        return template
    
    def decompose(self, question_type: str, parameters: Dict[str, Any]) -> List[str]:
        """
        拆解问题
        
        Args:
            question_type: 问题类型
            parameters: 提取的参数
            
        Returns:
            子问题列表
        """
        template = self.select_template(question_type)
        sub_questions = template.generate_sub_questions(parameters)
        
        return sub_questions


if __name__ == "__main__":
    # 测试模板
    selector = TemplateSelector()
    
    print("="*60)
    print("问题拆解模板测试")
    print("="*60)
    
    # 测试1: 变化类
    print("\n【测试1: 变化类】")
    params1 = {
        "time_range": {"start_year": "2015", "end_year": "2018"},
        "parties": ["CDU/CSU", "SPD"],
        "topics": ["难民政策"]
    }
    sub_q1 = selector.decompose("变化类", params1)
    print(f"参数: {params1}")
    print(f"子问题 ({len(sub_q1)}个):")
    for i, q in enumerate(sub_q1, 1):
        print(f"  {i}. {q}")
    
    # 测试2: 总结类
    print("\n【测试2: 总结类】")
    params2 = {
        "time_range": {"start_year": "2021"},
        "parties": ["绿党"],
        "topics": ["气候保护"]
    }
    sub_q2 = selector.decompose("总结类", params2)
    print(f"参数: {params2}")
    print(f"子问题 ({len(sub_q2)}个):")
    for i, q in enumerate(sub_q2, 1):
        print(f"  {i}. {q}")
    
    # 测试3: 对比类
    print("\n【测试3: 对比类】")
    params3 = {
        "time_range": {"start_year": "2019"},
        "parties": ["CDU/CSU", "SPD", "FDP"],
        "topics": ["数字化政策"]
    }
    sub_q3 = selector.decompose("对比类", params3)
    print(f"参数: {params3}")
    print(f"子问题 ({len(sub_q3)}个):")
    for i, q in enumerate(sub_q3, 1):
        print(f"  {i}. {q}")
    
    # 测试4: 趋势分析
    print("\n【测试4: 趋势分析】")
    params4 = {
        "time_range": {"start_year": "2010", "end_year": "2020"},
        "topics": ["气候政策"]
    }
    sub_q4 = selector.decompose("趋势分析", params4)
    print(f"参数: {params4}")
    print(f"子问题 ({len(sub_q4)}个):")
    for i, q in enumerate(sub_q4, 1):
        print(f"  {i}. {q}")
    
    print("\n" + "="*60)
    print("测试完成！")

