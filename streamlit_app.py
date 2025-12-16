#!/usr/bin/env python3
"""
德国议会RAG智能问答系统 - Streamlit UI演示界面
支持德语和中文问题输入
"""

import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

# 加载环境变量
project_root = Path(__file__).parent
sys.path.append(str(project_root))
load_dotenv(project_root / ".env", override=True)

# 导入必要模块
from src.utils.logger import setup_logger
from test_langgraph_complete import create_pinecone_workflow
from src.graph.state import create_initial_state

# 设置页面配置
st.set_page_config(
    page_title="德国议会RAG智能问答系统",
    page_icon="🇩🇪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 初始化logger
logger = setup_logger()


# 自定义CSS样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
        border-bottom: 3px solid #1f77b4;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .question-box {
        background-color: #e3f2fd;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
        margin: 1rem 0;
    }
    .answer-box {
        background-color: #f5f5f5;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #4caf50;
        margin: 1rem 0;
        line-height: 1.8;
    }
    .metadata-box {
        background-color: #fff3e0;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        font-size: 0.9rem;
    }
    .stButton>button {
        width: 100%;
        background-color: #1f77b4;
        color: white;
        font-weight: bold;
        padding: 0.75rem;
        border-radius: 8px;
    }
    .stButton>button:hover {
        background-color: #1565c0;
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """初始化session state"""
    if 'workflow' not in st.session_state:
        st.session_state.workflow = None
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'processing' not in st.session_state:
        st.session_state.processing = False
    if 'selected_question' not in st.session_state:
        st.session_state.selected_question = ""
    # 深度分析模式
    if 'deep_thinking_mode' not in st.session_state:
        st.session_state.deep_thinking_mode = False


def load_workflow():
    """加载工作流（缓存）"""
    if st.session_state.workflow is None:
        with st.spinner("🔧 正在初始化RAG系统..."):
            try:
                st.session_state.workflow = create_pinecone_workflow()
                logger.info("[Streamlit] Workflow初始化成功")
                return True
            except Exception as e:
                st.error(f"❌ 系统初始化失败: {str(e)}")
                logger.error(f"[Streamlit] Workflow初始化失败: {str(e)}")
                return False
    return True


def process_question(question: str):
    """处理用户问题"""
    if not question.strip():
        st.warning("⚠️ 请输入问题")
        return

    # 获取深度分析模式状态
    deep_thinking_mode = st.session_state.get('deep_thinking_mode', False)

    # 添加到历史记录
    st.session_state.chat_history.append({
        "role": "user",
        "content": question,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "deep_mode": deep_thinking_mode  # 记录是否使用深度模式
    })

    # 根据模式显示不同的状态提示
    if deep_thinking_mode:
        status_title = "🧠 深度分析模式 - RAG系统正在深度思考..."
        time_hint = "*（深度分析模式已启用，将进行全面的知识图谱扩展，预计需要 3-5 分钟，请耐心等待...）*"
    else:
        status_title = "🤔 RAG系统正在思考..."
        time_hint = "*（这是最耗时的步骤，预计需要2-3分钟，请耐心等待...）*"

    # 显示处理状态
    with st.status(status_title, expanded=True) as status:
        start_time = time.time()

        try:
            # 步骤 1
            st.write(f"📋 **步骤 1/5**: 分析问题意图... (0.0秒)")
            initial_state = create_initial_state(question, deep_thinking_mode=deep_thinking_mode)
            elapsed_1 = time.time() - start_time

            # 深度模式额外提示
            if deep_thinking_mode:
                st.write("🧠 *深度分析模式：将强制启用知识图谱扩展*")

            # 步骤 2
            st.write(f"🔍 **步骤 2/5**: 提取查询参数... ({elapsed_1:.1f}秒)")
            time.sleep(0.5)
            elapsed_2 = time.time() - start_time

            # 步骤 3
            st.write(f"✂️ **步骤 3/5**: 分解复杂问题... ({elapsed_2:.1f}秒)")
            time.sleep(0.5)
            elapsed_3 = time.time() - start_time

            # 步骤 4（最耗时的部分）
            st.write(f"🔎 **步骤 4/5**: 检索相关文档... ({elapsed_3:.1f}秒)")
            st.write(time_hint)

            # 运行工作流（这是最耗时的部分）
            final_state = st.session_state.workflow.invoke(initial_state)
            elapsed_4 = time.time() - start_time

            # 步骤 5
            st.write(f"📝 **步骤 5/5**: 生成最终答案... ({elapsed_4:.1f}秒)")

            total_time = time.time() - start_time
            st.write(f"⏱️ **总耗时**: {total_time:.1f} 秒")

            # 检查错误
            if final_state.get("error"):
                status.update(label="❌ 处理失败", state="error")
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": f"抱歉，处理过程中出现错误：{final_state['error']}",
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "error": True
                })
                return

            # 提取结果
            final_answer = final_state.get("final_answer", "未能生成答案")
            parameters = final_state.get("parameters", {})
            sub_questions = final_state.get("sub_questions", [])
            year_distribution = final_state.get("overall_year_distribution", {})
            retrieval_results = final_state.get("retrieval_results", [])

            # 深度分析模式相关信息
            kg_expansion_info = final_state.get("kg_expansion_info", None)
            reasoning_steps = final_state.get("reasoning_steps", [])

            # 计算检索到的文档总数
            total_docs = sum(len(r.get('chunks', [])) for r in retrieval_results)

            status.update(
                label=f"✅ 完成！耗时 {total_time:.1f} 秒",
                state="complete"
            )

            # 添加助手回复到历史
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": final_answer,
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "deep_mode": deep_thinking_mode,  # 记录使用的模式
                "metadata": {
                    "time": total_time,
                    "parameters": parameters,
                    "sub_questions": sub_questions,
                    "year_distribution": year_distribution,
                    "total_docs": total_docs,
                    "retrieval_results": retrieval_results,
                    # 深度模式专属信息
                    "kg_expansion_info": kg_expansion_info,
                    "reasoning_steps": reasoning_steps
                }
            })

            logger.info(f"[Streamlit] 问题处理成功，耗时 {total_time:.2f}秒")

        except Exception as e:
            status.update(label="❌ 处理失败", state="error")
            error_msg = f"系统错误: {str(e)}"
            st.error(error_msg)
            logger.error(f"[Streamlit] 问题处理失败: {str(e)}")

            st.session_state.chat_history.append({
                "role": "assistant",
                "content": error_msg,
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "error": True
            })


def display_chat_history():
    """显示对话历史"""
    for msg in st.session_state.chat_history:
        role = msg["role"]
        content = msg["content"]
        timestamp = msg.get("timestamp", "")

        if role == "user":
            # 用户问题
            deep_mode_label = " 🧠" if msg.get("deep_mode") else ""
            st.markdown(f"""
            <div class="question-box">
                <b>👤 用户{deep_mode_label}</b> <span style="color: #999; font-size: 0.85rem;">{timestamp}</span><br/>
                {content}
            </div>
            """, unsafe_allow_html=True)

        else:
            # 助手回答
            if msg.get("error"):
                # 错误消息
                st.markdown(f"""
                <div style="background-color: #ffebee; padding: 1rem; border-radius: 10px; border-left: 5px solid #f44336; margin: 1rem 0;">
                    <b>❌ 系统</b> <span style="color: #999; font-size: 0.85rem;">{timestamp}</span><br/>
                    {content}
                </div>
                """, unsafe_allow_html=True)
            else:
                # 正常答案
                deep_mode_label = " 🧠 深度分析" if msg.get("deep_mode") else ""
                st.markdown(f"""
                <div class="answer-box">
                    <b>🤖 RAG系统{deep_mode_label}</b> <span style="color: #999; font-size: 0.85rem;">{timestamp}</span>
                </div>
                """, unsafe_allow_html=True)

                # 显示答案内容
                st.markdown(content)

                # 显示元数据（可折叠）
                metadata = msg.get("metadata", {})
                if metadata:
                    with st.expander("📊 查看详细信息", expanded=False):
                        col1, col2, col3 = st.columns(3)

                        with col1:
                            st.metric("⏱️ 处理时间", f"{metadata.get('time', 0):.1f} 秒")
                        with col2:
                            st.metric("📄 检索文档数", metadata.get('total_docs', 0))
                        with col3:
                            year_dist = metadata.get('year_distribution', {})
                            st.metric("📅 覆盖年份", len(year_dist))

                        # 提取参数
                        params = metadata.get('parameters', {})
                        if params:
                            st.markdown("**📋 提取的查询参数:**")
                            st.json(params)

                        # 子问题
                        sub_qs = metadata.get('sub_questions', [])
                        if sub_qs:
                            st.markdown(f"**✂️ 问题分解 ({len(sub_qs)}个子问题):**")
                            for i, sq in enumerate(sub_qs, 1):
                                st.markdown(f"{i}. {sq}")

                        # 【深度分析模式】显示推理步骤
                        reasoning_steps = metadata.get('reasoning_steps', [])
                        if reasoning_steps:
                            st.markdown("**🧠 深度分析推理过程:**")
                            for step in reasoning_steps:
                                st.markdown(f"- {step}")

                        # 【深度分析模式】显示知识图谱扩展信息
                        kg_info = metadata.get('kg_expansion_info')
                        if kg_info and kg_info.get('triggered'):
                            st.markdown("**🔗 知识图谱扩展:**")
                            st.markdown(f"- 扩展级别: `{kg_info.get('level', 'N/A')}`")
                            st.markdown(f"- 评分: `{kg_info.get('score', 0)}`")

                            # 显示匹配的主题
                            matched_topics = kg_info.get('matched_topics', [])
                            if matched_topics:
                                st.markdown(f"- 匹配主题: {', '.join(matched_topics[:5])}")

                            # 显示扩展查询（可折叠）
                            expansion_queries = kg_info.get('expansion_queries', [])
                            if expansion_queries:
                                with st.expander(f"查看扩展查询 ({len(expansion_queries)}个)", expanded=False):
                                    for i, q in enumerate(expansion_queries[:15], 1):
                                        st.markdown(f"{i}. {q}")
                                    if len(expansion_queries) > 15:
                                        st.caption(f"...还有 {len(expansion_queries) - 15} 个扩展查询")

                        # 年份分布
                        year_dist = metadata.get('year_distribution', {})
                        if year_dist:
                            st.markdown("**📅 文档年份分布:**")
                            st.bar_chart(
                                {year: count for year, count in sorted(year_dist.items())}
                            )

                        # 检索来源（前5个）
                        retrieval_results = metadata.get('retrieval_results', [])
                        if retrieval_results:
                            st.markdown("**🔍 检索来源示例 (前5个):**")
                            shown = 0
                            for r in retrieval_results:
                                chunks = r.get('chunks', [])
                                for chunk in chunks[:5-shown]:
                                    chunk_meta = chunk.get('metadata', {})
                                    st.markdown(f"""
                                    <div class="metadata-box">
                                        <b>年份:</b> {chunk_meta.get('year', 'N/A')} |
                                        <b>党派:</b> {chunk_meta.get('group', 'N/A')} |
                                        <b>发言人:</b> {chunk_meta.get('speaker', 'N/A')}<br/>
                                        <b>相似度:</b> {chunk.get('score', 0):.3f}
                                    </div>
                                    """, unsafe_allow_html=True)
                                    shown += 1
                                    if shown >= 5:
                                        break
                                if shown >= 5:
                                    break


def main():
    """主函数"""
    # 初始化
    initialize_session_state()

    # 标题
    st.markdown('<div class="main-header">🇩🇪 德国议会RAG智能问答系统</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Intelligentes Frage-Antwort-System für Deutsche Bundestagsreden (1949-2025)</div>', unsafe_allow_html=True)

    # 侧边栏
    with st.sidebar:
        st.header("ℹ️ 系统信息")
        st.markdown("""
        **系统介绍:**
        - 📚 数据范围: 1949-2025年德国联邦议院演讲
        - 🔍 检索方式: 混合检索 (语义 + 元数据)
        - 🤖 LLM: Gemini 2.5 Pro
        - 📊 向量数据库: Pinecone (173,355文档)

        **支持的问题类型:**
        - 单年份/多年份查询
        - 党派观点对比
        - 政策变化分析
        - 发言人观点总结

        **示例问题:**
        """)

        # 7个测试问题（德语版 - 与test_langgraph_complete.py一致）
        example_questions = [
            "Bitte fassen Sie die wichtigsten Veränderungen in der Flüchtlingspolitik der CDU/CSU seit 2015 zusammen.",
            "Welche Positionen vertraten die verschiedenen Parteien im Deutschen Bundestag 2017 zur Reform des Fachkräfteeinwanderungsgesetzes?",
            "Was waren die Hauptpositionen und Forderungen der Grünen zur Migrationsfrage im Deutschen Bundestag 2015?",
            "Wie haben sich die Diskussionen der verschiedenen Parteien im Deutschen Bundestag über die Familienzusammenführung von Flüchtlingen zwischen 2015 und 2018 entwickelt?",
            "Bitte vergleichen Sie die Positionen der Unionsparteien und der Grünen zur Integrationspolitik zwischen 2015 und 2017.",
            "Wie haben sich die Positionen der CDU/CSU zur Migrationspolitik zwischen 2017 und 2019 im Vergleich verändert?",
            "Welche wichtigen Ansichten und Vorschläge vertrat die AfD zur Flüchtlingspolitik im Jahr 2018?"
        ]

        for i, eq in enumerate(example_questions, 1):
            if st.button(
                f"示例 {i}",
                key=f"example_{i}",
                on_click=lambda q=eq: setattr(st.session_state, 'user_input', q)
            ):
                pass  # 回调函数直接设置user_input

        st.markdown("---")

        if st.button(
            "🗑️ 清除对话历史",
            on_click=lambda: setattr(st.session_state, 'chat_history', [])
        ):
            pass  # 回调函数已经清除了历史

        st.markdown("---")

        # 深度分析模式开关
        st.markdown("**🧠 深度分析模式:**")
        deep_mode = st.toggle(
            "启用深度分析",
            value=st.session_state.deep_thinking_mode,
            key="deep_mode_toggle",
            help="开启后将强制进行知识图谱扩展，获取更全面的检索结果。适用于对标准结果不满意时使用。"
        )
        st.session_state.deep_thinking_mode = deep_mode

        if deep_mode:
            st.warning("⏱️ 深度模式预计需要 3-5 分钟")
            st.caption("将强制启用知识图谱扩展，生成更详细的分析报告")
        else:
            st.caption("标准模式，预计 2-3 分钟")

        st.markdown("---")
        st.markdown("**系统状态:**")
        if st.session_state.workflow:
            st.success("✅ 已初始化")
        else:
            st.info("⏳ 待初始化")

    # 加载工作流
    if not load_workflow():
        st.error("❌ 系统初始化失败，请检查配置")
        return

    # 显示对话历史
    if st.session_state.chat_history:
        st.markdown("## 💬 对话历史")
        display_chat_history()
    else:
        st.info("👋 欢迎使用德国议会RAG智能问答系统！请在下方输入您的问题。")

    # 输入区域
    st.markdown("---")
    st.markdown("## ❓ 输入您的问题")

    # 创建两列布局
    col1, col2 = st.columns([5, 1])

    with col1:
        user_input = st.text_area(
            "支持德语和中文输入:",
            height=100,
            placeholder="例如: Welche Positionen vertrat die CDU/CSU zur Flüchtlingspolitik 2015?\n或: 2015年基民盟对难民政策的立场是什么？",
            key="user_input"
        )

    with col2:
        st.markdown("<br/>", unsafe_allow_html=True)
        submit_button = st.button("🚀 提交问题", type="primary")

    # 处理提交
    if submit_button:
        if user_input.strip():
            process_question(user_input)
            st.rerun()
        else:
            st.warning("⚠️ 请输入问题")

    # 页脚
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #999; font-size: 0.85rem;">
        © 2025 德国议会RAG智能问答系统 | Powered by LangGraph + Gemini 2.5 Pro + Pinecone
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
