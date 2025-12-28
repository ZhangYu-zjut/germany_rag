"""
重排序节点 (ReRank Node)
使用Cohere Rerank API对检索到的文档进行重新排序
"""

import os
import requests
from typing import List, Dict, Any
from langchain_core.documents import Document

from ..state import GraphState, update_state
from ...utils.logger import logger
from ...utils.performance_monitor import get_performance_monitor


class ReRankNode:
    """
    重排序节点

    功能:
    1. 对RetrieveNode检索到的文档进行重新排序
    2. 使用CohereRerank提高文档相关性排序
    3. 【P2】议题关键词加权：对包含问题议题关键词的文档给予额外加分
    4. 保留原始检索结构，增强排序质量

    输入: retrieval_results (检索结果)
    输出: reranked_results (重排后结果)
    """

    def __init__(self, enable_topic_boost: bool = True, topic_boost_weight: float = 0.15):
        """初始化重排序节点

        Args:
            enable_topic_boost: 是否启用议题关键词加权
            topic_boost_weight: 议题关键词加权权重 (0.0-1.0)
        """
        logger.info("[ReRankNode] 初始化重排序节点...")

        try:
            # 检查API密钥
            cohere_api_key = os.getenv("COHERE_API_KEY")
            if not cohere_api_key:
                raise ValueError("COHERE_API_KEY未设置，无法初始化重排序功能")

            # 保存API密钥和配置
            self.cohere_api_key = cohere_api_key
            self.model = "rerank-v3.5"  # 修正：使用正确的模型名
            self.top_n = 25  # 【优化】增加到25，配合top_k=100提供更多高质量文档
            self.api_url = "https://api.cohere.com/v2/rerank"  # 修正：使用v2 API

            # 【P2】议题关键词加权配置
            self.enable_topic_boost = enable_topic_boost
            self.topic_boost_weight = topic_boost_weight

            logger.info(f"[ReRankNode] Cohere Rerank初始化成功, topic_boost={enable_topic_boost}, weight={topic_boost_weight}")

        except Exception as e:
            logger.error(f"[ReRankNode] 初始化失败: {str(e)}")
            raise
    
    def __call__(self, state: GraphState) -> GraphState:
        """
        执行重排序
        
        Args:
            state: 当前状态，包含retrieval_results
            
        Returns:
            更新后的状态，包含reranked_results
        """
        # 性能监控开始
        import time
        start_time = time.time()
        monitor = get_performance_monitor()
        
        logger.info("[ReRankNode] 开始重排序...")
        
        try:
            # 获取检索结果
            retrieval_results = state.get("retrieval_results", [])
            
            if not retrieval_results:
                logger.warning("[ReRankNode] 没有检索结果需要重排序")
                
                # 记录性能监控
                end_time = time.time()
                duration = end_time - start_time
                monitor.record_timing("文档重排", duration)
                
                return update_state(
                    state,
                    reranked_results=[],
                    current_node="rerank",
                    next_node="summarize"
                )
            
            reranked_results = []
            
            # 对每个子问题的检索结果进行重排序
            for i, retrieval_item in enumerate(retrieval_results):
                question = retrieval_item.get("question", "")
                chunks = retrieval_item.get("chunks", [])
                
                logger.info(f"[ReRankNode] 正在重排序第 {i+1}/{len(retrieval_results)} 个问题: {question[:50]}...")
                
                if not chunks:
                    logger.warning(f"[ReRankNode] 第 {i+1} 个问题没有chunks，跳过重排序")
                    reranked_results.append({
                        "question": question,
                        "chunks": [],
                        "answer": None,
                        "rerank_scores": []
                    })
                    continue
                
                # 转换chunks为Document对象进行重排序
                documents = []
                for chunk in chunks:
                    # chunk格式: {"text": "...", "metadata": {...}, "score": 0.95}
                    doc = Document(
                        page_content=chunk.get("text", ""),
                        metadata=chunk.get("metadata", {})
                    )
                    documents.append(doc)
                
                logger.info(f"[ReRankNode] 对 {len(documents)} 个文档进行重排序")
                
                # 使用Cohere API进行重排序
                try:
                    # 修正：转换为正确的文档格式
                    formatted_docs = [{"text": doc.page_content} for doc in documents]
                    reranked_result = self._cohere_rerank(
                        query=question,
                        documents=formatted_docs,
                        top_n=min(self.top_n, len(documents))
                    )

                    logger.info(f"[ReRankNode] 重排序完成，从 {len(documents)} 个文档中选出 {len(reranked_result)} 个")

                    # 【P2】应用议题关键词加权
                    if self.enable_topic_boost:
                        topic_keywords = self._extract_topic_keywords(state)
                        if topic_keywords:
                            reranked_result = self._apply_topic_boost(
                                reranked_result, documents, topic_keywords
                            )

                    # 转换重排序后的文档回chunks格式，并保留重排序分数
                    reranked_chunks = []
                    rerank_scores = []

                    for result in reranked_result:
                        original_idx = result['index']
                        original_doc = documents[original_idx]
                        original_chunk = chunks[original_idx]  # 获取原始chunk以获得score
                        rerank_score = result['relevance_score']

                        chunk = {
                            "text": original_doc.page_content,
                            "metadata": original_doc.metadata,
                            "score": original_chunk.get("score", 0.0),  # 从原始chunk获取检索分数
                            "rerank_score": rerank_score,  # 新增重排序分数
                            "rerank_position": len(reranked_chunks) + 1  # 重排序后的位置
                        }

                        reranked_chunks.append(chunk)
                        rerank_scores.append(rerank_score)
                    
                    # 构建重排序结果
                    reranked_item = {
                        "question": question,
                        "chunks": reranked_chunks,
                        "answer": None,  # 待Summarize节点填充
                        "rerank_scores": rerank_scores,
                        "original_count": len(documents),
                        "reranked_count": len(reranked_chunks)
                    }
                    
                    reranked_results.append(reranked_item)
                    
                    logger.info(f"[ReRankNode] 第 {i+1} 个问题重排序完成，保留 {len(reranked_chunks)} 个文档")
                    
                except Exception as rerank_error:
                    logger.error(f"[ReRankNode] 重排序失败: {str(rerank_error)}")
                    
                    # 重排序失败时，保留原始检索结果
                    fallback_chunks = []
                    for chunk in chunks:
                        fallback_chunk = chunk.copy()
                        fallback_chunk["rerank_score"] = None
                        fallback_chunk["rerank_position"] = None
                        fallback_chunks.append(fallback_chunk)
                    
                    reranked_results.append({
                        "question": question,
                        "chunks": fallback_chunks,
                        "answer": None,
                        "rerank_scores": [],
                        "rerank_error": str(rerank_error)
                    })
            
            logger.info(f"[ReRankNode] 重排序完成，处理了 {len(reranked_results)} 个问题")
            
            # 记录性能监控
            end_time = time.time()
            duration = end_time - start_time
            monitor.record_timing("文档重排", duration)
            
            return update_state(
                state,
                reranked_results=reranked_results,
                current_node="rerank",
                next_node="summarize"
            )
            
        except Exception as e:
            logger.error(f"[ReRankNode] 重排序失败: {str(e)}")
            
            # 记录性能监控（即使失败也要记录）
            end_time = time.time()
            duration = end_time - start_time
            monitor.record_timing("文档重排", duration)
            
            return update_state(
                state,
                error=f"重排序失败: {str(e)}",
                current_node="rerank",
                next_node="exception"
            )
    
    def _cohere_rerank(self, query: str, documents: List[Dict], top_n: int = 10) -> List[Dict]:
        """
        直接调用Cohere API进行重排序
        
        Args:
            query: 查询字符串
            documents: 文档对象列表，格式为[{"text": "..."}, {"text": "..."}]
            top_n: 返回top-n个结果
            
        Returns:
            重排序结果列表，每个元素包含 {index, relevance_score}
        """
        headers = {
            "Authorization": f"Bearer {self.cohere_api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "query": query,
            "documents": documents,
            "top_n": top_n
            # 移除return_documents参数，使用默认值
        }
        
        # 检查代理设置
        proxies = {}
        http_proxy = os.getenv('http_proxy') or os.getenv('HTTP_PROXY')
        https_proxy = os.getenv('https_proxy') or os.getenv('HTTPS_PROXY')
        
        if http_proxy:
            proxies['http'] = http_proxy
        if https_proxy:
            proxies['https'] = https_proxy
            
        if proxies:
            logger.info(f"[ReRankNode] 使用代理访问Cohere API: {proxies}")
        
        try:
            response = requests.post(
                self.api_url, 
                json=data, 
                headers=headers, 
                timeout=30,
                proxies=proxies if proxies else None
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get("results", [])
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[ReRankNode] Cohere API请求失败: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"[ReRankNode] 重排序处理失败: {str(e)}")
            raise
    
    def _log_rerank_results(self, question: str, original_docs: List[Document],
                           reranked_result: List[Dict]) -> None:
        """
        记录重排序结果（调试用）

        Args:
            question: 查询问题
            original_docs: 原始文档列表
            reranked_result: 重排序结果
        """
        logger.debug(f"[ReRankNode] === 重排序详情 ===")
        logger.debug(f"[ReRankNode] 查询: {question}")
        logger.debug(f"[ReRankNode] 原始文档数量: {len(original_docs)}")
        logger.debug(f"[ReRankNode] 重排序后数量: {len(reranked_result)}")

        # 记录前3个重排序后的文档片段
        for i, result in enumerate(reranked_result[:3]):
            doc_idx = result['index']
            score = result['relevance_score']
            doc_text = original_docs[doc_idx].page_content[:100] if doc_idx < len(original_docs) else "N/A"
            logger.debug(f"[ReRankNode] Top-{i+1} (score={score:.3f}): {doc_text}...")

    def _extract_topic_keywords(self, state: GraphState) -> List[str]:
        """
        【P2】从state中提取议题关键词

        从parameters中提取topic字段，以及从question中提取德语关键词

        Args:
            state: 当前状态

        Returns:
            议题关键词列表
        """
        keywords = []

        # 1. 从parameters中提取topic
        parameters = state.get("parameters", {})
        if parameters:
            topic = parameters.get("topic", "")
            if topic:
                # topic可能是德语词组，添加完整topic和拆分后的词
                keywords.append(topic.lower())
                # 拆分topic获取单独的词
                topic_words = topic.replace('-', ' ').replace('/', ' ').split()
                for word in topic_words:
                    clean_word = word.strip().lower()
                    if len(clean_word) >= 3 and clean_word not in keywords:
                        keywords.append(clean_word)

        # 2. 从question中提取德语关键词（常见主题词）
        question = state.get("question", "")
        if question:
            # 德语主题词模式（常见政策领域词汇）
            german_topic_patterns = [
                "integrationskurs", "integration", "flüchtling", "asyl", "migration",
                "wohnung", "miete", "immobilien", "wohnungskrise", "finanzialisierung",
                "stahl", "stahlkrise", "arbeitsplatz", "industrie",
                "frauen", "frauenfragen", "gleichstellung",
                "klima", "umwelt", "energie", "energiewende",
                "digitalisierung", "digital", "datenschutz",
                "gesundheit", "pflege", "rente", "sozial",
                "bildung", "schule", "universität",
                "verteidigung", "sicherheit", "bundeswehr",
                "europa", "eu", "brexit",
                "haushalt", "steuern", "finanzen", "budget"
            ]

            question_lower = question.lower()
            for pattern in german_topic_patterns:
                if pattern in question_lower and pattern not in keywords:
                    keywords.append(pattern)

        logger.info(f"[ReRankNode] 【P2】提取的议题关键词: {keywords}")
        return keywords

    def _apply_topic_boost(
        self,
        reranked_result: List[Dict],
        documents: List[Document],
        topic_keywords: List[str]
    ) -> List[Dict]:
        """
        【P2】对包含议题关键词的文档应用加权

        Args:
            reranked_result: Cohere重排序结果
            documents: 原始文档列表
            topic_keywords: 议题关键词列表

        Returns:
            加权后的重排序结果（按新分数排序）
        """
        if not topic_keywords or not self.enable_topic_boost:
            return reranked_result

        boosted_results = []

        for result in reranked_result:
            doc_idx = result['index']
            original_score = result['relevance_score']

            # 检查文档是否包含议题关键词
            doc_text = documents[doc_idx].page_content.lower() if doc_idx < len(documents) else ""

            keyword_matches = 0
            matched_keywords = []
            for keyword in topic_keywords:
                if keyword in doc_text:
                    keyword_matches += 1
                    matched_keywords.append(keyword)

            # 计算加权后的分数
            if keyword_matches > 0:
                # 每匹配一个关键词，增加topic_boost_weight的加权
                # 使用递减加权：第一个关键词权重最高，后续递减
                boost = 0
                for i in range(keyword_matches):
                    boost += self.topic_boost_weight * (0.7 ** i)  # 递减权重

                boosted_score = min(1.0, original_score + boost)  # 不超过1.0
                logger.debug(f"[ReRankNode] 【P2】文档{doc_idx}匹配关键词{matched_keywords}, "
                           f"原始分数{original_score:.4f} -> 加权分数{boosted_score:.4f}")
            else:
                boosted_score = original_score

            boosted_results.append({
                'index': doc_idx,
                'relevance_score': boosted_score,
                'original_score': original_score,
                'topic_boost_applied': keyword_matches > 0,
                'matched_keywords': matched_keywords
            })

        # 按加权后的分数重新排序
        boosted_results.sort(key=lambda x: x['relevance_score'], reverse=True)

        # 记录加权效果
        boosted_count = sum(1 for r in boosted_results if r.get('topic_boost_applied', False))
        if boosted_count > 0:
            logger.info(f"[ReRankNode] 【P2】议题加权影响了 {boosted_count}/{len(boosted_results)} 个文档")

        return boosted_results


if __name__ == "__main__":
    # 测试重排序节点
    from ..state import create_initial_state
    
    # 创建测试状态
    test_state = create_initial_state("2019年德国议会讨论了哪些主要议题？")
    
    # 模拟检索结果
    test_state["retrieval_results"] = [
        {
            "question": "2019年德国议会讨论了哪些主要议题？",
            "chunks": [
                {
                    "text": "2019年德国联邦议院讨论了移民政策改革...",
                    "metadata": {"source": "doc1.txt", "year": "2019"},
                    "score": 0.85
                },
                {
                    "text": "德国议会在2019年重点关注气候变化议题...",
                    "metadata": {"source": "doc2.txt", "year": "2019"},
                    "score": 0.78
                }
            ],
            "answer": None
        }
    ]
    
    print("=== 测试重排序节点 ===")
    print("注意: 需要设置COHERE_API_KEY环境变量")
    
    try:
        rerank_node = ReRankNode()
        result_state = rerank_node(test_state)
        
        print(f"重排序完成，结果数量: {len(result_state.get('reranked_results', []))}")
        
        if result_state.get('reranked_results'):
            first_result = result_state['reranked_results'][0]
            print(f"第一个结果的chunks数量: {len(first_result.get('chunks', []))}")
            
    except Exception as e:
        print(f"测试失败: {e}")

