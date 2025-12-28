"""
Pinecone数据检索节点
从Pinecone向量数据库检索相关材料
支持多年份分层检索策略

【架构解耦优化】
- 知识图谱扩展与问题复杂度解耦
- 简单问题也可以触发KG扩展
- 在Retrieve层独立判断是否需要KG扩展
"""

import asyncio
from typing import List, Dict, Optional
from ...vectordb.pinecone_retriever import PineconeRetriever, create_pinecone_retriever
from ...llm.embeddings import GeminiEmbeddingClient
from ...llm.client import GeminiLLMClient
from ...utils.logger import logger
from ...utils.performance_monitor import get_performance_monitor
from ..state import GraphState, update_state
from ..knowledge_graph import get_knowledge_graph_manager


class PineconeRetrieveNode:
    """
    Pinecone数据检索节点

    功能:
    1. 为每个问题(或子问题)检索相关材料
    2. 支持混合检索(向量+元数据过滤)
    3. 支持多年份分层检索(确保每年都有代表性文档)
    4. 输出详细的检索过程信息(年份分布、相似度等)

    优化:
    - 默认top_k=50,支持10+年时间跨度
    - 智能识别长时间跨度查询,自动使用分层检索
    - 输出内部思考过程,便于调试
    """

    def __init__(
        self,
        retriever: PineconeRetriever = None,
        embedding_client: GeminiEmbeddingClient = None,
        top_k: int = 100,  # 提升到100,进一步增加召回量
        index_name: str = "german-bge",
        enable_multi_year_strategy: bool = True,  # 启用多年份策略
        limit_per_year: int = 8,  # 多年份策略时每年的文档数（从5提升到8）
        enable_concurrent: bool = True,  # 启用并发检索
        enable_kg_expansion: bool = True  # 【架构解耦】启用独立的KG扩展判断
    ):
        """
        初始化Pinecone检索节点

        Args:
            retriever: Pinecone检索器,如果为None则自动创建
            embedding_client: Embedding客户端
            top_k: 默认返回的top-k结果
            index_name: Pinecone索引名称
            enable_multi_year_strategy: 是否启用多年份分层检索策略
            limit_per_year: 多年份策略时每年返回的文档数
            enable_concurrent: 是否启用并发检索(默认True, 可提升3-4倍速度)
            enable_kg_expansion: 是否启用独立的知识图谱扩展(用于简单问题)
        """
        self.index_name = index_name
        self.top_k = top_k
        self.enable_multi_year_strategy = enable_multi_year_strategy
        self.limit_per_year = limit_per_year
        self.enable_concurrent = enable_concurrent
        self.enable_kg_expansion = enable_kg_expansion

        # 创建或使用提供的retriever
        if retriever is None:
            try:
                logger.info(f"[PineconeRetrieveNode] 初始化Pinecone检索器...")
                self.retriever = create_pinecone_retriever(
                    index_name=index_name,
                    default_limit=top_k
                )

                # 获取统计信息
                stats = self.retriever.get_stats()
                logger.info(
                    f"[PineconeRetrieveNode] Pinecone连接成功: "
                    f"向量数={stats['total_vectors']:,}, 维度={stats['dimension']}"
                )

            except Exception as e:
                logger.error(f"[PineconeRetrieveNode] 创建检索器失败: {str(e)}")
                raise RuntimeError(f"无法初始化Pinecone检索器: {str(e)}")
        else:
            self.retriever = retriever

        self.embedding_client = embedding_client or GeminiEmbeddingClient()

        # 【德语Query扩展】初始化Flash LLM客户端用于快速翻译
        try:
            self.flash_client = GeminiLLMClient(model_name="gemini-2.5-flash")
            logger.info("[PineconeRetrieveNode] Flash LLM客户端已初始化（用于德语翻译）")
        except Exception as e:
            logger.warning(f"[PineconeRetrieveNode] Flash LLM初始化失败: {e}，德语扩展将被禁用")
            self.flash_client = None

        # 【架构解耦】初始化知识图谱管理器
        self.kg_manager = None
        if enable_kg_expansion:
            try:
                self.kg_manager = get_knowledge_graph_manager()
                logger.info("[PineconeRetrieveNode] 知识图谱管理器已初始化（架构解耦模式）")
            except Exception as e:
                logger.warning(f"[PineconeRetrieveNode] 知识图谱初始化失败: {e}，将跳过KG扩展")

        logger.info(
            f"[PineconeRetrieveNode] 初始化完成: "
            f"top_k={top_k}, 多年份策略={enable_multi_year_strategy}, "
            f"每年文档数={limit_per_year}, 并发检索={enable_concurrent}, "
            f"KG扩展={enable_kg_expansion}"
        )

    def __call__(self, state: GraphState) -> GraphState:
        """
        执行数据检索

        Args:
            state: 当前状态

        Returns:
            更新后的状态
        """
        # 性能监控开始
        import time
        start_time = time.time()
        monitor = get_performance_monitor()

        # 获取问题列表
        sub_questions = state.get("sub_questions")
        parameters = state.get("parameters", {})

        # 【深度分析模式】检测是否启用
        deep_thinking_mode = state.get("deep_thinking_mode", False)
        reasoning_steps = state.get("reasoning_steps", [])

        if deep_thinking_mode:
            logger.info("[PineconeRetrieveNode] 🔍 深度分析模式已启用")
            reasoning_steps.append("1. 深度分析模式已启用，将进行全面的知识图谱扩展")

        # 【架构解耦】检测是否是简单问题，并尝试KG扩展
        kg_expansion_info = None
        if sub_questions:
            questions = sub_questions
            logger.info(f"[PineconeRetrieveNode] 检索 {len(questions)} 个子问题")
            if deep_thinking_mode:
                reasoning_steps.append(f"2. 问题已拆解为 {len(questions)} 个子问题")
        else:
            # 简单问题路径：独立进行KG扩展判断
            original_question = state["question"]
            questions = [original_question]
            logger.info(f"[PineconeRetrieveNode] 检索原始问题（简单问题路径）")

            # 【修复】只有在深度分析模式下才启用KG扩展
            # 简单问题默认不进行KG扩展，除非用户主动选择深度分析
            if deep_thinking_mode and self.enable_kg_expansion and self.kg_manager:
                logger.info("[PineconeRetrieveNode] 🧠 深度分析模式：启用知识图谱扩展")
                kg_queries, kg_expansion_info = self._apply_kg_expansion_for_simple_question(
                    question=original_question,
                    intent=state.get("intent", "simple"),
                    question_type=state.get("question_type", "事实查询"),
                    parameters=parameters,
                    force_expansion=True  # 深度模式强制扩展
                )
                if kg_queries:
                    # 将KG扩展查询添加到检索任务中
                    questions = self._merge_kg_queries_to_questions(
                        original_question, kg_queries
                    )
                    logger.info(f"[PineconeRetrieveNode] KG扩展后检索 {len(questions)} 个查询")

                    if deep_thinking_mode:
                        reasoning_steps.append(
                            f"2. 知识图谱扩展: 触发{kg_expansion_info.get('expansion_level', '')}级别，"
                            f"生成{len(kg_queries)}个扩展查询"
                        )
                        if kg_expansion_info.get('matched_topics'):
                            reasoning_steps.append(
                                f"3. 匹配主题: {', '.join(kg_expansion_info.get('matched_topics', []))}"
                            )

        # 输出内部思考过程
        thinking_process = []
        thinking_process.append("=== 检索策略分析 ===")
        thinking_process.append(f"问题数量: {len(questions)}")
        thinking_process.append(f"提取参数: {parameters}")

        try:
            # === 并发优化：根据配置选择串行或并发检索 ===
            if self.enable_concurrent:
                logger.info(f"[PineconeRetrieveNode] 🚀 使用并发模式检索 {len(questions)} 个问题")
                retrieval_results, no_material_found, overall_year_distribution = asyncio.run(
                    self._retrieve_all_concurrent(questions, parameters, thinking_process)
                )
            else:
                logger.info(f"[PineconeRetrieveNode] 使用串行模式检索 {len(questions)} 个问题")
                retrieval_results, no_material_found, overall_year_distribution = self._retrieve_all_sequential(
                    questions, parameters, thinking_process
                )

            # 总结检索情况
            thinking_process.append("\n=== 检索总结 ===")
            thinking_process.append(f"总文档数: {sum(len(r['chunks']) for r in retrieval_results)}")
            thinking_process.append(f"整体年份分布: {overall_year_distribution}")
            thinking_process.append(f"找到材料: {'是' if not no_material_found else '否'}")

            # 记录性能监控
            end_time = time.time()
            duration = end_time - start_time
            monitor.record_timing("Pinecone检索", duration)

            thinking_process.append(f"检索耗时: {duration:.2f}秒")

            # 输出思考过程
            logger.info(f"\n[内部思考过程]\n" + "\n".join(thinking_process))

            # 构建更新字典
            update_dict = {
                "retrieval_results": retrieval_results,
                "no_material_found": no_material_found,
                "retrieval_thinking": "\n".join(thinking_process),
                "overall_year_distribution": overall_year_distribution,
                "current_node": "retrieve",
                "next_node": "exception" if no_material_found else "rerank"
            }

            # 【深度分析模式】更新推理步骤
            if deep_thinking_mode:
                reasoning_steps.append(
                    f"4. 检索完成: 获取到 {sum(len(r['chunks']) for r in retrieval_results)} 个文档"
                )
                update_dict["reasoning_steps"] = reasoning_steps

            # 【架构解耦】如果有KG扩展信息，添加到顶级字段和metadata
            if kg_expansion_info:
                # 添加到顶级字段（用于UI显示）
                update_dict["kg_expansion_info"] = kg_expansion_info

                # 同时添加到metadata（向后兼容）
                existing_metadata = state.get("metadata", {}) or {}
                update_dict["metadata"] = {
                    **existing_metadata,
                    "kg_expansion": kg_expansion_info,
                    "kg_expansion_source": "retrieve_node"  # 标记KG扩展来源
                }
                logger.info(f"[PineconeRetrieveNode] KG扩展信息已添加到state")

            return update_state(state, **update_dict)

        except Exception as e:
            logger.error(f"[PineconeRetrieveNode] 检索失败: {str(e)}")

            # 记录性能监控（即使失败也要记录）
            end_time = time.time()
            duration = end_time - start_time
            monitor.record_timing("Pinecone检索", duration)

            return update_state(
                state,
                error=f"检索失败: {str(e)}",
                no_material_found=True,
                current_node="retrieve",
                next_node="exception"
            )

    def _retrieve_for_question(
        self,
        question: str,
        parameters: Dict,
        thinking_process: List[str],
        question_metadata: Dict = None
    ) -> tuple[List[Dict], Dict[str, int], str]:
        """
        为单个问题检索材料（支持单年针对性检索 + Query扩展）

        Args:
            question: 问题
            parameters: 提取的参数
            thinking_process: 思考过程列表(用于记录)
            question_metadata: 子问题元数据（包含target_year等）

        Returns:
            (检索结果列表, 年份分布, 检索方法)
        """
        # === Phase 4: Query扩展策略 ===
        # 生成查询变体以提高召回率
        query_variants = self._generate_query_variants(question)
        thinking_process.append(f"📝 Query扩展: 生成 {len(query_variants)} 个查询变体")
        for i, variant in enumerate(query_variants, 1):
            thinking_process.append(f"   变体{i}: {variant[:80]}...")

        # 为每个变体生成向量
        query_vectors = []
        for variant in query_variants:
            vector = self.embedding_client.embed_text(variant)
            query_vectors.append((variant, vector))

        # ===  新增：单年针对性检索策略 ===
        if question_metadata is None:
            question_metadata = {}

        target_year = question_metadata.get("target_year")
        retrieval_strategy = question_metadata.get("retrieval_strategy", "multi_year")

        # 存储所有变体的检索结果
        all_results = []

        # 策略1: 单年检索（优先）
        if target_year and retrieval_strategy == "single_year":
            thinking_process.append(f"✅ 使用单年检索策略: target_year={target_year}")

            # 构造单年过滤条件
            filters = self._extract_filters(parameters)
            # 强制覆盖year为target_year
            filters['year'] = target_year

            thinking_process.append(f"单年过滤条件: {filters}")

            # 对每个查询变体执行检索
            for i, (variant_text, variant_vector) in enumerate(query_vectors, 1):
                variant_results = self.retriever.search(
                    query_vector=variant_vector,
                    limit=30,  # 每个变体召回30个，增加召回量
                    filters=filters if filters else None
                )
                thinking_process.append(f"   变体{i}召回: {len(variant_results)}个文档")
                all_results.extend(variant_results)

            retrieval_method = f"single_year_expanded(year={target_year}, variants={len(query_vectors)})"
            thinking_process.append(f"单年扩展检索完成，总计 {len(all_results)} 个文档（去重前）")

        # 策略2: 多年检索（原有逻辑）
        else:
            # 提取过滤条件
            filters = self._extract_filters(parameters)
            thinking_process.append(f"过滤条件: {filters}")

            # 判断是否使用多年份策略
            years = filters.get('year', [])
            if isinstance(years, str):
                years = [years]

            use_multi_year = (
                self.enable_multi_year_strategy and
                isinstance(years, list) and
                len(years) >= 3  # 3年及以上使用分层检索
            )

            if use_multi_year:
                thinking_process.append(f"检测到{len(years)}年跨度，使用多年份分层检索策略")
                retrieval_method = f"multi_year_stratified_expanded(years={len(years)}, variants={len(query_vectors)})"

                # 提取其他过滤条件（去除year）
                other_filters = {k: v for k, v in filters.items() if k != 'year'}

                # 对每个查询变体执行多年份检索
                for i, (variant_text, variant_vector) in enumerate(query_vectors, 1):
                    variant_results = self.retriever.search_multi_year_parallel(
                        query_vector=variant_vector,
                        years=years,
                        limit_per_year=self.limit_per_year,
                        other_filters=other_filters if other_filters else None
                    )
                    thinking_process.append(f"   变体{i}召回: {len(variant_results)}个文档")
                    all_results.extend(variant_results)
            else:
                thinking_process.append(f"使用标准检索 + Query扩展")
                retrieval_method = f"standard_expanded(variants={len(query_vectors)})"

                # 对每个查询变体执行标准检索
                for i, (variant_text, variant_vector) in enumerate(query_vectors, 1):
                    variant_results = self.retriever.search(
                        query_vector=variant_vector,
                        limit=30,  # 每个变体30个，增加召回量
                        filters=filters if filters else None
                    )
                    thinking_process.append(f"   变体{i}召回: {len(variant_results)}个文档")
                    all_results.extend(variant_results)

                # 【P1增强】多层降级策略
                if len(all_results) == 0 and filters:
                    all_results, retrieval_method = self._execute_fallback_strategy(
                        query_vectors=query_vectors,
                        original_filters=filters,
                        thinking_process=thinking_process,
                        current_method=retrieval_method
                    )

        # 去重并按相似度重新排序
        results = self._deduplicate_and_rerank(all_results, top_k=self.top_k)
        thinking_process.append(f"去重并重排序后: {len(results)}个文档")

        # 统计年份分布
        year_distribution = {}
        for result in results:
            year = result['metadata'].get('year', 'unknown')
            year_distribution[year] = year_distribution.get(year, 0) + 1

        # 格式化结果（转换为LangGraph统一格式）
        chunks = []
        seen_texts = set()  # 用于去重

        for result in results:
            metadata = result['metadata']
            text = result['text']

            # 去重：使用文本的前100字符作为唯一标识
            text_signature = text[:100] if len(text) > 100 else text

            if text_signature in seen_texts:
                logger.debug(f"[去重] 跳过重复文档: {metadata.get('speaker')}, {metadata.get('date')}")
                continue

            seen_texts.add(text_signature)

            chunks.append({
                "text": text,
                "metadata": {
                    "year": metadata.get("year"),
                    "month": metadata.get("month"),
                    "day": metadata.get("day"),
                    "date": metadata.get("date"),
                    "id": metadata.get("id"),  # Document ID for citation
                    "source_reference": metadata.get("source_reference"),  # User-friendly reference
                    "speaker": metadata.get("speaker"),
                    "party": metadata.get("party"),
                    "group": metadata.get("group"),
                    "group_chinese": metadata.get("group_chinese"),
                    "session": metadata.get("session"),
                    "lp": metadata.get("lp"),
                },
                "score": result['score'],
                "id": result['id']
            })

        if len(seen_texts) < len(results):
            logger.info(f"[去重] 移除了 {len(results) - len(seen_texts)} 个重复文档，保留 {len(chunks)} 个")

        return chunks, year_distribution, retrieval_method

    # 党派名称映射（统一为Pinecone存储格式）
    PARTY_NAME_MAPPING = {
        "BÜNDNIS 90/DIE GRÜNEN": "Grüne/Bündnis 90",
        "BÜNDNIS 90": "Grüne/Bündnis 90",
        "DIE GRÜNEN": "Grüne/Bündnis 90",
        "GRÜNE": "Grüne/Bündnis 90",
        "绿党": "Grüne/Bündnis 90",
        # 其他党派保持不变
        "CDU/CSU": "CDU/CSU",
        "SPD": "SPD",
        "FDP": "FDP",
        "DIE LINKE": "DIE LINKE",
        "AfD": "AfD",
    }

    def _extract_filters(self, parameters: Dict) -> Dict:
        """
        从参数中提取Pinecone过滤条件

        支持时间语义理解:
        - "2015年以来" -> ['2015', '2016', ..., '2024']
        - "2015-2018" -> ['2015', '2016', '2017', '2018']
        - "2019年" -> ['2019']

        Args:
            parameters: 提取的参数

        Returns:
            Pinecone格式的过滤条件
        """
        filters = {}

        # 时间过滤（增强版）
        time_range = parameters.get("time_range", {})

        # 提取年份参数
        start_year = time_range.get("start_year")
        end_year = time_range.get("end_year")
        specific_years = time_range.get("specific_years", [])

        # 🔧 修复: 优先使用specific_years（离散年份），避免离散对比被误判为连续范围
        # 例如 "2019年与2017年相比" 应该只检索 ['2017', '2019']，而不是 ['2017', '2018', '2019']
        if specific_years:
            # 具体年份列表 (优先级最高，支持离散对比)
            filters['year'] = specific_years if isinstance(specific_years, list) else [specific_years]
            logger.debug(f"[PineconeRetrieveNode] 使用specific_years: {filters['year']}")
        elif start_year and end_year:
            # 范围查询: 只在没有specific_years时使用，展开为连续年份列表
            try:
                year_list = [str(y) for y in range(int(start_year), int(end_year) + 1)]
                filters['year'] = year_list
                logger.debug(f"[PineconeRetrieveNode] 年份范围 {start_year}-{end_year} -> {year_list}")
            except:
                pass

        # 党派过滤
        parties = parameters.get("parties", [])
        if parties and parties != ["ALL_PARTIES"]:
            # 跳过ALL_PARTIES（表示不限制党派）
            if "ALL_PARTIES" not in parties:
                # 应用党派名称映射
                normalized_parties = [
                    self.PARTY_NAME_MAPPING.get(p, p) for p in parties
                ]
                filters['party'] = normalized_parties[0] if len(normalized_parties) == 1 else normalized_parties
                logger.debug(f"[PineconeRetrieveNode] 党派映射: {parties} -> {normalized_parties}")

        # 发言人过滤
        speakers = parameters.get("speakers", [])
        if speakers:
            filters['speaker'] = speakers[0]

        return filters

    def _generate_query_variants(self, question: str) -> List[str]:
        """
        生成查询变体以提高召回率（Phase 4: Query扩展）

        策略:
        1. 原始查询（保留完整语义）
        2. 关键词提取查询（去除冗余词）
        3. 动作词强化查询（针对具体措施添加相关动词）

        Args:
            question: 原始问题

        Returns:
            查询变体列表（3个）
        """
        variants = []

        # 变体1: 原始查询
        variants.append(question)

        # 变体2: 关键词提取版本
        keyword_query = self._extract_keywords(question)
        if keyword_query != question:  # 只有不同时才添加
            variants.append(keyword_query)

        # 变体3: 动作词强化版本
        action_query = self._generate_action_variant(question)
        if action_query not in variants:  # 避免重复
            variants.append(action_query)

        # 变体4: 【方案A】德语翻译版本（解决跨语言检索Gap）
        german_query = self._generate_german_variant(question)
        if german_query and german_query not in variants:
            # 德语变体放在最前面，优先级最高
            variants.insert(1, german_query)
            logger.info(f"[PineconeRetrieveNode] 添加德语检索变体")

        return variants

    def _extract_keywords(self, query: str) -> str:
        """
        提取查询中的关键词（无需LLM，纯规则）

        去除:
        - 疑问词: Was ist, Wie, Welche, etc.
        - 助动词: die Position von, im Jahr, etc.
        - 介词: zur, zu, von, im, etc.

        示例:
        "Was ist die Position von CDU/CSU zur Abschiebung und Rückführung im Jahr 2017?"
        → "CDU/CSU Abschiebung Rückführung 2017"

        Args:
            query: 原始查询

        Returns:
            关键词查询
        """
        import re

        # 移除常见疑问词和短语
        noise_patterns = [
            r'\b(Was ist|Was sind|Wie|Welche|Welcher|Welches|Warum|Wann)\b',
            r'\b(die Position|die Positionen|die Hauptansichten|die Hauptposition)\b',
            r'\b(von|vom|zu|zur|zum|im|in der|in den|auf|für|über)\b',
            r'\b(Jahr|Zeitraum|Thema)\b',
            r'\?',  # 问号
        ]

        result = query
        for pattern in noise_patterns:
            result = re.sub(pattern, ' ', result, flags=re.IGNORECASE)

        # 清理多余空格
        result = ' '.join(result.split())

        return result.strip()

    def _generate_action_variant(self, query: str) -> str:
        """
        生成动作词强化变体（针对具体政策措施）

        策略: 如果查询包含某些政策关键词，自动添加相关的动作词

        示例:
        - "Abschiebung" → 添加 "durchsetzen Zwang Ausreisepflicht"
        - "Integration" → 添加 "fördern Maßnahmen Programme"
        - "Klimaschutz" → 添加 "umsetzen Reduktion Maßnahmen"

        Args:
            query: 原始查询

        Returns:
            动作词强化查询
        """
        # 动作词映射表（针对德国议会政策领域）
        action_keywords_map = {
            # 移民/遣返政策
            "Abschiebung": "durchsetzen Zwang Ausreisepflicht konsequent",
            "Rückführung": "durchsetzen Zwang Ausreisepflicht konsequent",
            "Migrationspolitik": "Abschiebung Rückführung Zwang Ausreisepflicht",

            # 融合政策
            "Integration": "fördern Maßnahmen Programme Sprache Bildung",
            "Aufnahme": "fördern Programme Unterstützung",

            # 气候政策
            "Klimaschutz": "umsetzen Reduktion Maßnahmen Emissionen",
            "Klimapolitik": "Emissionen Reduktion Maßnahmen umsetzen",

            # 数字化
            "Digitalisierung": "vorantreiben Infrastruktur Ausbau fördern",

            # 边境控制
            "Grenzkontrollen": "verstärken durchsetzen Sicherheit",
            "Obergrenze": "festlegen durchsetzen begrenzen",
        }

        # 提取关键词版本作为基础
        base = self._extract_keywords(query)

        # 检查是否匹配任何政策关键词
        for keyword, action_words in action_keywords_map.items():
            if keyword in query:
                # 添加动作词
                return f"{base} {action_words}"

        # 如果没有匹配的关键词，返回关键词版本
        return base

    def _generate_german_variant(self, question: str) -> Optional[str]:
        """
        【方案A】将中文问题中的关键词翻译为德语专业术语

        解决跨语言语义检索Gap问题：
        - 问题用中文表述"圣诞免税额"
        - 文档是德文"Weihnachts-Freibetrag"
        - BGE-M3跨语言匹配存在精度损失

        示例:
        "根据Dr. Schmidt在1962年关于圣诞免税额的演讲..."
        → "Dr. Schmidt Weihnachts-Freibetrag SPD 1962"

        Args:
            question: 原始问题（可能含中文）

        Returns:
            德语检索查询，如果翻译失败则返回None
        """
        if not self.flash_client:
            return None

        # 检测是否包含中文字符
        import re
        has_chinese = bool(re.search(r'[\u4e00-\u9fff]', question))
        if not has_chinese:
            return None  # 纯德语问题不需要翻译

        try:
            prompt = f"""将以下中德混合问题转换为纯德语检索查询。

**原问题**: {question}

**转换规则**:
1. 保留所有德语专有名词（人名、党派名、法案名）原样不变
2. 将中文政策术语翻译为德语专业术语
3. 保留年份信息
4. 输出一个简洁的德语检索查询（40-80字符）
5. 只输出德语查询，不要任何解释

**常用术语对照**:
- 难民政策 → Flüchtlingspolitik
- 圣诞免税额 → Weihnachts-Freibetrag
- 数字化 → Digitalisierung
- 气候保护 → Klimaschutz
- 教育政策 → Bildungspolitik
- 外交政策 → Außenpolitik
- 国防政策 → Verteidigungspolitik
- 社会政策 → Sozialpolitik

**德语查询**:"""

            response = self.flash_client.invoke(prompt)
            german_query = response.strip()

            # 验证输出质量
            if len(german_query) < 10 or len(german_query) > 150:
                logger.debug(f"[PineconeRetrieveNode] 德语翻译长度不合规: {len(german_query)}")
                return None

            # 检查是否还有中文（翻译不完整）
            if re.search(r'[\u4e00-\u9fff]', german_query):
                logger.debug(f"[PineconeRetrieveNode] 德语翻译仍含中文，跳过")
                return None

            logger.info(f"[PineconeRetrieveNode] 🇩🇪 德语变体: {german_query[:60]}...")
            return german_query

        except Exception as e:
            logger.warning(f"[PineconeRetrieveNode] 德语翻译失败: {e}")
            return None

    def _deduplicate_and_rerank(self, results: List[Dict], top_k: int) -> List[Dict]:
        """
        去重并按相似度重新排序

        Args:
            results: 检索结果列表（可能包含重复）
            top_k: 保留的文档数

        Returns:
            去重并排序后的结果列表
        """
        # 使用文档ID去重（Pinecone的ID是唯一的）
        seen_ids = set()
        unique_results = []

        for result in results:
            doc_id = result.get('id')
            if doc_id not in seen_ids:
                seen_ids.add(doc_id)
                unique_results.append(result)

        # 按相似度降序排序
        unique_results.sort(key=lambda x: x.get('score', 0), reverse=True)

        # 保留top_k个
        return unique_results[:top_k]

    def _execute_fallback_strategy(
        self,
        query_vectors: List[tuple],
        original_filters: Dict,
        thinking_process: List[str],
        current_method: str
    ) -> tuple[List[Dict], str]:
        """
        【P1】多层降级检索策略

        当原始过滤条件返回0结果时，逐层放宽条件重试：
        层次1: 移除party，保留speaker+year
        层次2: 只保留year
        层次3: 纯向量检索（无过滤）

        Args:
            query_vectors: 查询向量列表 [(text, vector), ...]
            original_filters: 原始过滤条件
            thinking_process: 思考过程列表
            current_method: 当前检索方法名

        Returns:
            (检索结果列表, 更新后的检索方法名)
        """
        all_results = []

        # 提取原始过滤条件
        has_speaker = 'speaker' in original_filters
        has_year = 'year' in original_filters
        has_party = 'party' in original_filters

        logger.warning(f"[PineconeRetrieveNode] ⚠️ 原始过滤返回0结果，启动多层降级策略")
        thinking_process.append(f"\n⚠️ 【P1降级策略】原始过滤返回0结果")
        thinking_process.append(f"   原始过滤: {original_filters}")

        # 层次1: 移除party，保留speaker+year
        if has_party and (has_speaker or has_year):
            fallback1_filters = {k: v for k, v in original_filters.items() if k != 'party'}
            thinking_process.append(f"\n   层次1: 移除party过滤")
            thinking_process.append(f"   过滤条件: {fallback1_filters}")

            for i, (variant_text, variant_vector) in enumerate(query_vectors, 1):
                results = self.retriever.search(
                    query_vector=variant_vector,
                    limit=20,
                    filters=fallback1_filters
                )
                thinking_process.append(f"   变体{i}召回: {len(results)}个文档")
                all_results.extend(results)

            if all_results:
                logger.info(f"[PineconeRetrieveNode] ✓ 层次1成功，召回 {len(all_results)} 个文档")
                return all_results, f"{current_method}_fallback1_no_party"

        # 层次2: 只保留year
        if has_year and (has_speaker or has_party):
            fallback2_filters = {'year': original_filters['year']}
            thinking_process.append(f"\n   层次2: 只用year过滤")
            thinking_process.append(f"   过滤条件: {fallback2_filters}")

            for i, (variant_text, variant_vector) in enumerate(query_vectors, 1):
                results = self.retriever.search(
                    query_vector=variant_vector,
                    limit=30,  # 增加数量，因为过滤更宽松
                    filters=fallback2_filters
                )
                thinking_process.append(f"   变体{i}召回: {len(results)}个文档")
                all_results.extend(results)

            if all_results:
                logger.info(f"[PineconeRetrieveNode] ✓ 层次2成功，召回 {len(all_results)} 个文档")
                return all_results, f"{current_method}_fallback2_year_only"

        # 层次3: 纯向量检索（无过滤）
        thinking_process.append(f"\n   层次3: 纯向量检索（无过滤）")

        for i, (variant_text, variant_vector) in enumerate(query_vectors, 1):
            results = self.retriever.search(
                query_vector=variant_vector,
                limit=30,
                filters=None  # 无过滤
            )
            thinking_process.append(f"   变体{i}召回: {len(results)}个文档")
            all_results.extend(results)

        if all_results:
            logger.info(f"[PineconeRetrieveNode] ✓ 层次3成功，召回 {len(all_results)} 个文档")
            return all_results, f"{current_method}_fallback3_no_filter"

        # 所有层次都失败
        thinking_process.append(f"\n   ❌ 所有降级层次都未找到结果")
        logger.error(f"[PineconeRetrieveNode] ❌ 多层降级策略全部失败")
        return [], f"{current_method}_all_fallback_failed"

    def _retrieve_all_sequential(
        self,
        questions: List,
        parameters: Dict,
        thinking_process: List[str]
    ) -> tuple[List[Dict], bool, Dict[str, int]]:
        """
        串行模式：逐个检索问题（原有逻辑）

        Args:
            questions: 问题列表
            parameters: 参数
            thinking_process: 思考过程列表

        Returns:
            (检索结果列表, 是否未找到材料, 整体年份分布)
        """
        retrieval_results = []
        no_material_found = True
        overall_year_distribution = {}

        for i, question_item in enumerate(questions, 1):
            # 支持字典和字符串两种格式
            if isinstance(question_item, dict):
                question_text = question_item.get("question", question_item)
                question_metadata = question_item
            else:
                question_text = question_item
                question_metadata = {
                    "question": question_text,
                    "target_year": None,
                    "retrieval_strategy": "multi_year"
                }

            logger.info(f"[PineconeRetrieveNode] 检索问题 {i}/{len(questions)}: {question_text}")
            thinking_process.append(f"\n--- 子问题 {i} ---")
            thinking_process.append(f"问题: {question_text}")
            if question_metadata.get("target_year"):
                thinking_process.append(f"目标年份: {question_metadata['target_year']}")
                thinking_process.append(f"检索策略: {question_metadata.get('retrieval_strategy', 'single_year')}")

            # 检索（传入元数据）
            chunks, year_dist, retrieval_method = self._retrieve_for_question(
                question_text, parameters, thinking_process, question_metadata
            )

            if chunks:
                no_material_found = False

            # 记录年份分布
            for year, count in year_dist.items():
                overall_year_distribution[year] = overall_year_distribution.get(year, 0) + count

            retrieval_results.append({
                "question": question_text,
                "question_metadata": question_metadata,
                "chunks": chunks,
                "answer": None,
                "year_distribution": year_dist,
                "retrieval_method": retrieval_method,
                "top_similarity_score": chunks[0]['score'] if chunks else 0.0
            })

            logger.info(
                f"[PineconeRetrieveNode] 找到 {len(chunks)} 个相关chunks, "
                f"年份分布={year_dist}, 方法={retrieval_method}"
            )
            thinking_process.append(f"检索到文档数: {len(chunks)}")
            thinking_process.append(f"年份分布: {year_dist}")
            thinking_process.append(f"检索方法: {retrieval_method}")
            if chunks:
                thinking_process.append(f"最高相似度: {chunks[0]['score']:.4f}")

        return retrieval_results, no_material_found, overall_year_distribution

    async def _retrieve_all_concurrent(
        self,
        questions: List,
        parameters: Dict,
        thinking_process: List[str],
        max_retries: int = 2  # 单个查询最大重试次数
    ) -> tuple[List[Dict], bool, Dict[str, int]]:
        """
        并发模式：同时检索所有问题（3-4倍速度提升），带重试机制

        Args:
            questions: 问题列表
            parameters: 参数
            thinking_process: 思考过程列表
            max_retries: 单个查询失败时的最大重试次数

        Returns:
            (检索结果列表, 是否未找到材料, 整体年份分布)
        """
        import time as time_module

        async def retrieve_single(idx: int, question_item, retry_count: int = 0):
            """异步检索单个问题，带重试机制"""
            # 支持字典和字符串两种格式
            if isinstance(question_item, dict):
                question_text = question_item.get("question", question_item)
                question_metadata = question_item
            else:
                question_text = question_item
                question_metadata = {
                    "question": question_text,
                    "target_year": None,
                    "retrieval_strategy": "multi_year"
                }

            logger.debug(f"[PineconeRetrieveNode] 并发检索问题 {idx}/{len(questions)}: {question_text[:50]}...")

            # 创建该问题的独立思考过程列表（避免并发写入冲突）
            question_thinking = []
            question_thinking.append(f"\n--- 子问题 {idx} ---")
            question_thinking.append(f"问题: {question_text}")
            if question_metadata.get("target_year"):
                question_thinking.append(f"目标年份: {question_metadata['target_year']}")
                question_thinking.append(f"检索策略: {question_metadata.get('retrieval_strategy', 'single_year')}")

            try:
                # 在executor中执行检索（因为_retrieve_for_question是同步的）
                loop = asyncio.get_event_loop()
                chunks, year_dist, retrieval_method = await loop.run_in_executor(
                    None,
                    lambda: self._retrieve_for_question(
                        question_text, parameters, question_thinking, question_metadata
                    )
                )

                question_thinking.append(f"检索到文档数: {len(chunks)}")
                question_thinking.append(f"年份分布: {year_dist}")
                question_thinking.append(f"检索方法: {retrieval_method}")
                if chunks:
                    question_thinking.append(f"最高相似度: {chunks[0]['score']:.4f}")

                logger.info(
                    f"[PineconeRetrieveNode] 问题{idx}检索完成: {len(chunks)} chunks, "
                    f"年份分布={year_dist}"
                )

                return {
                    "question": question_text,
                    "question_metadata": question_metadata,
                    "chunks": chunks,
                    "answer": None,
                    "year_distribution": year_dist,
                    "retrieval_method": retrieval_method,
                    "top_similarity_score": chunks[0]['score'] if chunks else 0.0,
                    "thinking": question_thinking  # 返回思考过程
                }

            except Exception as e:
                # 重试机制
                if retry_count < max_retries:
                    wait_time = min(2 ** (retry_count + 1), 8)  # 指数退避，最多等待8秒
                    logger.warning(
                        f"🔄 [PineconeRetrieveNode] 问题{idx}检索失败，"
                        f"等待{wait_time}秒后重试 ({retry_count + 1}/{max_retries}): {str(e)[:100]}"
                    )
                    await asyncio.sleep(wait_time)
                    return await retrieve_single(idx, question_item, retry_count + 1)
                else:
                    # 所有重试都失败
                    logger.error(
                        f"❌ [PineconeRetrieveNode] 问题{idx}检索失败，"
                        f"已重试{max_retries}次: {str(e)}"
                    )
                    raise

        # 创建并发任务
        logger.info(f"[PineconeRetrieveNode] 启动 {len(questions)} 个并发检索任务...")
        tasks = [retrieve_single(idx, q) for idx, q in enumerate(questions, 1)]

        # 并发执行
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        retrieval_results = []
        no_material_found = True
        overall_year_distribution = {}

        for idx, result in enumerate(results, 1):
            if isinstance(result, Exception):
                logger.error(f"[PineconeRetrieveNode] 问题{idx}检索失败: {result}")
                # 添加失败占位符
                retrieval_results.append({
                    "question": questions[idx-1] if isinstance(questions[idx-1], str) else questions[idx-1].get("question", ""),
                    "question_metadata": {},
                    "chunks": [],
                    "answer": None,
                    "year_distribution": {},
                    "retrieval_method": "failed",
                    "top_similarity_score": 0.0
                })
            else:
                # 成功的结果
                if result["chunks"]:
                    no_material_found = False

                # 合并年份分布
                for year, count in result["year_distribution"].items():
                    overall_year_distribution[year] = overall_year_distribution.get(year, 0) + count

                # 合并思考过程到主列表
                thinking_process.extend(result.pop("thinking"))

                retrieval_results.append(result)

        logger.info(f"[PineconeRetrieveNode] ✅ 并发检索完成，共处理 {len(retrieval_results)} 个问题")
        return retrieval_results, no_material_found, overall_year_distribution

    # ========== 【架构解耦】知识图谱扩展相关方法 ==========

    def _apply_kg_expansion_for_simple_question(
        self,
        question: str,
        intent: str,
        question_type: str,
        parameters: Dict,
        force_expansion: bool = False  # 深度模式强制扩展
    ) -> tuple:
        """
        【架构解耦】对简单问题独立应用知识图谱扩展

        此方法实现了KG扩展与问题复杂度的解耦：
        - 简单问题也可以触发KG扩展
        - 不再依赖Decompose节点
        - 深度分析模式下强制触发扩展

        Args:
            question: 原问题
            intent: 问题意图
            question_type: 问题类型
            parameters: 问题参数
            force_expansion: 是否强制扩展（深度分析模式）

        Returns:
            (扩展查询列表, 扩展信息字典)
        """
        if not self.kg_manager:
            return [], None

        try:
            if force_expansion:
                logger.info("[PineconeRetrieveNode] 🔍 【深度分析】强制启用KG扩展...")
            else:
                logger.info("[PineconeRetrieveNode] 【架构解耦】开始简单问题KG扩展判断...")

            # 调用知识图谱扩展判断
            use_kg, expansion_queries, kg_info = self.kg_manager.expand_query(
                question=question,
                intent=intent,
                question_type=question_type,
                parameters=parameters,
                force_expansion=force_expansion  # 传递强制扩展参数
            )

            if use_kg and expansion_queries:
                logger.info(f"[PineconeRetrieveNode] ✅ 简单问题KG扩展触发成功:")
                logger.info(f"  - 扩展级别: {kg_info.get('expansion_level', 'unknown')}")
                logger.info(f"  - 评分: {kg_info.get('score', 0)}")
                logger.info(f"  - 触发原因: {kg_info.get('reasons', [])}")
                logger.info(f"  - 扩展查询数: {len(expansion_queries)}")

                # 记录前5个扩展查询
                for i, eq in enumerate(expansion_queries[:5], 1):
                    logger.info(f"    扩展查询{i}: {eq}")
                if len(expansion_queries) > 5:
                    logger.info(f"    ... 共{len(expansion_queries)}个扩展查询")

                return expansion_queries, kg_info
            else:
                logger.info(f"[PineconeRetrieveNode] 简单问题KG扩展未触发: {kg_info.get('reasons', [])}")
                return [], kg_info

        except Exception as e:
            logger.error(f"[PineconeRetrieveNode] 简单问题KG扩展失败: {e}")
            return [], {"error": str(e)}

    def _merge_kg_queries_to_questions(
        self,
        original_question: str,
        kg_queries: List[str]
    ) -> List[Dict]:
        """
        【架构解耦】将知识图谱扩展查询合并到检索问题列表中

        Args:
            original_question: 原始问题
            kg_queries: KG扩展查询列表

        Returns:
            合并后的问题列表（Dict格式）
        """
        questions = []

        # 1. 原始问题
        questions.append({
            "question": original_question,
            "target_year": None,
            "target_party": None,
            "retrieval_strategy": "multi_year",
            "source": "original"
        })

        # 2. 添加KG扩展查询（去重）
        seen_questions = {original_question.lower().strip()}

        for query in kg_queries:
            query_normalized = query.lower().strip()
            if query_normalized not in seen_questions:
                questions.append({
                    "question": query,
                    "target_year": None,
                    "target_party": None,
                    "retrieval_strategy": "kg_expansion",
                    "source": "knowledge_graph"
                })
                seen_questions.add(query_normalized)

        # 限制总数（避免查询爆炸）
        max_questions = 25  # 简单问题的KG扩展限制
        if len(questions) > max_questions:
            logger.warning(
                f"[PineconeRetrieveNode] KG扩展查询过多({len(questions)})，"
                f"截取前{max_questions}个"
            )
            questions = questions[:max_questions]

        logger.info(
            f"[PineconeRetrieveNode] KG扩展合并完成: "
            f"原始1个 + KG扩展{len(questions)-1}个 = {len(questions)}个查询"
        )

        return questions


if __name__ == "__main__":
    # 测试Pinecone检索节点
    from ..state import create_initial_state, update_state

    print("=== Pinecone检索节点测试 ===")

    # 测试多年份检索
    question = "请概述2015年以来德国基民盟对难民政策的立场发生了哪些主要变化。"
    state = create_initial_state(question)
    state = update_state(
        state,
        intent="complex",
        question_type="变化类",
        parameters={
            "time_range": {
                "start_year": "2015",
                "end_year": "2024",
                "specific_years": [str(y) for y in range(2015, 2025)]
            },
            "parties": ["CDU/CSU"],
            "topics": ["难民"]
        }
    )

    print(f"问题: {question}")
    print(f"参数: {state['parameters']}")
    print("\n如需完整测试,请确保:")
    print("1. PINECONE_VECTOR_DATABASE_API_KEY已设置")
    print("2. Pinecone索引german-bge存在且有2015-2024数据")
    print("3. 运行: python -m src.graph.nodes.retrieve_pinecone")

    try:
        node = PineconeRetrieveNode()
        print(f"\n✅ 节点创建成功，配置:")
        print(f"   - top_k: {node.top_k}")
        print(f"   - 多年份策略: {node.enable_multi_year_strategy}")
        print(f"   - 每年文档数: {node.limit_per_year}")

    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
