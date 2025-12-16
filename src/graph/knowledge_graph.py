"""
知识图谱模块 - 解决Q7类召回失败问题

核心功能:
1. 加载和管理知识图谱数据
2. 判断是否需要触发知识图谱扩展（条件触发）
3. 根据问题参数智能筛选相关标签
4. 生成扩展查询

设计原则:
- 2.5层结构: topics -> dimensions -> tags
- 条件触发: 不是每次都扩展，基于问题复杂度判断
- 智能筛选: 基于触发条件和权重选择最相关的标签
- 数量控制: 最多扩展15个标签，避免查询爆炸
"""

import json
import os
from typing import Dict, List, Optional, Tuple
from ..utils.logger import logger


class KnowledgeGraphManager:
    """
    知识图谱管理器

    负责:
    1. 加载知识图谱数据
    2. 判断是否触发扩展
    3. 筛选相关标签
    4. 生成扩展查询
    """

    # 默认配置
    DEFAULT_CONFIG = {
        "max_tags": 15,           # 最多扩展15个标签
        "min_trigger_score": 1,   # 最低触发分数
        "expansion_threshold": 2, # 扩展到标签层的评分阈值（从3降到2，让简单问题也能触发tag级别）
    }

    def __init__(self, kg_path: str = None):
        """
        初始化知识图谱管理器

        Args:
            kg_path: 知识图谱JSON文件路径
        """
        if kg_path is None:
            # 默认路径
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            kg_path = os.path.join(base_dir, "data", "knowledge_graph.json")

        self.kg_path = kg_path
        self.kg_data = self._load_knowledge_graph()
        self.config = self.DEFAULT_CONFIG.copy()

        logger.info(f"[KnowledgeGraph] 加载知识图谱: {len(self.kg_data.get('topics', {}))} 个主题, "
                   f"{len(self.kg_data.get('dimensions', {}))} 个维度, "
                   f"{len(self.kg_data.get('tags', {}))} 个标签")

    def _load_knowledge_graph(self) -> Dict:
        """加载知识图谱数据"""
        try:
            with open(self.kg_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except Exception as e:
            logger.error(f"[KnowledgeGraph] 加载知识图谱失败: {e}")
            return {"topics": {}, "dimensions": {}, "tags": {}}

    def should_use_knowledge_graph(
        self,
        question: str,
        intent: str,
        question_type: str,
        parameters: Dict
    ) -> Dict:
        """
        判断是否需要触发知识图谱扩展

        Args:
            question: 用户问题
            intent: 问题意图 (simple/complex)
            question_type: 问题类型 (变化类/对比类/总结类等)
            parameters: 问题参数 (时间范围、党派等)

        Returns:
            {
                "use_kg": True/False,
                "expansion_level": "none" | "dimension" | "tag",
                "score": int,
                "reasons": List[str]
            }
        """
        # 【架构解耦】不再基于intent判断，而是基于问题内容评分
        # 简单问题也可能需要KG扩展（如Q7：AfD 2018难民政策）
        score = 0
        reasons = []

        # 【Day 4新增】条件0：基础分（简单问题从0开始，复杂问题从1开始）
        if intent == "complex":
            score += 1
            reasons.append("复杂问题基础分+1")

        # 条件1：问题类型（权重2）
        if question_type in ["变化类", "对比类"]:
            score += 2
            reasons.append(f"问题类型为{question_type}，需要细节支撑")

        # 条件2：时间跨度（权重2）
        time_range = parameters.get("time_range", {})
        if time_range:
            start = int(time_range.get("start_year", 0) or 0)
            end = int(time_range.get("end_year", 0) or 0)
            span = end - start
            if span >= 2:
                score += 2
                reasons.append(f"时间跨度{span}年，需要更多细节")
            elif span >= 1:
                score += 1
                reasons.append(f"时间跨度{span}年")

        # 条件3：多党派（权重1）
        parties = parameters.get("parties", [])
        if len(parties) >= 2:
            score += 1
            reasons.append(f"涉及{len(parties)}个党派对比")

        # 条件4：问题包含细节关键词（权重2）
        detail_keywords = ["konkret", "Beispiel", "Projekt", "Initiative",
                          "具体", "例子", "项目", "案例"]
        if any(kw in question for kw in detail_keywords):
            score += 2
            reasons.append("问题要求具体例子/项目")

        # 条件5：问题已包含知识图谱中的标签关键词（权重3，直接触发）
        for tag_name, tag_data in self.kg_data.get("tags", {}).items():
            tag_keywords = tag_data.get("keywords", [])
            if any(kw in question for kw in tag_keywords):
                score += 3
                reasons.append(f"问题直接提到标签相关词: {tag_name}")
                break  # 只加一次

        # 【Day 4新增】条件6：主题匹配知识图谱主题（权重2）
        # 如果问题的topics包含知识图谱主题关键词，应触发相关标签
        question_topics = parameters.get("topics", [])
        for topic_name, topic_data in self.kg_data.get("topics", {}).items():
            topic_keywords = topic_data.get("keywords", [])
            # 检查问题主题是否匹配知识图谱主题
            for q_topic in question_topics:
                if q_topic in topic_keywords or q_topic == topic_name:
                    score += 2
                    reasons.append(f"主题匹配知识图谱: {topic_name}")
                    break
            else:
                continue
            break  # 只加一次

        # 【Day 4新增】条件7：总结类问题涉及敏感主题（权重1）
        # 难民、移民、庇护等敏感主题的总结类问题也应触发知识图谱
        if question_type == "总结类":
            sensitive_topics = ["Flüchtling", "Migration", "Asyl", "Integration",
                              "难民", "移民", "融合", "庇护"]
            question_lower = question.lower()
            for topic in sensitive_topics:
                if topic.lower() in question_lower:
                    score += 1
                    reasons.append(f"总结类问题涉及敏感主题: {topic}")
                    break
            # 也检查参数中的主题
            for q_topic in question_topics:
                for sensitive in sensitive_topics:
                    if sensitive.lower() in q_topic.lower():
                        score += 1
                        reasons.append(f"参数主题包含敏感词: {q_topic}")
                        break
                else:
                    continue
                break

        # 决策
        if score >= self.config["expansion_threshold"]:
            return {
                "use_kg": True,
                "expansion_level": "tag",
                "score": score,
                "reasons": reasons
            }
        elif score > 0:
            return {
                "use_kg": True,
                "expansion_level": "dimension",
                "score": score,
                "reasons": reasons
            }
        else:
            return {
                "use_kg": False,
                "expansion_level": "none",
                "score": score,
                "reasons": ["评分不足，不触发知识图谱"]
            }

    def get_relevant_topics(self, question: str, parameters: Dict) -> List[str]:
        """
        识别问题相关的主题

        Args:
            question: 用户问题
            parameters: 问题参数

        Returns:
            相关主题列表
        """
        matched_topics = []
        topics = parameters.get("topics", [])

        # 优先使用已提取的topics
        for topic in topics:
            for topic_name, topic_data in self.kg_data.get("topics", {}).items():
                if topic in topic_data.get("keywords", []) or topic == topic_name:
                    if topic_name not in matched_topics:
                        matched_topics.append(topic_name)

        # 如果没有匹配，用关键词匹配
        if not matched_topics:
            question_lower = question.lower()
            for topic_name, topic_data in self.kg_data.get("topics", {}).items():
                keywords = topic_data.get("keywords", [])
                if any(kw.lower() in question_lower for kw in keywords):
                    matched_topics.append(topic_name)

        logger.info(f"[KnowledgeGraph] 识别到主题: {matched_topics}")
        return matched_topics

    def get_dimensions_for_topics(self, topics: List[str]) -> List[str]:
        """
        获取主题下的所有维度

        Args:
            topics: 主题列表

        Returns:
            维度列表
        """
        dimensions = set()
        for topic in topics:
            topic_data = self.kg_data.get("topics", {}).get(topic, {})
            dimensions.update(topic_data.get("dimensions", []))

        return list(dimensions)

    def select_relevant_tags(
        self,
        question: str,
        parameters: Dict,
        dimensions: List[str]
    ) -> List[Dict]:
        """
        智能筛选相关标签（三层筛选机制）

        Args:
            question: 用户问题
            parameters: 问题参数
            dimensions: 相关维度列表

        Returns:
            筛选后的标签列表，包含分数信息
        """
        # Step 1: 获取维度下的所有候选标签
        candidate_tags = {}
        for dim_name in dimensions:
            dim_data = self.kg_data.get("dimensions", {}).get(dim_name, {})
            for tag_name in dim_data.get("tags", []):
                if tag_name not in candidate_tags:
                    tag_data = self.kg_data.get("tags", {}).get(tag_name, {})
                    if tag_data:
                        candidate_tags[tag_name] = tag_data

        logger.info(f"[KnowledgeGraph] 候选标签数: {len(candidate_tags)}")

        # Step 2: 触发条件筛选
        question_years = []
        time_range = parameters.get("time_range", {})
        if time_range:
            specific_years = time_range.get("specific_years", [])
            question_years = [int(y) for y in specific_years if y]

        question_parties = parameters.get("parties", [])
        question_lower = question.lower()

        triggered_tags = []
        for tag_name, tag_data in candidate_tags.items():
            conditions = tag_data.get("trigger_conditions", {})
            trigger_score = 0

            # 条件1：年份匹配
            condition_years = conditions.get("years", [])
            if question_years and condition_years:
                year_overlap = set(question_years) & set(condition_years)
                if year_overlap:
                    trigger_score += len(year_overlap)

            # 条件2：党派匹配
            condition_parties = conditions.get("parties", [])
            if question_parties and condition_parties:
                party_overlap = set(question_parties) & set(condition_parties)
                if party_overlap:
                    trigger_score += len(party_overlap) * 2

            # 条件3：关键词匹配
            condition_keywords = conditions.get("keywords", [])
            for kw in condition_keywords:
                if kw.lower() in question_lower:
                    trigger_score += 3

            # 条件4：标签关键词直接出现在问题中
            tag_keywords = tag_data.get("keywords", [])
            for kw in tag_keywords:
                if kw.lower() in question_lower:
                    trigger_score += 5  # 直接提到的权重最高

            if trigger_score >= self.config["min_trigger_score"]:
                triggered_tags.append({
                    "name": tag_name,
                    "trigger_score": trigger_score,
                    "weight": tag_data.get("weight", 1.0),
                    "final_score": trigger_score * tag_data.get("weight", 1.0),
                    "data": tag_data
                })

        logger.info(f"[KnowledgeGraph] 触发的标签数: {len(triggered_tags)}")

        # Step 3: 按分数排序，限制数量
        sorted_tags = sorted(triggered_tags, key=lambda x: x["final_score"], reverse=True)
        final_tags = sorted_tags[:self.config["max_tags"]]

        logger.info(f"[KnowledgeGraph] 最终选择标签数: {len(final_tags)}")
        if final_tags:
            logger.debug(f"[KnowledgeGraph] 选中标签: {[t['name'] for t in final_tags]}")

        return final_tags

    def generate_expansion_queries(
        self,
        selected_tags: List[Dict],
        parameters: Dict
    ) -> List[str]:
        """
        根据选中的标签生成扩展查询

        Args:
            selected_tags: 选中的标签列表
            parameters: 问题参数（用于填充模板）

        Returns:
            扩展查询列表
        """
        expansion_queries = []

        # 获取参数
        parties = parameters.get("parties", [""])
        time_range = parameters.get("time_range", {})
        years = time_range.get("specific_years", [""])

        for tag in selected_tags:
            tag_data = tag.get("data", {})
            templates = tag_data.get("expansion_queries", [])

            for template in templates:
                # 为每个党派和年份生成查询
                for party in parties[:2]:  # 最多2个党派
                    for year in years[:2]:  # 最多2个年份
                        query = template.format(
                            party=party or "",
                            year=year or ""
                        ).strip()
                        if query and query not in expansion_queries:
                            expansion_queries.append(query)

        logger.info(f"[KnowledgeGraph] 生成扩展查询: {len(expansion_queries)}个")
        return expansion_queries[:30]  # 最多30个扩展查询

    def expand_query(
        self,
        question: str,
        intent: str,
        question_type: str,
        parameters: Dict,
        force_expansion: bool = False  # 深度分析模式强制扩展
    ) -> Tuple[bool, List[str], Dict]:
        """
        完整的查询扩展流程

        Args:
            question: 用户问题
            intent: 问题意图
            question_type: 问题类型
            parameters: 问题参数
            force_expansion: 是否强制扩展（深度分析模式）

        Returns:
            (是否扩展, 扩展查询列表, 详细信息)
        """
        # 【深度分析模式】强制启用扩展
        if force_expansion:
            logger.info("[KnowledgeGraph] 🔍 深度分析模式: 强制启用知识图谱扩展")
            kg_decision = {
                "use_kg": True,
                "expansion_level": "tag",  # 强制tag级别
                "score": 99,  # 最高分
                "reasons": ["深度分析模式强制启用"]
            }
        else:
            # Step 1: 判断是否需要知识图谱扩展
            kg_decision = self.should_use_knowledge_graph(
                question, intent, question_type, parameters
            )

            if not kg_decision["use_kg"]:
                return False, [], kg_decision

        # Step 2: 识别相关主题
        topics = self.get_relevant_topics(question, parameters)
        if not topics:
            logger.warning("[KnowledgeGraph] 未识别到相关主题")
            return False, [], {"error": "未识别到相关主题"}

        # Step 3: 获取相关维度
        dimensions = self.get_dimensions_for_topics(topics)

        # Step 4: 根据扩展级别决定是否继续
        if kg_decision["expansion_level"] == "dimension":
            # 只扩展到维度层，不扩展到标签
            logger.info(f"[KnowledgeGraph] 只扩展到维度层: {dimensions}")
            return True, dimensions, kg_decision

        # Step 5: 筛选相关标签
        selected_tags = self.select_relevant_tags(question, parameters, dimensions)

        # Step 6: 生成扩展查询
        expansion_queries = self.generate_expansion_queries(selected_tags, parameters)

        # 返回结果
        result_info = {
            **kg_decision,
            "topics": topics,
            "matched_topics": topics,  # 别名，用于UI显示
            "dimensions": dimensions,
            "selected_tags": [t["name"] for t in selected_tags],
            "expansion_query_count": len(expansion_queries),
            "expansion_queries": expansion_queries[:5]  # 返回前5个扩展查询用于显示
        }

        return True, expansion_queries, result_info

    def update_tag_weight(self, tag_name: str, delta: float = 0.5):
        """
        更新标签权重（用于用户反馈）

        Args:
            tag_name: 标签名
            delta: 权重增量（正数增加，负数减少）
        """
        if tag_name in self.kg_data.get("tags", {}):
            current_weight = self.kg_data["tags"][tag_name].get("weight", 1.0)
            new_weight = max(0.5, min(3.0, current_weight + delta))  # 限制在0.5-3.0
            self.kg_data["tags"][tag_name]["weight"] = new_weight
            logger.info(f"[KnowledgeGraph] 更新标签权重: {tag_name} {current_weight} -> {new_weight}")

    def save_knowledge_graph(self):
        """保存知识图谱（用于持久化权重更新）"""
        try:
            with open(self.kg_path, 'w', encoding='utf-8') as f:
                json.dump(self.kg_data, f, ensure_ascii=False, indent=2)
            logger.info(f"[KnowledgeGraph] 知识图谱已保存")
        except Exception as e:
            logger.error(f"[KnowledgeGraph] 保存知识图谱失败: {e}")


# 全局单例
_kg_manager = None

def get_knowledge_graph_manager() -> KnowledgeGraphManager:
    """获取知识图谱管理器单例"""
    global _kg_manager
    if _kg_manager is None:
        _kg_manager = KnowledgeGraphManager()
    return _kg_manager
