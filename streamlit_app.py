"""
德国议会RAG系统 - Streamlit交互界面
支持完整的端到端测试和结果展示
"""

import streamlit as st
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 🔧 首先加载环境变量 (修复环境变量读取问题)
load_dotenv()

# 🎯 设置Qdrant配置环境变量 (修复Collection not found问题)
os.environ["QDRANT_MODE"] = "local"
os.environ["QDRANT_LOCAL_PATH"] = "./data/qdrant"

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

# 检查和设置代理环境变量
def setup_proxy():
    """设置代理环境变量"""
    proxy_url = "http://127.0.0.1:7890"
    os.environ['http_proxy'] = proxy_url
    os.environ['https_proxy'] = proxy_url
    os.environ['ALL_PROXY'] = proxy_url

def check_environment():
    """检查环境配置"""
    setup_proxy()
    
    issues = []
    
    # 检查API密钥
    cohere_key = os.getenv('COHERE_API_KEY')
    if not cohere_key:
        issues.append("❌ COHERE_API_KEY 未设置")
    
    gemini_key = os.getenv('GEMINI_API_KEY') or os.getenv('OPENAI_API_KEY')
    if not gemini_key:
        issues.append("❌ GEMINI_API_KEY 未设置")
    
    # 检查代理
    proxy = os.getenv('http_proxy')
    if proxy:
        st.sidebar.success(f"✅ 代理设置: {proxy}")
    
    return issues

def main():
    # 页面标题
    st.title("🏛️ 德国联邦议院演讲智能问答系统")
    st.markdown("---")
    
    # 侧边栏：系统状态
    st.sidebar.header("🔧 系统状态")
    
    # 环境检查
    issues = check_environment()
    if issues:
        st.sidebar.error("⚠️ 配置问题:")
        for issue in issues:
            st.sidebar.write(issue)
        st.sidebar.markdown("请检查 `.env` 文件配置")
    else:
        st.sidebar.success("✅ 环境配置正常")
    
    # 侧边栏：数据范围信息
    st.sidebar.header("📊 数据范围")
    st.sidebar.info("""
    **时间范围**: 2018-2020年
    
    **党派覆盖**:
    - CDU/CSU (联盟党)
    - SPD (社会民主党) 
    - FDP (自由民主党)
    - BÜNDNIS 90/DIE GRÜNEN (绿党)
    - DIE LINKE (左翼党)
    - AfD (德国选择党)
    
    **数据来源**: 德国联邦议院官方演讲记录
    """)
    
    # 主界面：问题输入区域
    st.header("💬 智能问答")
    
    # 预设问题选择
    st.subheader("📋 预设问题示例")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🔍 事实查询类**")
        example_questions_facts = [
            "2019年德国议会讨论了哪些主要议题？",
            "2020年3月Merkel在气候政策上说了什么？",
            "2018年绿党在能源政策方面的主要观点？"
        ]
        
        st.markdown("**📊 总结类**")
        example_questions_summary = [
            "请总结2019年绿党在气候保护方面的主要主张",
            "总结2018-2020年期间难民政策的主要讨论",
            "CDU/CSU在数字化转型方面的核心政策"
        ]
    
    with col2:
        st.markdown("**🔄 变化类**")
        example_questions_change = [
            "2018-2020年期间CDU对数字化政策的立场有何变化？",
            "德国议会对气候政策的态度如何演变？",
            "AfD在移民问题上的立场变化"
        ]
        
        st.markdown("**⚖️ 对比类**")
        example_questions_compare = [
            "对比CDU和SPD在2019年数字化政策上的差异",
            "不同党派在气候保护方面的立场有何不同？",
            "绿党和FDP在能源政策上的分歧"
        ]
    
    # 问题输入
    st.subheader("✍️ 输入您的问题")
    
    # 快速选择按钮
    st.markdown("**快速选择示例问题：**")
    quick_questions = [
        "2019年德国议会讨论了哪些主要议题？",
        "请总结2019年绿党在气候保护方面的主要主张",
        "2018-2020年期间CDU对数字化政策的立场有何变化？",
        "对比CDU和SPD在2019年数字化政策上的差异"
    ]
    
    selected_question = st.selectbox("选择示例问题", ["请选择..."] + quick_questions)
    
    # 问题输入框
    if selected_question != "请选择...":
        user_question = st.text_area("问题内容", value=selected_question, height=100)
    else:
        user_question = st.text_area("问题内容", placeholder="例如：2019年德国议会讨论了哪些主要议题？", height=100)
    
    # 高级选项
    with st.expander("🔧 高级选项"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            enable_rerank = st.checkbox("启用重排 (Cohere)", value=True, help="使用Cohere API进行文档重排")
            
        with col2:
            top_k = st.slider("检索文档数", min_value=5, max_value=20, value=10, help="从向量数据库检索的文档数量")
            
        with col3:
            show_debug = st.checkbox("显示调试信息", value=False, help="显示详细的处理过程")
    
    # 提交按钮
    if st.button("🚀 开始问答", type="primary", disabled=not user_question.strip()):
        with st.spinner("🔄 正在处理您的问题，请稍候..."):
            try:
                # 导入RAG系统
                from src.graph.workflow import QuestionAnswerWorkflow
                
                if show_debug:
                    st.info("🔄 正在初始化RAG工作流...")
                
                # 初始化工作流
                workflow = QuestionAnswerWorkflow()
                
                if show_debug:
                    st.info("🔄 正在运行完整RAG流程...")
                
                # 运行工作流
                result = workflow.run(user_question, verbose=show_debug)
                
                # 显示结果
                st.success("✅ 处理完成！")
                
                # 结果展示区域
                st.header("📄 回答结果")
                
                if result.get('final_answer'):
                    # 显示最终答案
                    st.subheader("💡 生成的答案")
                    st.markdown(result['final_answer'])
                    
                    # 显示处理信息
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        intent = result.get('intent', '未知')
                        st.metric("意图识别", intent)
                    
                    with col2:
                        question_type = result.get('question_type', '未知')
                        st.metric("问题类型", question_type)
                    
                    with col3:
                        answer_length = len(result['final_answer'])
                        st.metric("答案长度", f"{answer_length} 字符")
                    
                    # 检索和重排信息
                    if show_debug:
                        st.subheader("🔍 处理详情")
                        
                        # 检索结果
                        retrieval_results = result.get('retrieval_results', [])
                        if retrieval_results:
                            total_retrieved = sum(len(item.get('chunks', [])) for item in retrieval_results)
                            st.write(f"📊 检索到 {total_retrieved} 个相关文档")
                        
                        # 重排结果
                        reranked_results = result.get('reranked_results', [])
                        if reranked_results and enable_rerank:
                            first_rerank = reranked_results[0]
                            rerank_chunks = len(first_rerank.get('chunks', []))
                            
                            has_rerank_scores = any(chunk.get('rerank_score') is not None 
                                                   for chunk in first_rerank.get('chunks', []))
                            
                            if has_rerank_scores:
                                st.write(f"🔄 重排成功: 处理了 {rerank_chunks} 个文档")
                                
                                # 显示重排分数
                                with st.expander("查看重排详情"):
                                    for i, chunk in enumerate(first_rerank.get('chunks', [])[:3]):
                                        rerank_score = chunk.get('rerank_score', 0)
                                        original_score = chunk.get('score', 0)
                                        text_preview = chunk['text'][:100] + '...'
                                        
                                        st.write(f"**文档 {i+1}**")
                                        st.write(f"- 重排分数: {rerank_score:.4f}")
                                        st.write(f"- 原始分数: {original_score:.3f}")
                                        st.write(f"- 内容预览: {text_preview}")
                                        st.write("---")
                            else:
                                st.write("⚠️ 重排API失败，使用降级处理")
                                if first_rerank.get('rerank_error'):
                                    st.write(f"错误信息: {first_rerank['rerank_error']}")
                    
                else:
                    st.error("❌ 未能生成答案")
                    if result.get('error'):
                        st.error(f"错误信息: {result['error']}")
                        
            except Exception as e:
                st.error(f"❌ 处理过程中出现错误: {str(e)}")
                
                if show_debug:
                    st.exception(e)
    
    # 页面底部信息
    st.markdown("---")
    st.markdown("""
    ### 💡 使用提示
    
    1. **选择合适的问题类型**：系统对不同类型的问题有不同的处理策略
    2. **时间范围**：请确保问题涉及的时间在2018-2020年范围内
    3. **具体性**：越具体的问题，通常能得到越准确的答案
    4. **党派名称**：支持中文和德文党派名称
    
    ### 🔧 系统架构
    - **检索**: BGE-M3本地模型 + Milvus向量数据库
    - **重排**: Cohere API智能重排 + 降级处理
    - **生成**: Gemini 2.5 Pro答案生成
    """)

if __name__ == "__main__":
    main()
