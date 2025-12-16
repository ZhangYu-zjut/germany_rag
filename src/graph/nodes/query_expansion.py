"""
QueryExpansion Node - LLM驱动的多角度查询生成（支持并发 + 实体提取）
"""
import json
import asyncio
import re
from typing import Dict, Any, List
from loguru import logger

from src.graph.state import GraphState
from src.llm.client import GeminiLLMClient
from src.llm.prompts_query_expansion import build_query_expansion_prompt, QUERY_EXPANSION_FALLBACK_PROMPT


class QueryExpansionNode:
    """Query扩展节点 - 使用LLM生成多个不同角度的检索查询"""

    def __init__(self, llm_client: GeminiLLMClient = None, expansion_count: int = 5, enable_concurrent: bool = True):
        """
        初始化Query扩展节点

        Args:
            llm_client: LLM客户端（可选，如果为None则自动创建）
            expansion_count: 扩展查询数量（默认5个）
            enable_concurrent: 是否启用并发查询扩展（默认True，可提升4-5倍速度）
        """
        self.llm_client = llm_client or GeminiLLMClient()
        self.expansion_count = expansion_count
        self.enable_concurrent = enable_concurrent
        logger.info(f"[QueryExpansionNode] 初始化完成: expansion_count={expansion_count}, concurrent={enable_concurrent}")

    def __call__(self, state: GraphState) -> Dict[str, Any]:
        """
        执行Query扩展

        Args:
            state: 当前图状态

        Returns:
            更新后的状态字典
        """
        logger.info("[QueryExpansionNode] 开始Query扩展...")

        # 使用question字段作为原始问题
        original_question = state.get("question", "")
        sub_questions = state.get("sub_questions", [])

        if not sub_questions:
            logger.warning("[QueryExpansionNode] 没有子问题，跳过Query扩展")
            return {"expanded_queries_map": {}}

        # 提取参数（用于Prompt） - 使用parameters字段
        params = state.get("parameters", {})
        year = params.get("year", [""])[0] if params.get("year") else ""
        group = params.get("group", [""])[0] if params.get("group") else ""
        topic = params.get("topic", [""])[0] if params.get("topic") else ""

        # === 并发优化：根据配置选择串行或并发 ===
        if self.enable_concurrent:
            logger.info(f"[QueryExpansionNode] 🚀 使用并发模式扩展 {len(sub_questions)} 个子问题")
            expanded_queries_map = asyncio.run(
                self._expand_all_concurrent(sub_questions, original_question, year, group, topic)
            )
        else:
            logger.info(f"[QueryExpansionNode] 使用串行模式扩展 {len(sub_questions)} 个子问题")
            expanded_queries_map = self._expand_all_sequential(sub_questions, original_question, year, group, topic)

        return {
            "expanded_queries_map": expanded_queries_map
        }

    def _expand_all_sequential(self, sub_questions: List, original_question: str,
                               year: str, group: str, topic: str) -> Dict[str, List[str]]:
        """
        串行模式：逐个扩展子问题（原有逻辑）

        Args:
            sub_questions: 子问题列表
            original_question: 原始问题
            year: 年份
            group: 党派
            topic: 主题

        Returns:
            扩展查询映射字典
        """
        expanded_queries_map = {}

        for idx, sub_q in enumerate(sub_questions, start=1):
            # === 支持多种子问题格式（字符串或字典） ===
            if isinstance(sub_q, dict):
                sub_q_text = sub_q.get("question", str(sub_q))
            else:
                sub_q_text = str(sub_q)

            logger.info(f"[QueryExpansionNode] 为子问题{idx}生成扩展查询: {sub_q_text[:100]}...")

            try:
                # 构建Prompt
                prompt = build_query_expansion_prompt(
                    original_question=original_question,
                    sub_question=sub_q_text,
                    year=year,
                    group=group,
                    topic=topic
                )

                # 调用LLM（invoke方法不支持temperature和max_tokens参数）
                response = self.llm_client.invoke(prompt)

                # 解析JSON
                expanded_queries = self._parse_llm_response(response)

                # 验证并限制数量
                expanded_queries = self._validate_queries(expanded_queries, sub_q_text, year, group)

                # === 【Layer 2增强】添加实体精确查询（修复Q5/Q7） ===
                expanded_queries = self._add_entity_queries(expanded_queries, sub_q_text)

                # === 使用子问题文本作为key（字典不能作为dict key） ===
                # 如果sub_q是dict，则使用question字段作为key；如果是字符串，直接使用
                map_key = sub_q_text if isinstance(sub_q, dict) else sub_q
                expanded_queries_map[map_key] = expanded_queries

                logger.success(
                    f"[QueryExpansionNode] 子问题{idx}生成{len(expanded_queries)}个扩展查询"
                )
                for i, query in enumerate(expanded_queries, start=1):
                    logger.debug(f"  {i}. {query}")

            except Exception as e:
                logger.error(f"[QueryExpansionNode] 子问题{idx}扩展失败: {e}")
                # Fallback: 使用原始子问题文本
                map_key = sub_q_text if isinstance(sub_q, dict) else sub_q
                expanded_queries_map[map_key] = [sub_q_text]

        return expanded_queries_map

    async def _expand_all_concurrent(self, sub_questions: List, original_question: str,
                                    year: str, group: str, topic: str) -> Dict[str, List[str]]:
        """
        并发模式：同时扩展所有子问题（4-5倍速度提升）

        Args:
            sub_questions: 子问题列表
            original_question: 原始问题
            year: 年份
            group: 党派
            topic: 主题

        Returns:
            扩展查询映射字典
        """
        # 创建并发任务
        tasks = []
        for idx, sub_q in enumerate(sub_questions, start=1):
            task = self._expand_single_async(idx, sub_q, original_question, year, group, topic)
            tasks.append(task)

        # 并发执行所有任务
        logger.info(f"[QueryExpansionNode] 启动 {len(tasks)} 个并发LLM调用...")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 构建结果映射
        expanded_queries_map = {}
        for idx, (sub_q, result) in enumerate(zip(sub_questions, results), start=1):
            # 提取子问题文本
            if isinstance(sub_q, dict):
                sub_q_text = sub_q.get("question", str(sub_q))
            else:
                sub_q_text = str(sub_q)

            map_key = sub_q_text if isinstance(sub_q, dict) else sub_q

            # 处理结果或异常
            if isinstance(result, Exception):
                logger.error(f"[QueryExpansionNode] 子问题{idx}并发扩展失败: {result}")
                expanded_queries_map[map_key] = [sub_q_text]
            else:
                expanded_queries_map[map_key] = result
                logger.success(f"[QueryExpansionNode] 子问题{idx}生成{len(result)}个扩展查询")

        logger.info(f"[QueryExpansionNode] ✅ 并发扩展完成，共处理 {len(expanded_queries_map)} 个子问题")
        return expanded_queries_map

    async def _expand_single_async(self, idx: int, sub_q: Any, original_question: str,
                                  year: str, group: str, topic: str) -> List[str]:
        """
        异步扩展单个子问题

        Args:
            idx: 子问题索引
            sub_q: 子问题（字符串或字典）
            original_question: 原始问题
            year: 年份
            group: 党派
            topic: 主题

        Returns:
            扩展查询列表
        """
        # 提取子问题文本
        if isinstance(sub_q, dict):
            sub_q_text = sub_q.get("question", str(sub_q))
        else:
            sub_q_text = str(sub_q)

        logger.debug(f"[QueryExpansionNode] 异步扩展子问题{idx}: {sub_q_text[:50]}...")

        try:
            # 构建Prompt
            prompt = build_query_expansion_prompt(
                original_question=original_question,
                sub_question=sub_q_text,
                year=year,
                group=group,
                topic=topic
            )

            # 异步调用LLM（使用LangChain的ainvoke）
            from langchain_core.messages import HumanMessage
            response = await self.llm_client.llm.ainvoke([HumanMessage(content=prompt)])

            # 解析JSON
            expanded_queries = self._parse_llm_response(response.content)

            # 验证并限制数量
            expanded_queries = self._validate_queries(expanded_queries, sub_q_text, year, group)

            # === 【Layer 2增强】添加实体精确查询（修复Q5/Q7） ===
            expanded_queries = self._add_entity_queries(expanded_queries, sub_q_text)

            return expanded_queries

        except Exception as e:
            logger.error(f"[QueryExpansionNode] 子问题{idx}异步扩展失败: {e}")
            # Fallback: 使用原始子问题
            return [sub_q_text]

    def _parse_llm_response(self, response: str) -> List[str]:
        """
        解析LLM返回的JSON格式响应

        Args:
            response: LLM响应字符串

        Returns:
            扩展查询列表

        Raises:
            ValueError: JSON解析失败
        """
        try:
            # 尝试直接解析JSON
            data = json.loads(response)
            queries = data.get("expanded_queries", [])

            if not queries or not isinstance(queries, list):
                raise ValueError("expanded_queries字段不存在或格式错误")

            return queries

        except json.JSONDecodeError:
            # 尝试提取JSON块
            logger.warning("[QueryExpansionNode] 直接JSON解析失败，尝试提取JSON块...")

            import re
            # 查找 ```json ... ``` 或 { ... }
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r'\{.*"expanded_queries".*\}', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    raise ValueError("无法从响应中提取JSON")

            data = json.loads(json_str)
            queries = data.get("expanded_queries", [])

            if not queries or not isinstance(queries, list):
                raise ValueError("expanded_queries字段不存在或格式错误")

            return queries

    def _validate_queries(self, queries: List[str], original_sub_q: str,
                         year: str = "", group: str = "") -> List[str]:
        """
        验证并过滤扩展查询

        Args:
            queries: 原始查询列表
            original_sub_q: 原始子问题
            year: 年份
            group: 党派

        Returns:
            验证后的查询列表
        """
        validated = []

        for query in queries:
            if not query or not isinstance(query, str):
                continue

            query = query.strip()

            # 长度验证（15-120字符）
            if len(query) < 15 or len(query) > 120:
                logger.debug(f"[QueryExpansionNode] 查询长度不合规: {query}")
                continue

            # 必须包含年份（如果指定了年份）
            if year and year not in query:
                logger.debug(f"[QueryExpansionNode] 查询缺少年份{year}: {query}")
                # 尝试修复：添加年份
                query = f"{query} {year}"

            # 必须包含党派（如果指定了党派）
            if group and group not in query:
                logger.debug(f"[QueryExpansionNode] 查询缺少党派{group}: {query}")
                # 尝试修复：添加党派
                query = f"{group} {query}"

            validated.append(query)

        # 确保至少有原始子问题
        if not validated:
            logger.warning("[QueryExpansionNode] 所有扩展查询验证失败，使用原始子问题")
            validated = [original_sub_q]

        # 限制数量
        if len(validated) > self.expansion_count:
            validated = validated[:self.expansion_count]

        # 去重
        validated = list(dict.fromkeys(validated))  # 保持顺序的去重

        return validated

    def _extract_entities(self, text: str) -> List[str]:
        """
        从文本中提取专有名词（实体）- 修复Q5/Q7类问题

        提取类型：
        1. 国家名（以-ien/-land/-stan结尾）: Georgien, Syrien, Deutschland
        2. 项目名（引号包裹或特定模式）: "Kultur baut Brücken"
        3. 法律/缩写（连续大写）: GEAS, EU, CDU
        4. 政策术语（特定模式）: Asylpaket II, sichere Herkunftsländer

        Args:
            text: 输入文本（问题或子问题）

        Returns:
            提取的实体列表
        """
        entities = []

        # 1. 国家名（德语国家名后缀）
        # 匹配模式：大写字母开头 + 小写字母 + ien/land/stan
        countries = re.findall(r'\b[A-ZÄÖÜ][a-zäöüß]+(?:ien|land|stan)\b', text)
        entities.extend(countries)

        # 2. 项目/计划名（引号包裹）
        # 匹配 "Kultur baut Brücken" 或 „Kultur baut Brücken"
        quoted_programs = re.findall(r'["""„]([^"""„]+)[""""]', text)
        entities.extend(quoted_programs)

        # 3. 法律/缩写（2个及以上连续大写字母）
        # 排除常见词（如CD, TV等）
        acronyms = re.findall(r'\b[A-ZÄÖÜ]{2,}\b', text)
        # 过滤：排除纯数字、单个字母
        acronyms = [a for a in acronyms if not a.isdigit() and len(a) >= 2]
        entities.extend(acronyms)

        # 4. 政策术语（特定模式）
        # 匹配 "词 + 罗马数字" 或 "sichere + 名词"
        policy_terms = re.findall(r'\b(?:Asylpaket|Integrationsgesetz|Masterplan)\s+[IVX]+\b', text)
        entities.extend(policy_terms)

        # 匹配 "sichere/sicherer/sichere + 名词"
        safe_terms = re.findall(r'\bsicher[e|er|es]?\s+[A-ZÄÖÜ][a-zäöüß]+\b', text)
        entities.extend(safe_terms)

        # 去重并过滤
        entities = list(dict.fromkeys(entities))  # 保持顺序去重

        # 过滤：长度至少3个字符
        entities = [e for e in entities if len(e.strip()) >= 3]

        if entities:
            logger.info(f"[QueryExpansionNode] 提取到{len(entities)}个实体: {entities}")

        return entities

    def _add_entity_queries(self, validated_queries: List[str], sub_q_text: str) -> List[str]:
        """
        为提取的实体添加精确查询（修复Q5/Q7）

        Args:
            validated_queries: 已验证的查询列表
            sub_q_text: 子问题文本

        Returns:
            增强后的查询列表（原查询 + 实体精确查询）
        """
        # 从子问题中提取实体
        entities = self._extract_entities(sub_q_text)

        if not entities:
            return validated_queries

        # 为每个实体生成精确匹配查询
        entity_queries = []
        for entity in entities:
            # 使用引号包裹实体，确保精确匹配
            # 注意：Pinecone支持引号精确匹配
            entity_query = f'"{entity}"'
            entity_queries.append(entity_query)

        # 合并：实体查询 + 原查询
        # 实体查询放在前面，优先级更高
        enhanced_queries = entity_queries + validated_queries

        logger.info(
            f"[QueryExpansionNode] 添加{len(entity_queries)}个实体精确查询，"
            f"总查询数: {len(enhanced_queries)}"
        )

        return enhanced_queries
