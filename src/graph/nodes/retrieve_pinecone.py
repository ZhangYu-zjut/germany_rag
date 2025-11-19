"""
Pinecone数据检索节点
从Pinecone向量数据库检索相关材料
支持多年份分层检索策略
"""

from typing import List, Dict, Optional
from ...vectordb.pinecone_retriever import PineconeRetriever, create_pinecone_retriever
from ...llm.embeddings import GeminiEmbeddingClient
from ...utils.logger import logger
from ...utils.performance_monitor import get_performance_monitor
from ..state import GraphState, update_state


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
        top_k: int = 50,  # 提升到50,支持长时间跨度
        index_name: str = "german-bge",
        enable_multi_year_strategy: bool = True,  # 启用多年份策略
        limit_per_year: int = 5  # 多年份策略时每年的文档数
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
        """
        self.index_name = index_name
        self.top_k = top_k
        self.enable_multi_year_strategy = enable_multi_year_strategy
        self.limit_per_year = limit_per_year

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

        logger.info(
            f"[PineconeRetrieveNode] 初始化完成: "
            f"top_k={top_k}, 多年份策略={enable_multi_year_strategy}, "
            f"每年文档数={limit_per_year}"
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
        if sub_questions:
            questions = sub_questions
            logger.info(f"[PineconeRetrieveNode] 检索 {len(questions)} 个子问题")
        else:
            questions = [state["question"]]
            logger.info(f"[PineconeRetrieveNode] 检索原始问题")

        parameters = state.get("parameters", {})

        # 输出内部思考过程
        thinking_process = []
        thinking_process.append("=== 检索策略分析 ===")
        thinking_process.append(f"问题数量: {len(questions)}")
        thinking_process.append(f"提取参数: {parameters}")

        try:
            # 为每个问题检索
            retrieval_results = []
            no_material_found = True  # 是否找到材料
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
                    "question_metadata": question_metadata,  # 保存元数据
                    "chunks": chunks,
                    "answer": None,  # 待填充
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

            return update_state(
                state,
                retrieval_results=retrieval_results,
                no_material_found=no_material_found,
                retrieval_thinking="\n".join(thinking_process),  # 保存到状态
                overall_year_distribution=overall_year_distribution,
                current_node="retrieve",
                next_node="exception" if no_material_found else "rerank"
            )

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
                    limit=20,  # 每个变体召回20个，总共最多60个
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
                        limit=20,  # 每个变体20个
                        filters=filters if filters else None
                    )
                    thinking_process.append(f"   变体{i}召回: {len(variant_results)}个文档")
                    all_results.extend(variant_results)

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
