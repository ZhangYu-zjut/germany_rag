"""
数据检索节点
从向量数据库检索相关材料
现在使用Qdrant替代Milvus，提供更好的WSL2兼容性
"""

from typing import List, Dict, Optional
from ...vectordb.qdrant_retriever import QdrantRetriever, create_qdrant_retriever
from ...vectordb.qdrant_client import QdrantClient, create_qdrant_client
from ...llm.embeddings import GeminiEmbeddingClient
from ...utils.logger import logger
from ...utils.performance_monitor import get_performance_monitor
from ..state import GraphState, update_state


class RetrieveNode:
    """
    数据检索节点 (现在使用Qdrant)
    
    功能:
    1. 为每个问题(或子问题)检索相关材料
    2. 支持混合检索(向量+元数据过滤)
    3. 返回分数最高的chunks
    4. 使用Qdrant提供更好的WSL2兼容性
    
    输出:
    - retrieval_results: 检索结果列表
    """
    
    def __init__(
        self,
        retriever: QdrantRetriever = None,
        embedding_client: GeminiEmbeddingClient = None,
        top_k: int = 5,
        collection_name: str = "german_parliament"
    ):
        """
        初始化检索节点
        
        Args:
            retriever: Qdrant检索器,如果为None则自动创建
            embedding_client: Embedding客户端
            top_k: 每个问题返回的top-k结果
            collection_name: Qdrant集合名称
        """
        self.collection_name = collection_name
        
        # 如果没有提供retriever,创建默认的
        if retriever is None:
            try:
                logger.info("[RetrieveNode] 初始化Qdrant检索器...")
                
                # 创建Qdrant客户端
                self.qdrant_client = create_qdrant_client()
                
                # 验证连接和集合
                if not self.qdrant_client.health_check():
                    raise RuntimeError("无法建立Qdrant连接")
                
                logger.info("[RetrieveNode] Qdrant连接成功")
                
                # 检查集合是否存在
                try:
                    collection_info = self.qdrant_client.get_collection_info(collection_name)
                    logger.info(
                        f"[RetrieveNode] 找到现有集合: {collection_name}, "
                        f"数据点: {collection_info['points_count']}"
                    )
                except Exception as e:
                    logger.warning(f"[RetrieveNode] 集合 {collection_name} 不存在: {str(e)}")
                    logger.warning("[RetrieveNode] 将在数据导入时自动创建集合")
                
                # 创建检索器
                self.retriever = QdrantRetriever(
                    qdrant_client=self.qdrant_client,
                    collection_name=collection_name,
                    default_limit=top_k
                )
                
                logger.info("[RetrieveNode] QdrantRetriever创建成功")
                
            except Exception as e:
                logger.error(f"[RetrieveNode] 创建QdrantRetriever失败: {str(e)}")
                raise RuntimeError(f"无法初始化检索器: {str(e)}")
        else:
            self.retriever = retriever
            self.qdrant_client = retriever.client
        
        self.embedding_client = embedding_client or GeminiEmbeddingClient()
        self.top_k = top_k
        
        logger.info(f"[RetrieveNode] 初始化完成，top_k={top_k}, 集合={collection_name}")
        
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
            logger.info(f"[RetrieveNode] 检索 {len(questions)} 个子问题")
        else:
            questions = [state["question"]]
            logger.info(f"[RetrieveNode] 检索原始问题")
        
        parameters = state.get("parameters", {})
        
        try:
            # 为每个问题检索
            retrieval_results = []
            no_material_found = True  # 是否找到材料
            
            for question in questions:
                logger.info(f"[RetrieveNode] 检索问题: {question}")
                
                # 检索
                chunks = self._retrieve_for_question(question, parameters)
                
                if chunks:
                    no_material_found = False
                
                retrieval_results.append({
                    "question": question,
                    "chunks": chunks,
                    "answer": None  # 待填充
                })
                
                logger.info(f"[RetrieveNode] 找到 {len(chunks)} 个相关chunks")
            
            # 更新状态
            
            # 记录性能监控
            end_time = time.time()
            duration = end_time - start_time
            monitor.record_timing("向量检索", duration)
            
            return update_state(
                state,
                retrieval_results=retrieval_results,
                no_material_found=no_material_found,
                current_node="retrieve",
                next_node="exception" if no_material_found else "summarize"
            )
            
        except Exception as e:
            logger.error(f"[RetrieveNode] 检索失败: {str(e)}")
            
            # 记录性能监控（即使失败也要记录）
            end_time = time.time()
            duration = end_time - start_time
            monitor.record_timing("向量检索", duration)
            
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
        parameters: Dict
    ) -> List[Dict]:
        """
        为单个问题检索材料 (使用Qdrant)
        
        Args:
            question: 问题
            parameters: 提取的参数
            
        Returns:
            检索结果列表
        """
        # 生成问题的向量
        query_vector = self.embedding_client.embed_text(question)
        
        # 提取过滤条件 (转换为Qdrant格式)
        filters = self._extract_qdrant_filters(question, parameters)
        
        logger.debug(f"[RetrieveNode] Qdrant过滤条件: {filters}")
        
        # 确保Qdrant连接可用
        if not self.qdrant_client.health_check():
            logger.warning("[RetrieveNode] Qdrant连接检查失败，尝试重连...")
            if not self.qdrant_client.ensure_connection():
                raise RuntimeError("Qdrant连接不可用")
        
        # 使用Qdrant检索器执行搜索
        try:
            results = self.retriever.search(
                query_vector=query_vector,
                limit=self.top_k,
                filters=filters
            )
            
            logger.info(f"[RetrieveNode] Qdrant检索成功，返回 {len(results)} 个结果")
            
        except Exception as e:
            logger.error(f"[RetrieveNode] Qdrant检索失败: {str(e)}")
            # 尝试基础搜索（无过滤）
            try:
                logger.info("[RetrieveNode] 尝试无过滤的基础搜索...")
                results = self.retriever.search(
                    query_vector=query_vector,
                    limit=self.top_k
                )
                logger.info(f"[RetrieveNode] 基础搜索成功，返回 {len(results)} 个结果")
            except Exception as e2:
                logger.error(f"[RetrieveNode] 基础搜索也失败: {str(e2)}")
                raise RuntimeError(f"所有检索方式都失败: {str(e)}")
        
        # 格式化结果 (转换Qdrant结果为统一格式)
        chunks = []
        for result in results:
            # Qdrant结果格式: {id, score, payload, text, metadata}
            metadata = result.get("metadata", {})
            
            chunks.append({
                "text": result.get("text", ""),
                "metadata": {
                    "year": metadata.get("year"),
                    "month": metadata.get("month"),
                    "day": metadata.get("day"),
                    "speaker": metadata.get("speaker"),
                    "party": metadata.get("party"),
                    "group": metadata.get("group"),
                    "group_chinese": metadata.get("group_chinese"),
                    "session": metadata.get("session"),
                    "lp": metadata.get("lp"),
                    "topics": metadata.get("topics", [])
                },
                "score": result.get("score", 0.0),
                "id": result.get("id")
            })
        
        return chunks
    
    def _extract_qdrant_filters(self, question: str, parameters: Dict) -> Dict:
        """
        从问题和参数中提取Qdrant格式的过滤条件
        
        Args:
            question: 问题
            parameters: 参数
            
        Returns:
            Qdrant格式的过滤条件字典
        """
        filters = {}
        
        # 时间过滤
        time_range = parameters.get("time_range", {})
        specific_years = time_range.get("specific_years", [])
        
        # 优先从问题中提取年份
        import re
        year_matches = re.findall(r'\b(19\d{2}|20\d{2})\b', question)
        if year_matches:
            # 如果问题中有明确年份,使用问题中的年份
            year_values = [int(y) for y in year_matches]
            if len(year_values) == 1:
                filters["year"] = year_values[0]
            elif len(year_values) >= 2:
                # TODO: 支持年份范围查询
                filters["year"] = year_values[0]  # 暂时使用第一个年份
        elif specific_years:
            # 否则使用提取的参数
            if len(specific_years) == 1:
                filters["year"] = int(specific_years[0])
            elif len(specific_years) >= 2:
                # TODO: 支持年份范围查询
                filters["year"] = int(specific_years[0])  # 暂时使用第一个年份
        
        # 党派过滤
        parties = parameters.get("parties", [])
        # 从问题中提取党派
        for party in ["CDU/CSU", "SPD", "FDP", "GRÜNE", "DIE LINKE", "AfD"]:
            if party in question:
                filters["party"] = party
                break
        
        # 如果问题中没有,使用参数中的第一个党派
        if "party" not in filters and parties:
            filters["party"] = parties[0]
        
        # 议员过滤
        speakers = parameters.get("speakers", [])
        if speakers:
            filters["speaker"] = speakers[0]
        
        # 主题过滤 (如果参数中有的话)
        topics = parameters.get("topics", [])
        if topics:
            filters["topic"] = topics[0]  # 暂时使用第一个主题
        
        return filters
    
    def _extract_filters(self, question: str, parameters: Dict) -> Dict:
        """
        从问题和参数中提取过滤条件 (向后兼容方法)
        
        Args:
            question: 问题
            parameters: 参数
            
        Returns:
            过滤条件字典
        """
        # 为了向后兼容，直接调用新方法
        return self._extract_qdrant_filters(question, parameters)


if __name__ == "__main__":
    # 测试检索节点 (使用Qdrant)
    from ..state import create_initial_state, update_state
    
    # 测试简单检索
    question = "2019年德国联邦议院讨论了哪些主要议题?"
    state = create_initial_state(question)
    state = update_state(
        state,
        intent="simple",
        question_type="事实查询",
        parameters={
            "time_range": {"specific_years": ["2019"]},
            "topics": ["议题"]
        }
    )
    
    print("=== Qdrant检索节点测试 ===")
    print(f"问题: {question}")
    print("✅ Qdrant无需外部服务，WSL2环境友好")
    print("\n如需测试,请:")
    print("1. 确保已安装 qdrant-client")
    print("2. 运行数据导入脚本导入德国议会数据")
    print("3. 再运行此测试")
    print("\n优势:")
    print("✅ 无Milvus连接超时问题")
    print("✅ 支持本地和云端模式")
    print("✅ 更丰富的元数据过滤")
    
    # 简单功能测试
    try:
        print("\n--- 测试Qdrant客户端创建 ---")
        qdrant_client = create_qdrant_client()
        print("✅ Qdrant客户端创建成功")
        
        # 健康检查
        if qdrant_client.health_check():
            print("✅ Qdrant健康检查通过")
        else:
            print("⚠️ Qdrant健康检查失败(正常，因为还没有数据)")
            
        qdrant_client.close()
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        print("请确保已正确安装 qdrant-client")
