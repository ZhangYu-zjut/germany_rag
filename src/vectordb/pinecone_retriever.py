"""
Pinecone检索器
为LangGraph工作流提供Pinecone向量检索能力
"""

import os
from typing import List, Dict, Optional, Any
from pinecone import Pinecone
from ..utils.logger import logger


class PineconeRetriever:
    """
    Pinecone检索器

    功能:
    1. 向量相似度检索
    2. 元数据过滤(年份、党派、发言人等)
    3. 支持多年份范围查询
    4. 返回统一格式的检索结果
    """

    def __init__(
        self,
        index_name: str = "german-bge",
        namespace: str = "",
        default_limit: int = 50  # 默认50个结果,支持长时间跨度查询
    ):
        """
        初始化Pinecone检索器

        Args:
            index_name: 索引名称
            namespace: 命名空间
            default_limit: 默认返回结果数
        """
        self.index_name = index_name
        self.namespace = namespace
        self.default_limit = default_limit

        # 初始化Pinecone客户端
        api_key = os.getenv('PINECONE_VECTOR_DATABASE_API_KEY')
        if not api_key:
            raise ValueError("PINECONE_VECTOR_DATABASE_API_KEY未设置")

        # 检查代理设置
        proxy_url = os.getenv('HTTPS_PROXY') or os.getenv('https_proxy') or os.getenv('HTTP_PROXY') or os.getenv('http_proxy')

        if proxy_url:
            self.pc = Pinecone(api_key=api_key, proxy_url=proxy_url)
            logger.debug(f"[PineconeRetriever] 使用代理: {proxy_url}")
        else:
            self.pc = Pinecone(api_key=api_key)

        self.index = self.pc.Index(index_name)

        logger.info(f"[PineconeRetriever] 初始化完成: index={index_name}, default_limit={default_limit}")

    def search(
        self,
        query_vector: List[float],
        limit: Optional[int] = None,
        filters: Optional[Dict] = None,
        include_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """
        执行向量搜索

        Args:
            query_vector: 查询向量
            limit: 返回结果数量
            filters: 元数据过滤条件
            include_metadata: 是否包含元数据

        Returns:
            检索结果列表，统一格式:
            [
                {
                    "id": "...",
                    "score": 0.95,
                    "text": "...",
                    "metadata": {...}
                }
            ]
        """
        limit = limit or self.default_limit

        # 构建查询参数
        query_args = {
            'vector': query_vector,
            'top_k': limit,
            'include_metadata': include_metadata
        }

        # 添加过滤器
        if filters:
            pinecone_filter = self._convert_to_pinecone_filter(filters)
            if pinecone_filter:
                query_args['filter'] = pinecone_filter
                logger.debug(f"[PineconeRetriever] 使用过滤器: {pinecone_filter}")

        # 执行查询
        try:
            results = self.index.query(**query_args)
            logger.info(f"[PineconeRetriever] 检索成功，返回{len(results.matches)}个结果")

            # 转换为统一格式
            formatted_results = []
            for match in results.matches:
                formatted_results.append({
                    "id": match.id,
                    "score": match.score,
                    "text": match.metadata.get('text', '') if match.metadata else '',
                    "metadata": match.metadata or {}
                })

            return formatted_results

        except Exception as e:
            logger.error(f"[PineconeRetriever] 检索失败: {str(e)}")
            raise

    def search_multi_year(
        self,
        query_vector: List[float],
        years: List[str],
        limit_per_year: int = 5,
        other_filters: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        多年份分层检索（策略：每年独立检索，然后合并）

        适用场景: "2015年以来"、"2015-2024"等长时间跨度查询
        保证每年都有代表性文档

        Args:
            query_vector: 查询向量
            years: 年份列表 (e.g., ['2015', '2016', ..., '2024'])
            limit_per_year: 每年返回的文档数
            other_filters: 其他过滤条件(党派、发言人等)

        Returns:
            合并后的检索结果，按相似度排序
        """
        logger.info(f"[PineconeRetriever] 多年份检索: {len(years)}年, 每年{limit_per_year}个文档")

        all_results = []
        year_distribution = {}

        # 预先转换other_filters为Pinecone格式（避免双重转换）
        converted_other_filters = None
        if other_filters:
            converted_other_filters = self._convert_to_pinecone_filter(other_filters)
            logger.debug(f"[PineconeRetriever] 其他过滤条件转换: {other_filters} -> {converted_other_filters}")

        for year in years:
            # 构建当前年份的过滤器(已经是Pinecone格式)
            year_filter = {'year': {'$eq': str(year)}}

            # 合并其他过滤条件(都是Pinecone格式，直接合并)
            if converted_other_filters:
                # 使用$and合并(都已经是Pinecone格式)
                combined_filter = {'$and': [year_filter, converted_other_filters]}
            else:
                combined_filter = year_filter

            # 检索（注意：直接传递Pinecone格式filter到index.query，绕过_convert_to_pinecone_filter）
            try:
                # 直接调用Pinecone index.query，不经过search()方法（避免二次转换）
                query_args = {
                    'vector': query_vector,
                    'top_k': limit_per_year,
                    'filter': combined_filter,
                    'include_metadata': True
                }

                results = self.index.query(**query_args)

                # 转换为统一格式
                year_results = []
                for match in results.matches:
                    year_results.append({
                        "id": match.id,
                        "score": match.score,
                        "text": match.metadata.get('text', '') if match.metadata else '',
                        "metadata": match.metadata or {}
                    })

                year_distribution[year] = len(year_results)
                all_results.extend(year_results)

                logger.debug(f"[PineconeRetriever] {year}年: {len(year_results)}个文档")

            except Exception as e:
                logger.warning(f"[PineconeRetriever] {year}年检索失败: {str(e)}")
                year_distribution[year] = 0

        # 按相似度重新排序
        all_results.sort(key=lambda x: x['score'], reverse=True)

        logger.info(
            f"[PineconeRetriever] 多年份检索完成: 共{len(all_results)}个文档, "
            f"年份分布={year_distribution}"
        )

        return all_results

    def search_multi_year_parallel(
        self,
        query_vector: List[float],
        years: List[str],
        limit_per_year: int = 5,
        other_filters: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        多年份分层检索（并行优化版）

        相比串行版本,使用ThreadPoolExecutor并行查询所有年份,大幅提升性能

        性能对比:
        - 串行版本: 10年 × 8秒 = 80秒
        - 并行版本: max(8秒) = 8-10秒 (提升8-10倍)

        Args:
            query_vector: 查询向量
            years: 年份列表 (e.g., ['2015', '2016', ..., '2024'])
            limit_per_year: 每年返回的文档数
            other_filters: 其他过滤条件(党派、发言人等)

        Returns:
            合并后的检索结果，按相似度排序
        """
        import concurrent.futures

        logger.info(f"[PineconeRetriever] 🚀 并行多年份检索: {len(years)}年, 每年{limit_per_year}个文档")

        # 预先转换other_filters为Pinecone格式
        converted_other_filters = None
        if other_filters:
            converted_other_filters = self._convert_to_pinecone_filter(other_filters)
            logger.debug(f"[PineconeRetriever] 其他过滤条件转换: {other_filters} -> {converted_other_filters}")

        def query_single_year(year: str) -> tuple:
            """
            查询单个年份(线程安全)

            Returns:
                (year, results_list)
            """
            # 构建年份过滤器
            year_filter = {'year': {'$eq': str(year)}}

            # 合并其他过滤条件
            if converted_other_filters:
                combined_filter = {'$and': [year_filter, converted_other_filters]}
            else:
                combined_filter = year_filter

            try:
                # Pinecone查询
                query_args = {
                    'vector': query_vector,
                    'top_k': limit_per_year,
                    'filter': combined_filter,
                    'include_metadata': True
                }

                results = self.index.query(**query_args)

                # 转换为统一格式
                year_results = []
                for match in results.matches:
                    year_results.append({
                        "id": match.id,
                        "score": match.score,
                        "text": match.metadata.get('text', '') if match.metadata else '',
                        "metadata": match.metadata or {}
                    })

                logger.debug(f"[PineconeRetriever] ✓ {year}年: {len(year_results)}个文档")
                return (year, year_results)

            except Exception as e:
                logger.warning(f"[PineconeRetriever] ✗ {year}年检索失败: {str(e)}")
                return (year, [])

        # 并行查询所有年份
        max_workers = min(len(years), 20)  # 限制最大并发数为20
        all_results = []
        year_distribution = {}

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_year = {executor.submit(query_single_year, year): year
                             for year in years}

            # 收集结果
            for future in concurrent.futures.as_completed(future_to_year):
                year = future_to_year[future]
                try:
                    returned_year, year_results = future.result()
                    year_distribution[returned_year] = len(year_results)
                    all_results.extend(year_results)
                except Exception as e:
                    logger.error(f"[PineconeRetriever] {year}年检索异常: {str(e)}")
                    year_distribution[year] = 0

        # 按相似度重新排序
        all_results.sort(key=lambda x: x['score'], reverse=True)

        logger.info(
            f"[PineconeRetriever] ✅ 并行多年份检索完成: 共{len(all_results)}个文档, "
            f"年份分布={year_distribution}"
        )

        return all_results

    def _convert_to_pinecone_filter(self, filters: Dict) -> Dict:
        """
        转换过滤器格式为Pinecone格式

        输入格式:
        {
            "year": "2015" 或 ["2015", "2016"],
            "party": "CDU/CSU",
            "speaker": "Angela Merkel"
        }

        输出格式(Pinecone):
        {
            "year": {"$eq": "2015"} 或 {"$in": ["2015", "2016"]},
            "group": {"$eq": "CDU/CSU"}
        }
        """
        if not filters:
            return {}

        pinecone_filter = {}

        # 年份过滤
        if 'year' in filters:
            year_value = filters['year']
            if isinstance(year_value, list):
                if len(year_value) == 1:
                    pinecone_filter['year'] = {'$eq': year_value[0]}
                else:
                    pinecone_filter['year'] = {'$in': year_value}
            else:
                pinecone_filter['year'] = {'$eq': year_value}

        # 党派过滤 (注意: Pinecone中字段是'group')
        if 'party' in filters:
            party_value = filters['party']
            if isinstance(party_value, list):
                if len(party_value) == 1:
                    pinecone_filter['group'] = {'$eq': party_value[0]}
                else:
                    pinecone_filter['group'] = {'$in': party_value}
            else:
                pinecone_filter['group'] = {'$eq': party_value}

        # 发言人过滤 - 使用模糊匹配策略
        if 'speaker' in filters:
            speaker = filters['speaker']
            # 生成可能的名字变体
            speaker_variants = self._generate_speaker_variants(speaker)
            if len(speaker_variants) == 1:
                pinecone_filter['speaker'] = {'$eq': speaker_variants[0]}
            else:
                # 使用$in匹配多个变体
                pinecone_filter['speaker'] = {'$in': speaker_variants}
                logger.info(f"[PineconeRetriever] 发言人模糊匹配: {speaker} -> {speaker_variants}")

        # 主题过滤 (如果有的话)
        if 'topic' in filters:
            # Pinecone可能需要全文匹配或者使用contains
            pinecone_filter['topic'] = {'$eq': filters['topic']}

        return pinecone_filter

    def _generate_speaker_variants(self, speaker: str) -> List[str]:
        """
        生成发言人名字的可能变体，用于模糊匹配

        解决问题：同一发言人在不同年份使用不同格式
        - "Volker Beck (Köln)" vs "Volker Beck"
        - "Christian Kühn (Tübingen)" vs "Christian Kühn"
        - "Dr. Grünewald, Parl. Staatssekretär" vs "Dr. Grünewald"

        Args:
            speaker: 原始发言人名称

        Returns:
            可能的名字变体列表

        Examples:
            "Volker Beck (Köln)" -> ["Volker Beck (Köln)", "Volker Beck"]
            "Dr. Grünewald, Parl. Staatssekretär" -> ["Dr. Grünewald, Parl. Staatssekretär", "Dr. Grünewald"]
            "Angela Merkel" -> ["Angela Merkel"]
        """
        variants = [speaker]  # 原始名字始终包含

        # 变体1：去除括号中的城市名
        # "Volker Beck (Köln)" -> "Volker Beck"
        if '(' in speaker and ')' in speaker:
            base_name = speaker.split('(')[0].strip()
            if base_name and base_name not in variants:
                variants.append(base_name)
                logger.debug(f"[PineconeRetriever] 变体(去括号): '{speaker}' -> '{base_name}'")

        # 变体2：去除职位（逗号后的部分）
        # "Dr. Grünewald, Parl. Staatssekretär" -> "Dr. Grünewald"
        if ', ' in speaker:
            base_name = speaker.split(', ')[0].strip()
            if base_name and base_name not in variants:
                variants.append(base_name)
                logger.debug(f"[PineconeRetriever] 变体(去职位): '{speaker}' -> '{base_name}'")

        # 变体3：同时去除括号和职位
        # "Dr. Barbara Hendricks, Parl. Staatssekretärin (XYZ)" -> "Dr. Barbara Hendricks"
        if ('(' in speaker or ', ' in speaker) and len(variants) > 1:
            # 对已有变体再次处理
            for v in list(variants):
                if '(' in v:
                    clean = v.split('(')[0].strip()
                    if clean and clean not in variants:
                        variants.append(clean)
                if ', ' in v:
                    clean = v.split(', ')[0].strip()
                    if clean and clean not in variants:
                        variants.append(clean)

        return variants

    def get_stats(self) -> Dict:
        """
        获取索引统计信息

        Returns:
            统计信息字典
        """
        stats = self.index.describe_index_stats()
        return {
            'total_vectors': stats.get('total_vector_count', 0),
            'dimension': stats.get('dimension', 0),
            'index_fullness': stats.get('index_fullness', 0)
        }


def create_pinecone_retriever(
    index_name: str = "german-bge",
    default_limit: int = 50
) -> PineconeRetriever:
    """
    创建Pinecone检索器的工厂函数

    Args:
        index_name: 索引名称
        default_limit: 默认检索数量

    Returns:
        PineconeRetriever实例
    """
    return PineconeRetriever(
        index_name=index_name,
        default_limit=default_limit
    )


if __name__ == "__main__":
    # 测试Pinecone检索器
    print("=== Pinecone检索器测试 ===")

    try:
        retriever = create_pinecone_retriever()
        print(f"✅ 检索器创建成功")

        stats = retriever.get_stats()
        print(f"✅ 索引统计: {stats}")

        print("\n如需完整测试，请:")
        print("1. 确保PINECONE_VECTOR_DATABASE_API_KEY已设置")
        print("2. 确保索引german-bge存在且有数据")
        print("3. 提供查询向量进行实际检索")

    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
