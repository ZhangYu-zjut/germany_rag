#!/usr/bin/env python3
"""
多年份RAG系统测试
测试跨年份的复杂查询能力
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
project_root = Path(__file__).parent
sys.path.append(str(project_root))
load_dotenv(project_root / ".env", override=True)

from pinecone import Pinecone
from src.llm.embeddings import GeminiEmbeddingClient
from src.llm.client import GeminiLLMClient
from src.utils.logger import setup_logger
import requests
import json
import re

logger = setup_logger()


# 7个测试问题
TEST_QUESTIONS = [
    {
        "id": 1,
        "question": "请概述2015年以来德国基民盟对难民政策的立场发生了哪些主要变化。",
        "type": "多年变化分析",
        "years": "2015-2024"
    },
    {
        "id": 2,
        "question": "2017年，德国联邦议会中各党派对专业人才移民制度改革分别持什么立场？",
        "type": "单年多党派对比",
        "years": "2017"
    },
    {
        "id": 3,
        "question": "2015年，德国联邦议会中绿党在移民国籍问题上的主要立场和诉求是什么？",
        "type": "单年单党派观点",
        "years": "2015"
    },
    {
        "id": 4,
        "question": "在2015年到2018年期间，德国联邦议会中不同党派在难民家庭团聚问题上的讨论发生了怎样的变化？",
        "type": "跨年多党派变化",
        "years": "2015-2018"
    },
    {
        "id": 5,
        "question": "请对比2015-2017年联盟党与绿党在移民融合政策方面的主张。",
        "type": "跨年两党对比",
        "years": "2015-2017"
    },
    {
        "id": 6,
        "question": "2019年与2017年相比，联邦议会关于难民遣返的讨论有何变化？",
        "type": "两年对比",
        "years": "2017, 2019"
    },
    {
        "id": 7,
        "question": "新冠疫情期间（主要是2020年），联邦议院对坚持气候目标的看法发生了什么变化？请使用2019-2021年的资料进行回答。必要时给出具体引语。",
        "type": "跨年疫情影响分析",
        "years": "2019-2021"
    }
]


def extract_params(question: str) -> dict:
    """从问题中提取参数"""
    params = {}

    # 提取年份
    year_patterns = [
        r'(\d{4})\s*年',  # 2015年
        r'(\d{4})\s*-\s*(\d{4})',  # 2015-2018
        r'(\d{4})',  # 2015
    ]

    years = set()
    for pattern in year_patterns:
        matches = re.findall(pattern, question)
        for match in matches:
            if isinstance(match, tuple):
                for year in match:
                    if 2000 <= int(year) <= 2030:
                        years.add(year)
            else:
                if 2000 <= int(match) <= 2030:
                    years.add(match)

    if years:
        params['years'] = sorted(list(years))

    # 提取党派
    parties_map = {
        'CDU/CSU': ['CDU/CSU', 'CDU', 'CSU', '基民盟', '联盟党'],
        'SPD': ['SPD', '社民党'],
        'BÜNDNIS 90/DIE GRÜNEN': ['绿党', 'GRÜNEN', 'GRÜNE'],
        'DIE LINKE': ['左翼党', 'LINKE'],
        'FDP': ['FDP', '自民党'],
        'AfD': ['AfD', '选择党']
    }

    detected_parties = []
    for standard_name, keywords in parties_map.items():
        for keyword in keywords:
            if keyword in question:
                if standard_name not in detected_parties:
                    detected_parties.append(standard_name)
                break

    if detected_parties:
        params['parties'] = detected_parties

    # 提取主题关键词
    topic_keywords = ['难民', '移民', '融合', '遣返', '家庭团聚', '专业人才', '气候', '疫情']
    topics = [kw for kw in topic_keywords if kw in question]
    if topics:
        params['topics'] = topics

    return params


def retrieve_documents(index, embedding_client, question: str, params: dict, top_k: int = 20):
    """检索相关文档"""
    # 生成查询向量
    query_vector = embedding_client.embed_text(question)

    # 构建过滤器
    filters = {}

    # 年份过滤
    if 'years' in params:
        years = params['years']
        if len(years) == 1:
            filters['year'] = {'$eq': years[0]}
        else:
            filters['year'] = {'$in': years}

    # 党派过滤（暂不使用，让检索更宽泛）
    # if 'parties' in params:
    #     filters['group'] = {'$in': params['parties']}

    # 查询
    query_args = {
        'vector': query_vector,
        'top_k': top_k,
        'include_metadata': True
    }

    if filters:
        query_args['filter'] = filters

    results = index.query(**query_args)

    return results.matches


def rerank_with_cohere(question: str, documents: list, top_n: int = 5):
    """使用Cohere ReRank重排序"""
    cohere_key = os.getenv('COHERE_API_KEY')
    if not cohere_key:
        logger.warning("⚠️ COHERE_API_KEY未设置，跳过ReRank")
        return documents[:top_n]

    try:
        # 准备文档文本
        doc_texts = []
        for doc in documents:
            text = doc.metadata.get('text', '')
            doc_texts.append(text[:2000])  # 限制长度

        # 调用Cohere API
        url = "https://api.cohere.com/v2/rerank"
        headers = {
            "Authorization": f"Bearer {cohere_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "rerank-v3.5",
            "query": question,
            "documents": doc_texts,
            "top_n": top_n
        }

        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()

        # 重新排序
        reranked = []
        for item in result.get('results', []):
            idx = item['index']
            score = item['relevance_score']
            doc = documents[idx]
            doc.rerank_score = score
            reranked.append(doc)

        return reranked

    except Exception as e:
        logger.warning(f"⚠️ ReRank失败: {str(e)}, 使用原始排序")
        return documents[:top_n]


def generate_answer(llm, question: str, documents: list) -> str:
    """生成答案"""
    # 构建context
    context_parts = []
    for i, doc in enumerate(documents, 1):
        metadata = doc.metadata
        speaker = metadata.get('speaker', '未知')
        date = metadata.get('date', '未知')
        party = metadata.get('group', '未知')
        text = metadata.get('text', '')

        context_parts.append(
            f"[文档{i}] {date} | {speaker} ({party})\n{text}\n"
        )

    context = "\n".join(context_parts)

    # 构建提示词
    prompt = f"""你是一个专业的德国议会研究助手。请基于以下文档回答用户问题。

要求：
1. 答案必须基于提供的文档内容
2. 对于多年份、多党派的问题，要清晰地组织答案结构
3. 适当引用具体发言人和日期
4. 如果文档中没有足够信息，明确说明
5. 使用中文回答

问题：{question}

文档内容：
{context}

请提供详细、准确的答案："""

    answer = llm.invoke(prompt)
    return answer


def test_one_question(question_data: dict, index, embedding_client, llm):
    """测试一个问题"""
    qid = question_data['id']
    question = question_data['question']
    qtype = question_data['type']
    years = question_data['years']

    logger.info(f"\n{'='*80}")
    logger.info(f"📝 问题 {qid}: {qtype} ({years})")
    logger.info(f"{'='*80}")
    logger.info(f"问题: {question}")

    # 1. 参数提取
    logger.info(f"\n🔍 1. 参数提取")
    params = extract_params(question)
    logger.info(f"   提取参数: {params}")

    # 2. 文档检索
    logger.info(f"\n📚 2. 文档检索 (top_k=20)")
    start_time = time.time()
    documents = retrieve_documents(index, embedding_client, question, params, top_k=20)
    retrieve_time = time.time() - start_time
    logger.info(f"   检索到 {len(documents)} 个文档")
    logger.info(f"   耗时: {retrieve_time:.2f}秒")

    if documents:
        top_doc = documents[0]
        logger.info(f"   最高相似度: {top_doc.score:.4f}")
        logger.info(f"   示例: {top_doc.metadata.get('speaker', '未知')}, {top_doc.metadata.get('date', '未知')}")

    # 3. ReRank
    logger.info(f"\n🔄 3. Cohere ReRank (top_n=5)")
    start_time = time.time()
    reranked_docs = rerank_with_cohere(question, documents, top_n=5)
    rerank_time = time.time() - start_time
    logger.info(f"   重排后文档数: {len(reranked_docs)}")
    logger.info(f"   耗时: {rerank_time:.2f}秒")

    if reranked_docs and hasattr(reranked_docs[0], 'rerank_score'):
        logger.info(f"   最高ReRank分数: {reranked_docs[0].rerank_score:.4f}")

    # 4. 生成答案
    logger.info(f"\n💬 4. 生成答案")
    start_time = time.time()
    answer = generate_answer(llm, question, reranked_docs)
    generate_time = time.time() - start_time
    logger.info(f"   答案长度: {len(answer)} 字符")
    logger.info(f"   耗时: {generate_time:.2f}秒")

    # 5. 显示答案
    logger.info(f"\n{'='*80}")
    logger.info(f"✅ 答案:")
    logger.info(f"{'='*80}")
    logger.info(answer)
    logger.info(f"\n{'='*80}")

    return {
        "question_id": qid,
        "question": question,
        "type": qtype,
        "years": years,
        "params": params,
        "retrieved_docs": len(documents),
        "reranked_docs": len(reranked_docs),
        "retrieve_time": retrieve_time,
        "rerank_time": rerank_time,
        "generate_time": generate_time,
        "total_time": retrieve_time + rerank_time + generate_time,
        "answer_length": len(answer),
        "answer": answer
    }


def main():
    """主函数"""
    logger.info("="*80)
    logger.info("🚀 多年份RAG系统测试")
    logger.info("="*80)

    # 1. 初始化
    logger.info("\n📦 1. 初始化组件")
    logger.info("-" * 40)

    # Pinecone
    pc = Pinecone(api_key=os.getenv('PINECONE_VECTOR_DATABASE_API_KEY'))
    index = pc.Index('german-bge')
    logger.info("✅ Pinecone连接成功")

    stats = index.describe_index_stats()
    logger.info(f"   索引向量数: {stats['total_vector_count']:,}")

    # Embedding
    embedding_client = GeminiEmbeddingClient(
        embedding_mode="local",
        model_name="BAAI/bge-m3",
        dimensions=1024
    )
    logger.info("✅ Embedding客户端初始化完成")

    # LLM
    llm = GeminiLLMClient(temperature=0.0)
    logger.info("✅ LLM客户端初始化完成")

    # 2. 运行测试
    logger.info("\n📋 2. 运行测试问题")
    logger.info("-" * 40)

    results = []
    for question_data in TEST_QUESTIONS:
        try:
            result = test_one_question(question_data, index, embedding_client, llm)
            results.append(result)
            time.sleep(2)  # 避免API速率限制
        except Exception as e:
            logger.error(f"❌ 问题 {question_data['id']} 测试失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

    # 3. 生成报告
    logger.info("\n" + "="*80)
    logger.info("📊 测试总结")
    logger.info("="*80)

    logger.info(f"\n完成测试: {len(results)}/{len(TEST_QUESTIONS)}")

    if results:
        avg_retrieve = sum(r['retrieve_time'] for r in results) / len(results)
        avg_rerank = sum(r['rerank_time'] for r in results) / len(results)
        avg_generate = sum(r['generate_time'] for r in results) / len(results)
        avg_total = sum(r['total_time'] for r in results) / len(results)

        logger.info(f"\n平均性能:")
        logger.info(f"  检索时间: {avg_retrieve:.2f}秒")
        logger.info(f"  重排时间: {avg_rerank:.2f}秒")
        logger.info(f"  生成时间: {avg_generate:.2f}秒")
        logger.info(f"  总时间: {avg_total:.2f}秒")

        logger.info(f"\n答案质量:")
        logger.info(f"  平均答案长度: {sum(r['answer_length'] for r in results) / len(results):.0f} 字符")
        logger.info(f"  平均检索文档: {sum(r['retrieved_docs'] for r in results) / len(results):.0f}")
        logger.info(f"  平均重排文档: {sum(r['reranked_docs'] for r in results) / len(results):.0f}")

    # 4. 保存结果
    output_file = project_root / "multi_year_rag_test_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    logger.info(f"\n✅ 结果已保存: {output_file}")

    logger.info("\n" + "="*80)
    logger.info("🎉 测试完成!")
    logger.info("="*80)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"❌ 测试过程出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        exit(1)
