"""
德国议会RAG系统 - Streamlit交互界面 (Pinecone版本)
支持流式输出、实时进度显示、完整workflow测试
"""

import streamlit as st
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加项目路径
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# 设置页面配置
st.set_page_config(
    page_title="德国议会RAG系统",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
st.markdown("""
<style>
    .stProgress > div > div > div > div {
        background-color: #1f77b4;
    }
    .status-box {
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
    }
    .status-running {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
    }
    .status-done {
        background-color: #e8f5e9;
        border-left: 4px solid #4caf50;
    }
    .status-error {
        background-color: #ffebee;
        border-left: 4px solid #f44336;
    }
</style>
""", unsafe_allow_html=True)


def check_environment():
    """检查环境配置"""
    issues = []

    # 检查Pinecone API密钥
    pinecone_key = os.getenv('PINECONE_VECTOR_DATABASE_API_KEY')
    if not pinecone_key:
        issues.append("❌ PINECONE_VECTOR_DATABASE_API_KEY 未设置")
    else:
        st.sidebar.success("✅ Pinecone API Key 已配置")

    # 检查LLM API密钥
    llm_key = os.getenv('GEMINI_API_KEY') or os.getenv('OPENAI_API_KEY')
    if not llm_key:
        issues.append("❌ LLM API Key 未设置")
    else:
        st.sidebar.success("✅ LLM API Key 已配置")

    # 检查Cohere API密钥
    cohere_key = os.getenv('COHERE_API_KEY')
    if not cohere_key:
        issues.append("⚠️ COHERE_API_KEY 未设置 (ReRank功能将不可用)")
    else:
        st.sidebar.success("✅ Cohere API Key 已配置")

    return issues


def create_progress_placeholder():
    """创建进度显示容器"""
    return st.container()


def update_progress(container, stage: str, status: str, message: str = ""):
    """更新进度显示

    Args:
        container: streamlit容器
        stage: 阶段名称
        status: 状态 (running/done/error)
        message: 附加消息
    """
    status_icon = {
        "running": "🔄",
        "done": "✅",
        "error": "❌"
    }

    status_class = {
        "running": "status-running",
        "done": "status-done",
        "error": "status-error"
    }

    icon = status_icon.get(status, "⏸️")
    css_class = status_class.get(status, "")

    with container:
        st.markdown(
            f'<div class="status-box {css_class}">'
            f'{icon} <strong>{stage}</strong>'
            f'{f": {message}" if message else ""}'
            f'</div>',
            unsafe_allow_html=True
        )


def run_complete_workflow_with_progress(question: str, enable_rerank: bool = True):
    """运行完整workflow并显示进度"""

    # 创建进度显示区域
    progress_container = st.empty()
    result_container = st.empty()

    stages = {
        "init": "初始化系统",
        "intent": "意图分析",
        "classify": "问题分类",
        "extract": "参数提取",
        "decompose": "问题分解",
        "retrieve": "文档检索",
        "rerank": "文档重排",
        "summarize": "生成答案"
    }

    try:
        # 1. 初始化
        with progress_container.container():
            update_progress(st, "初始化系统", "running", "加载模型和配置...")

        from src.llm.embeddings import GeminiEmbeddingClient
        from src.llm.client import GeminiLLMClient
        from pinecone import Pinecone
        import requests

        # 初始化组件
        embedding_client = GeminiEmbeddingClient(
            embedding_mode="local",
            model_name="BAAI/bge-m3",
            dimensions=1024
        )

        api_key = os.getenv("PINECONE_VECTOR_DATABASE_API_KEY")
        pc = Pinecone(api_key=api_key)
        index = pc.Index("german-bge")

        llm = GeminiLLMClient(temperature=0.0)

        cohere_api_key = os.getenv("COHERE_API_KEY")

        with progress_container.container():
            update_progress(st, "初始化系统", "done", "✓ 完成")

        # 2. 参数提取
        with progress_container.container():
            update_progress(st, "参数提取", "running", "分析问题关键信息...")

        import re
        params = {}
        year_match = re.search(r'20\d{2}', question)
        if year_match:
            params['year'] = year_match.group()

        parties = []
        if 'CDU/CSU' in question or 'CDU' in question:
            parties.append('CDU/CSU')
        if 'SPD' in question:
            parties.append('SPD')
        if parties:
            params['parties'] = parties

        if '难民' in question or '移民' in question:
            params['topic'] = 'refugee'
        elif '欧盟' in question:
            params['topic'] = 'EU'

        with progress_container.container():
            update_progress(st, "参数提取", "done", f"✓ {params}")

        # 3. 文档检索
        with progress_container.container():
            update_progress(st, "文档检索", "running", "从向量数据库检索相关文档...")

        query_vector = embedding_client.embed_text(question)

        query_params = {
            "vector": query_vector,
            "top_k": 20,
            "include_metadata": True
        }

        filters = []
        if 'year' in params:
            filters.append({"year": {"$eq": params['year']}})
        if 'parties' in params and len(params['parties']) > 0:
            filters.append({"group": {"$in": params['parties']}})

        if filters:
            if len(filters) == 1:
                query_params["filter"] = filters[0]
            else:
                query_params["filter"] = {"$and": filters}

        results = index.query(**query_params)

        chunks = []
        for match in results.matches:
            chunk = {
                "id": match.id,
                "score": match.score,
                "text": match.metadata.get("text", ""),
                "metadata": match.metadata
            }
            chunks.append(chunk)

        with progress_container.container():
            update_progress(st, "文档检索", "done", f"✓ 检索到{len(chunks)}个文档")

        # 4. 文档重排
        reranked_chunks = chunks
        if enable_rerank and cohere_api_key and len(chunks) > 0:
            with progress_container.container():
                update_progress(st, "文档重排", "running", "使用Cohere API重新排序...")

            try:
                documents = [chunk['text'] for chunk in chunks]

                url = "https://api.cohere.com/v2/rerank"
                headers = {
                    "Authorization": f"Bearer {cohere_api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": "rerank-v3.5",
                    "query": question,
                    "documents": documents,
                    "top_n": 10
                }

                response = requests.post(url, headers=headers, json=payload, timeout=30)
                response.raise_for_status()
                result = response.json()

                reranked_chunks = []
                for item in result.get("results", []):
                    index_num = item["index"]
                    relevance_score = item["relevance_score"]

                    reranked_chunk = chunks[index_num].copy()
                    reranked_chunk["rerank_score"] = relevance_score
                    reranked_chunks.append(reranked_chunk)

                with progress_container.container():
                    update_progress(st, "文档重排", "done", f"✓ 重排到{len(reranked_chunks)}个最相关文档")

            except Exception as e:
                with progress_container.container():
                    update_progress(st, "文档重排", "error", f"失败，使用原始排序: {str(e)[:50]}")
                reranked_chunks = chunks[:10]
        else:
            reranked_chunks = chunks[:10]
            with progress_container.container():
                update_progress(st, "文档重排", "done", "✓ 跳过（未启用或无API密钥）")

        # 5. 生成答案
        with progress_container.container():
            update_progress(st, "生成答案", "running", "LLM正在生成答案，请稍候...")

        # 构建context
        context_parts = []
        for i, chunk in enumerate(reranked_chunks, 1):
            metadata = chunk.get('metadata', {})
            speaker = metadata.get('speaker', '未知')
            date = metadata.get('date', '未知')
            group = metadata.get('group', '未知')
            text = chunk.get('text', '')

            context_parts.append(
                f"[文档{i}] 发言人: {speaker}, 党派: {group}, 日期: {date}\n{text}"
            )

        context = "\n\n".join(context_parts)

        prompt = f"""请基于以下德国议会发言记录回答问题。

【问题】
{question}

【参考资料】
{context}

【回答要求】
1. 基于提供的资料进行总结和分析
2. 如果资料不足，请明确说明
3. 引用具体发言人、日期和党派
4. 保持客观和准确

请回答："""

        answer = llm.invoke(prompt)

        with progress_container.container():
            update_progress(st, "生成答案", "done", f"✓ 答案生成完成（{len(answer)}字符）")

        return {
            "success": True,
            "answer": answer,
            "params": params,
            "chunks_retrieved": len(chunks),
            "chunks_reranked": len(reranked_chunks),
            "reranked_chunks": reranked_chunks
        }

    except Exception as e:
        with progress_container.container():
            update_progress(st, "系统错误", "error", str(e))
        return {
            "success": False,
            "error": str(e)
        }


def main():
    # 页面标题
    st.title("🏛️ 德国联邦议院演讲智能问答系统")
    st.markdown("*基于Pinecone向量数据库 + BGE-M3 Embedding + Cohere ReRank + Gemini 2.5 Pro*")
    st.markdown("---")

    # 侧边栏：系统状态
    st.sidebar.header("🔧 系统状态")

    # 环境检查
    issues = check_environment()
    if issues:
        st.sidebar.error("⚠️ 配置问题:")
        for issue in issues:
            st.sidebar.write(issue)

    # 侧边栏：数据范围信息
    st.sidebar.header("📊 当前数据范围")
    st.sidebar.info("""
    **时间范围**: 2015-2016年（已上传）

    **党派覆盖**:
    - CDU/CSU (联盟党)
    - SPD (社会民主党)
    - FDP (自由民主党)
    - BÜNDNIS 90/DIE GRÜNEN (绿党)
    - DIE LINKE (左翼党)
    - AfD (德国选择党)

    **向量数据库**: Pinecone (german-bge索引)
    **总向量数**: ~50,000+
    """)

    # 主界面：问题输入区域
    st.header("💬 智能问答")

    # 2015年测试问题
    st.subheader("📋 2015年测试问题")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**🔍 总结类 & 对比类**")
        test_questions_1 = [
            "请总结2015年德国议会关于难民政策的主要讨论内容",
            "CDU/CSU和SPD在2015年对难民政策的立场有什么不同？",
        ]
        for q in test_questions_1:
            st.markdown(f"- {q}")

    with col2:
        st.markdown("**📊 观点类 & 事实查询**")
        test_questions_2 = [
            "2015年德国议会议员对欧盟一体化的主要观点是什么？",
            "2015年德国议会有哪些重要法案被讨论？"
        ]
        for q in test_questions_2:
            st.markdown(f"- {q}")

    # 问题输入
    st.subheader("✍️ 输入您的问题")

    # 快速选择
    all_test_questions = [
        "请总结2015年德国议会关于难民政策的主要讨论内容",
        "CDU/CSU和SPD在2015年对难民政策的立场有什么不同？",
        "2015年德国议会议员对欧盟一体化的主要观点是什么？",
        "2015年德国议会有哪些重要法案被讨论？"
    ]

    selected_question = st.selectbox("选择测试问题", ["请选择..."] + all_test_questions)

    # 问题输入框
    if selected_question != "请选择...":
        user_question = st.text_area("问题内容", value=selected_question, height=100)
    else:
        user_question = st.text_area(
            "问题内容",
            placeholder="例如：请总结2015年德国议会关于难民政策的主要讨论内容",
            height=100
        )

    # 高级选项
    with st.expander("🔧 高级选项"):
        col1, col2 = st.columns(2)

        with col1:
            enable_rerank = st.checkbox(
                "启用Cohere ReRank",
                value=True,
                help="使用Cohere API进行文档重排，提升答案质量"
            )

        with col2:
            show_retrieved_docs = st.checkbox(
                "显示检索文档",
                value=False,
                help="显示检索到的原始文档内容"
            )

    # 提交按钮
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        submit_button = st.button(
            "🚀 开始问答",
            type="primary",
            disabled=not user_question.strip(),
            use_container_width=True
        )

    if submit_button:
        st.markdown("---")
        st.header("📊 处理进度")

        # 运行workflow
        result = run_complete_workflow_with_progress(user_question, enable_rerank)

        st.markdown("---")

        if result.get("success"):
            # 显示答案
            st.header("💡 生成的答案")
            st.markdown(result['answer'])

            # 显示统计信息
            st.markdown("---")
            st.subheader("📈 处理统计")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("提取参数", len(result.get('params', {})))

            with col2:
                st.metric("检索文档", result.get('chunks_retrieved', 0))

            with col3:
                st.metric("重排后文档", result.get('chunks_reranked', 0))

            with col4:
                st.metric("答案长度", f"{len(result['answer'])} 字符")

            # 显示检索文档
            if show_retrieved_docs and result.get('reranked_chunks'):
                st.markdown("---")
                st.subheader("📄 检索到的文档")

                for i, chunk in enumerate(result['reranked_chunks'][:5], 1):
                    with st.expander(f"文档 {i} - 相关性评分: {chunk.get('rerank_score', chunk.get('score', 0)):.4f}"):
                        metadata = chunk.get('metadata', {})

                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.write(f"**发言人**: {metadata.get('speaker', '未知')}")
                        with col2:
                            st.write(f"**党派**: {metadata.get('group', '未知')}")
                        with col3:
                            st.write(f"**日期**: {metadata.get('date', '未知')}")

                        st.markdown("**文档内容**:")
                        st.text(chunk.get('text', '')[:500] + "...")
        else:
            st.error(f"❌ 处理失败: {result.get('error', '未知错误')}")

    # 页面底部信息
    st.markdown("---")
    st.markdown("""
    ### 💡 使用提示

    1. **完整流程**: 参数提取 → 文档检索(20个) → Cohere重排(10个) → LLM生成答案
    2. **实时进度**: 系统会显示每个处理阶段的实时状态
    3. **ReRank优势**: 启用后可显著提升答案质量，但会增加1-2秒处理时间
    4. **测试问题**: 建议从上方4个测试问题开始体验

    ### 🔧 技术架构
    - **Embedding**: BGE-M3 (本地, 1024维, GPU加速)
    - **向量数据库**: Pinecone (german-bge索引)
    - **重排**: Cohere rerank-v3.5 API
    - **生成**: Gemini 2.5 Pro
    """)


if __name__ == "__main__":
    main()
