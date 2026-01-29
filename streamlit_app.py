#!/usr/bin/env python3
"""
DE-SMART 1.0: Deutsche Semantic Multi-agent Architecture for RAG Technology
Streamlit UI Demo Interface - Frontend calls backend API

Supports German and English question input
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
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "1200"))  # 默认20分钟超时（复杂问题需要更长时间）

# 时区配置：UTC+8（北京时间）
UTC_PLUS_8 = timezone(timedelta(hours=8))

def get_current_time_str() -> str:
    """获取当前UTC+8时间字符串"""
    return datetime.now(UTC_PLUS_8).strftime("%H:%M:%S")

# 设置页面配置
st.set_page_config(
    page_title="DE-SMART 1.0 | German Parliament RAG System",
    page_icon="🏛️",
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
        return {"healthy": False, "error": "Cannot connect to API service"}
    except requests.exceptions.Timeout:
        return {"healthy": False, "error": "API service timeout"}
    except Exception as e:
        return {"healthy": False, "error": str(e)}


def call_api(question: str, deep_thinking: bool = False, progress_callback=None) -> Dict[str, Any]:
    """
    调用API进行问答（使用异步轮询模式，避免长连接超时）

    Args:
        question: 用户问题
        deep_thinking: 是否启用深度分析模式
        progress_callback: 进度回调函数

    Returns:
        API响应结果
    """
    try:
        # 步骤1: 提交异步任务
        submit_endpoint = f"{API_URL}/api/v1/ask/async"
        payload = {
            "question": question,
            "deep_thinking": deep_thinking
        }

        if progress_callback:
            progress_callback("Submitting question...")

        submit_response = requests.post(
            submit_endpoint,
            json=payload,
            timeout=30  # 提交请求应该很快
        )

        if submit_response.status_code != 200:
            return {
                "success": False,
                "error": f"Failed to submit task: HTTP {submit_response.status_code}",
                "detail": submit_response.text
            }

        job_data = submit_response.json()
        job_id = job_data.get("job_id")

        if not job_id:
            return {"success": False, "error": "No job ID returned from server"}

        if progress_callback:
            progress_callback(f"Task submitted (ID: {job_id}), waiting for result...")

        # 步骤2: 轮询任务状态
        status_endpoint = f"{API_URL}/api/v1/jobs/{job_id}"
        poll_interval = 3  # 每3秒轮询一次
        max_polls = API_TIMEOUT // poll_interval  # 最大轮询次数

        for poll_count in range(max_polls):
            time.sleep(poll_interval)

            try:
                status_response = requests.get(status_endpoint, timeout=10)

                if status_response.status_code != 200:
                    continue  # 重试

                status_data = status_response.json()
                job_status = status_data.get("status")

                if progress_callback:
                    progress_info = status_data.get("progress", "Processing...")
                    elapsed = (poll_count + 1) * poll_interval
                    progress_callback(f"[{elapsed}s] {progress_info}")

                if job_status == "completed":
                    result = status_data.get("result")
                    if result:
                        return {"success": True, "data": result}
                    else:
                        return {"success": False, "error": "Task completed but no result returned"}

                elif job_status == "failed":
                    error_msg = status_data.get("error", "Unknown error")
                    return {"success": False, "error": f"Task failed: {error_msg}"}

                # pending 或 processing 状态继续等待

            except requests.exceptions.RequestException:
                # 网络错误，继续重试
                continue

        # 超时
        return {"success": False, "error": f"Task timeout after {API_TIMEOUT} seconds. Please try again."}

    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timeout while submitting task."}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "Cannot connect to API service. Please check if the service is running."}
    except Exception as e:
        return {"success": False, "error": f"Request failed: {str(e)}"}


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
        st.warning("Please enter a question")
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
        status_title = "🧠 Deep Analysis Mode - Processing..."
        time_hint = "*(Deep analysis mode, estimated 3-5 minutes)*"
    else:
        status_title = "🤔 Processing your question..."
        time_hint = "*(Estimated 1-3 minutes)*"

    # 显示处理状态
    with st.status(status_title, expanded=True) as status:
        start_time = time.time()

        st.write(f"📡 API service: `{API_URL}`")
        st.write(time_hint)

        # 创建进度显示区域
        progress_placeholder = st.empty()

        def update_progress(msg: str):
            """更新进度显示"""
            progress_placeholder.write(f"⏳ {msg}")

        # 调用API（使用异步轮询模式）
        result = call_api(question, deep_thinking_mode, progress_callback=update_progress)
        total_time = time.time() - start_time

        if not result["success"]:
            status.update(label="❌ Processing Failed", state="error")
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": f"Sorry, an error occurred during processing: {result['error']}",
                "timestamp": get_current_time_str(),
                "error": True
            })
            return

        # 解析API响应
        api_response = result["data"]

        if not api_response.get("success", False):
            status.update(label="❌ Processing Failed", state="error")
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": f"Sorry, an error occurred during processing: {api_response.get('error', 'Unknown error')}",
                "timestamp": get_current_time_str(),
                "error": True
            })
            return

        # 提取结果
        final_answer = api_response.get("answer", "Unable to generate answer")
        processing_time_ms = api_response.get("processing_time_ms", 0)

        status.update(
            label=f"✅ Complete! API processing: {processing_time_ms/1000:.1f}s, Total: {total_time:.1f}s",
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
                <b>👤 User{deep_mode_label}</b> <span style="color: #999; font-size: 0.85rem;">{timestamp}</span><br/>
                {content}
            </div>
            """, unsafe_allow_html=True)

        else:
            if msg.get("error"):
                st.markdown(f"""
                <div style="background-color: #ffebee; padding: 1rem; border-radius: 10px; border-left: 5px solid #f44336; margin: 1rem 0;">
                    <b>❌ System</b> <span style="color: #999; font-size: 0.85rem;">{timestamp}</span><br/>
                    {content}
                </div>
                """, unsafe_allow_html=True)
            else:
                deep_mode_label = " 🧠 Deep Analysis" if msg.get("deep_mode") else ""
                st.markdown(f"""
                <div class="answer-box">
                    <b>🤖 DE-SMART{deep_mode_label}</b> <span style="color: #999; font-size: 0.85rem;">{timestamp}</span>
                </div>
                """, unsafe_allow_html=True)

                st.markdown(content)

                # 显示元数据（可折叠）
                metadata = msg.get("metadata", {})
                if metadata:
                    with st.expander("📊 View Details", expanded=False):
                        col1, col2, col3 = st.columns(3)

                        with col1:
                            st.metric("⏱️ Processing Time", f"{metadata.get('time', 0):.1f}s")
                        with col2:
                            st.metric("📄 Source Documents", metadata.get('sources_count', 0))
                        with col3:
                            st.metric("🎯 Question Type", metadata.get('question_type', 'N/A'))

                        # 提取参数
                        params = metadata.get('parameters')
                        if params:
                            st.markdown("**📋 Extracted Query Parameters:**")
                            st.json(params)

                        # 子问题
                        sub_qs = metadata.get('sub_questions', [])
                        if sub_qs:
                            st.markdown(f"**✂️ Question Decomposition ({len(sub_qs)} sub-questions):**")
                            for i, sq in enumerate(sub_qs, 1):
                                if isinstance(sq, dict):
                                    sq_text = sq.get('question', str(sq))
                                else:
                                    sq_text = str(sq)
                                st.markdown(f"{i}. {sq_text}")

                        # 深度分析推理步骤
                        reasoning_steps = metadata.get('reasoning_steps', [])
                        if reasoning_steps:
                            st.markdown("**🧠 Deep Analysis Reasoning Process:**")
                            for step in reasoning_steps:
                                st.markdown(f"- {step}")

                        # 知识图谱扩展信息
                        kg_info = metadata.get('kg_expansion_info')
                        if kg_info and kg_info.get('triggered'):
                            st.markdown("**🔗 Knowledge Graph Expansion:**")
                            st.markdown(f"- Expansion Level: `{kg_info.get('level', 'N/A')}`")
                            st.markdown(f"- Score: `{kg_info.get('score', 0)}`")

                        # 来源文档
                        sources = metadata.get('sources', [])
                        if sources:
                            st.markdown(f"**🔍 Retrieved Sources (Top {len(sources)}):**")
                            for src in sources[:5]:
                                score_val = src.get('score')
                                score_str = f"{score_val:.3f}" if score_val is not None else 'N/A'
                                st.markdown(f"""
                                <div class="metadata-box">
                                    <b>Year:</b> {src.get('year', 'N/A')} |
                                    <b>Party:</b> {src.get('party', 'N/A')} |
                                    <b>Speaker:</b> {src.get('speaker', 'N/A')}<br/>
                                    <b>Similarity:</b> {score_str}
                                </div>
                                """, unsafe_allow_html=True)


# ========== 主函数 ==========

def main():
    """主函数"""
    initialize_session_state()

    # 标题
    st.markdown('<div class="main-header">DE-SMART 1.0</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Deutsche Semantic Multi-agent Architecture for RAG Technology<br/><small style="font-size: 0.9rem;">Intelligent Q&A System for German Bundestag Speeches (1949-2025)</small></div>', unsafe_allow_html=True)

    # 侧边栏
    with st.sidebar:
        st.header("ℹ️ System Information")

        # API状态检查
        st.markdown("**🔌 API Service Status:**")
        health = check_api_status()

        if health["healthy"]:
            st.markdown(f"""
            <div class="api-status-ok">
                ✅ API Service Online<br/>
                <small>{API_URL}</small>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="api-status-error">
                ❌ API Service Unavailable<br/>
                <small>{health.get('error', 'Unknown error')}</small><br/>
                <small>{API_URL}</small>
            </div>
            """, unsafe_allow_html=True)
            st.warning("Please ensure the API service is running")

        if st.button("🔄 Refresh Status"):
            st.rerun()

        st.markdown("---")

        st.markdown("""
        **System Overview:**
        - 📚 Data: German Bundestag Speeches (1949-2025)
        - 🔍 Retrieval: Hybrid Search (Semantic + Metadata)
        - 🤖 LLM: Gemini 2.5 Pro
        - 📊 Vector DB: Pinecone

        **Supported Query Types:**
        - Single/Multi-year queries
        - Party position comparison
        - Policy change analysis
        - Speaker viewpoint summary

        **Example Questions:**
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
                f"Example {i}",
                key=f"example_{i}",
                on_click=lambda q=eq: setattr(st.session_state, 'user_input', q)
            ):
                pass

        st.markdown("---")

        if st.button(
            "🗑️ Clear History",
            on_click=lambda: setattr(st.session_state, 'chat_history', [])
        ):
            pass

    # 检查API是否可用
    if not st.session_state.api_healthy:
        st.error(f"""
        ❌ **Unable to connect to API service**

        Please ensure the API service is running:
        ```bash
        python api_server.py
        ```

        Current API URL: `{API_URL}`

        To change the API URL, set the `API_URL` environment variable.
        """)
        return

    # 显示对话历史
    if st.session_state.chat_history:
        st.markdown("## 💬 Conversation History")
        display_chat_history()
    else:
        st.info("👋 Welcome to DE-SMART 1.0! Please enter your question below.")

    # 输入区域
    st.markdown("---")
    st.markdown("## ❓ Enter Your Question")

    col1, col2 = st.columns([4, 1])

    with col1:
        user_input = st.text_area(
            "Supports German and English input:",
            height=100,
            placeholder="e.g.: Welche Positionen vertrat die CDU/CSU zur Flüchtlingspolitik 2015?\nor: What was CDU/CSU's position on refugee policy in 2015?",
            key="user_input"
        )

    with col2:
        # 深度分析模式开关
        deep_mode = st.toggle(
            "🧠 Deep Analysis",
            value=st.session_state.deep_thinking_mode,
            key="deep_mode_toggle",
            help="Enable knowledge graph expansion for more comprehensive retrieval (takes 3-5 minutes)"
        )
        st.session_state.deep_thinking_mode = deep_mode

        if deep_mode:
            st.caption("⏱️ Est. 3-5 min")
        else:
            st.caption("⏱️ Est. 1-2 min")

        submit_button = st.button("🚀 Submit", type="primary")

    if submit_button:
        if user_input.strip():
            process_question(user_input)
            st.rerun()
        else:
            st.warning("Please enter a question")

    # 页脚
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align: center; color: #999; font-size: 0.85rem;">
        © 2025 DE-SMART 1.0 | Powered by LangGraph + Gemini 2.5 Pro + Pinecone<br/>
        <small>API: {API_URL}</small>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
