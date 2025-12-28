#!/usr/bin/env python3
"""
德国议会RAG智能问答系统 - Streamlit UI演示界面
前后端分离版本：通过API调用后端服务

支持德语和中文问题输入
"""

import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

import streamlit as st
import requests
from dotenv import load_dotenv

# 加载环境变量
project_root = Path(__file__).parent
load_dotenv(project_root / ".env", override=True)

# ========== API 配置 ==========
# 优先使用环境变量，否则使用本地默认地址
API_URL = os.getenv("API_URL", "http://localhost:8000")
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "300"))  # 默认5分钟超时

# 时区配置：UTC+8（北京时间）
UTC_PLUS_8 = timezone(timedelta(hours=8))

def get_current_time_str() -> str:
    """获取当前UTC+8时间字符串"""
    return datetime.now(UTC_PLUS_8).strftime("%H:%M:%S")

# 设置页面配置
st.set_page_config(
    page_title="德国议会RAG智能问答系统",
    page_icon="🇩🇪",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
    .api-status-ok {
        background-color: #e8f5e9;
        padding: 0.5rem;
        border-radius: 5px;
        border-left: 3px solid #4caf50;
    }
    .api-status-error {
        background-color: #ffebee;
        padding: 0.5rem;
        border-radius: 5px;
        border-left: 3px solid #f44336;
    }
</style>
""", unsafe_allow_html=True)


# ========== API 调用函数 ==========

def check_api_health() -> Dict[str, Any]:
    """检查API服务健康状态"""
    try:
        response = requests.get(f"{API_URL}/api/v1/health", timeout=10)
        if response.status_code == 200:
            return {"healthy": True, "data": response.json()}
        else:
            return {"healthy": False, "error": f"HTTP {response.status_code}"}
    except requests.exceptions.ConnectionError:
        return {"healthy": False, "error": "无法连接到API服务"}
    except requests.exceptions.Timeout:
        return {"healthy": False, "error": "API服务响应超时"}
    except Exception as e:
        return {"healthy": False, "error": str(e)}


def call_api(question: str, deep_thinking: bool = False) -> Dict[str, Any]:
    """
    调用API进行问答

    Args:
        question: 用户问题
        deep_thinking: 是否启用深度分析模式

    Returns:
        API响应结果
    """
    try:
        endpoint = f"{API_URL}/api/v1/ask"
        payload = {
            "question": question,
            "deep_thinking": deep_thinking
        }

        response = requests.post(
            endpoint,
            json=payload,
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            return {
                "success": False,
                "error": f"API返回错误: HTTP {response.status_code}",
                "detail": response.text
            }

    except requests.exceptions.Timeout:
        return {"success": False, "error": "请求超时，问题可能过于复杂，请稍后重试"}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "无法连接到API服务，请检查服务是否正常运行"}
    except Exception as e:
        return {"success": False, "error": f"请求失败: {str(e)}"}


# ========== Session State 管理 ==========

def initialize_session_state():
    """初始化session state"""
    if 'api_healthy' not in st.session_state:
        st.session_state.api_healthy = False
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'processing' not in st.session_state:
        st.session_state.processing = False
    if 'selected_question' not in st.session_state:
        st.session_state.selected_question = ""
    if 'deep_thinking_mode' not in st.session_state:
        st.session_state.deep_thinking_mode = False


def check_api_status():
    """检查API状态并更新session state"""
    health = check_api_health()
    st.session_state.api_healthy = health["healthy"]
    return health


# ========== 问题处理 ==========

def process_question(question: str):
    """处理用户问题"""
    if not question.strip():
        st.warning("请输入问题")
        return

    deep_thinking_mode = st.session_state.get('deep_thinking_mode', False)

    # 添加到历史记录
    st.session_state.chat_history.append({
        "role": "user",
        "content": question,
        "timestamp": get_current_time_str(),
        "deep_mode": deep_thinking_mode
    })

    # 根据模式显示不同的状态提示
    if deep_thinking_mode:
        status_title = "🧠 深度分析模式 - 正在调用API..."
        time_hint = "*（深度分析模式，预计需要 3-5 分钟）*"
    else:
        status_title = "🤔 正在调用API处理问题..."
        time_hint = "*（预计需要 2-3 分钟）*"

    # 显示处理状态
    with st.status(status_title, expanded=True) as status:
        start_time = time.time()

        st.write(f"📡 正在连接API服务: `{API_URL}`")
        st.write(time_hint)

        # 调用API
        result = call_api(question, deep_thinking_mode)
        total_time = time.time() - start_time

        if not result["success"]:
            status.update(label="❌ 处理失败", state="error")
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": f"抱歉，处理过程中出现错误：{result['error']}",
                "timestamp": get_current_time_str(),
                "error": True
            })
            return

        # 解析API响应
        api_response = result["data"]

        if not api_response.get("success", False):
            status.update(label="❌ 处理失败", state="error")
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": f"抱歉，处理过程中出现错误：{api_response.get('error', '未知错误')}",
                "timestamp": get_current_time_str(),
                "error": True
            })
            return

        # 提取结果
        final_answer = api_response.get("answer", "未能生成答案")
        processing_time_ms = api_response.get("processing_time_ms", 0)

        status.update(
            label=f"✅ 完成！API处理耗时 {processing_time_ms/1000:.1f} 秒，总耗时 {total_time:.1f} 秒",
            state="complete"
        )

        # 添加助手回复到历史
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": final_answer,
            "timestamp": get_current_time_str(),
            "deep_mode": deep_thinking_mode,
            "metadata": {
                "time": processing_time_ms / 1000,
                "total_time": total_time,
                "parameters": api_response.get("parameters"),
                "sub_questions": api_response.get("sub_questions"),
                "sources_count": api_response.get("sources_count", 0),
                "sources": api_response.get("sources"),
                "intent": api_response.get("intent"),
                "question_type": api_response.get("question_type"),
                "kg_expansion_info": api_response.get("kg_expansion_info"),
                "reasoning_steps": api_response.get("reasoning_steps")
            }
        })


# ========== 显示对话历史 ==========

def display_chat_history():
    """显示对话历史"""
    for msg in st.session_state.chat_history:
        role = msg["role"]
        content = msg["content"]
        timestamp = msg.get("timestamp", "")

        if role == "user":
            deep_mode_label = " 🧠" if msg.get("deep_mode") else ""
            st.markdown(f"""
            <div class="question-box">
                <b>👤 用户{deep_mode_label}</b> <span style="color: #999; font-size: 0.85rem;">{timestamp}</span><br/>
                {content}
            </div>
            """, unsafe_allow_html=True)

        else:
            if msg.get("error"):
                st.markdown(f"""
                <div style="background-color: #ffebee; padding: 1rem; border-radius: 10px; border-left: 5px solid #f44336; margin: 1rem 0;">
                    <b>❌ 系统</b> <span style="color: #999; font-size: 0.85rem;">{timestamp}</span><br/>
                    {content}
                </div>
                """, unsafe_allow_html=True)
            else:
                deep_mode_label = " 🧠 深度分析" if msg.get("deep_mode") else ""
                st.markdown(f"""
                <div class="answer-box">
                    <b>🤖 RAG系统{deep_mode_label}</b> <span style="color: #999; font-size: 0.85rem;">{timestamp}</span>
                </div>
                """, unsafe_allow_html=True)

                st.markdown(content)

                # 显示元数据（可折叠）
                metadata = msg.get("metadata", {})
                if metadata:
                    with st.expander("📊 查看详细信息", expanded=False):
                        col1, col2, col3 = st.columns(3)

                        with col1:
                            st.metric("⏱️ API处理时间", f"{metadata.get('time', 0):.1f} 秒")
                        with col2:
                            st.metric("📄 来源文档数", metadata.get('sources_count', 0))
                        with col3:
                            st.metric("🎯 问题类型", metadata.get('question_type', 'N/A'))

                        # 提取参数
                        params = metadata.get('parameters')
                        if params:
                            st.markdown("**📋 提取的查询参数:**")
                            st.json(params)

                        # 子问题
                        sub_qs = metadata.get('sub_questions', [])
                        if sub_qs:
                            st.markdown(f"**✂️ 问题分解 ({len(sub_qs)}个子问题):**")
                            for i, sq in enumerate(sub_qs, 1):
                                if isinstance(sq, dict):
                                    sq_text = sq.get('question', str(sq))
                                else:
                                    sq_text = str(sq)
                                st.markdown(f"{i}. {sq_text}")

                        # 深度分析推理步骤
                        reasoning_steps = metadata.get('reasoning_steps', [])
                        if reasoning_steps:
                            st.markdown("**🧠 深度分析推理过程:**")
                            for step in reasoning_steps:
                                st.markdown(f"- {step}")

                        # 知识图谱扩展信息
                        kg_info = metadata.get('kg_expansion_info')
                        if kg_info and kg_info.get('triggered'):
                            st.markdown("**🔗 知识图谱扩展:**")
                            st.markdown(f"- 扩展级别: `{kg_info.get('level', 'N/A')}`")
                            st.markdown(f"- 评分: `{kg_info.get('score', 0)}`")

                        # 来源文档
                        sources = metadata.get('sources', [])
                        if sources:
                            st.markdown(f"**🔍 检索来源 (前{len(sources)}个):**")
                            for src in sources[:5]:
                                score_val = src.get('score')
                                score_str = f"{score_val:.3f}" if score_val is not None else 'N/A'
                                st.markdown(f"""
                                <div class="metadata-box">
                                    <b>年份:</b> {src.get('year', 'N/A')} |
                                    <b>党派:</b> {src.get('party', 'N/A')} |
                                    <b>发言人:</b> {src.get('speaker', 'N/A')}<br/>
                                    <b>相似度:</b> {score_str}
                                </div>
                                """, unsafe_allow_html=True)


# ========== 主函数 ==========

def main():
    """主函数"""
    initialize_session_state()

    # 标题
    st.markdown('<div class="main-header">🇩🇪 德国议会RAG智能问答系统</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Intelligentes Frage-Antwort-System für Deutsche Bundestagsreden (1949-2025)</div>', unsafe_allow_html=True)

    # 侧边栏
    with st.sidebar:
        st.header("ℹ️ 系统信息")

        # API状态检查
        st.markdown("**🔌 API服务状态:**")
        health = check_api_status()

        if health["healthy"]:
            st.markdown(f"""
            <div class="api-status-ok">
                ✅ API服务正常<br/>
                <small>{API_URL}</small>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="api-status-error">
                ❌ API服务异常<br/>
                <small>{health.get('error', '未知错误')}</small><br/>
                <small>{API_URL}</small>
            </div>
            """, unsafe_allow_html=True)
            st.warning("请确保API服务已启动")

        if st.button("🔄 刷新API状态"):
            st.rerun()

        st.markdown("---")

        st.markdown("""
        **系统介绍:**
        - 📚 数据范围: 1949-2025年德国联邦议院演讲
        - 🔍 检索方式: 混合检索 (语义 + 元数据)
        - 🤖 LLM: Gemini 2.5 Pro
        - 📊 向量数据库: Pinecone

        **支持的问题类型:**
        - 单年份/多年份查询
        - 党派观点对比
        - 政策变化分析
        - 发言人观点总结

        **示例问题:**
        """)

        # 7个测试问题（德语版）
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
                pass

        st.markdown("---")

        if st.button(
            "🗑️ 清除对话历史",
            on_click=lambda: setattr(st.session_state, 'chat_history', [])
        ):
            pass

    # 检查API是否可用
    if not st.session_state.api_healthy:
        st.error(f"""
        ❌ **无法连接到API服务**

        请确保API服务已启动：
        ```bash
        python api_server.py
        ```

        当前配置的API地址: `{API_URL}`

        如需修改API地址，请设置环境变量 `API_URL`
        """)
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

    col1, col2 = st.columns([4, 1])

    with col1:
        user_input = st.text_area(
            "支持德语和中文输入:",
            height=100,
            placeholder="例如: Welche Positionen vertrat die CDU/CSU zur Flüchtlingspolitik 2015?\n或: 2015年基民盟对难民政策的立场是什么？",
            key="user_input"
        )

    with col2:
        # 深度分析模式开关
        deep_mode = st.toggle(
            "🧠 深度分析",
            value=st.session_state.deep_thinking_mode,
            key="deep_mode_toggle",
            help="启用知识图谱扩展，获取更全面的检索结果（需要3-5分钟）"
        )
        st.session_state.deep_thinking_mode = deep_mode

        if deep_mode:
            st.caption("⏱️ 预计 3-5 分钟")
        else:
            st.caption("⏱️ 预计 1-2 分钟")

        submit_button = st.button("🚀 提交问题", type="primary")

    if submit_button:
        if user_input.strip():
            process_question(user_input)
            st.rerun()
        else:
            st.warning("请输入问题")

    # 页脚
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align: center; color: #999; font-size: 0.85rem;">
        © 2025 德国议会RAG智能问答系统 | Powered by LangGraph + Gemini 2.5 Pro + Pinecone<br/>
        <small>API: {API_URL}</small>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
