#!/bin/bash

# 德国议会RAG系统 - Streamlit UI启动脚本

echo "🏛️ 德国议会RAG系统 - Streamlit UI"
echo "=================================="
echo

# 设置代理环境变量
echo "📡 设置代理环境变量..."
export http_proxy="http://127.0.0.1:7890"
export https_proxy="http://127.0.0.1:7890" 
export ALL_PROXY="http://127.0.0.1:7890"
echo "✅ 代理设置完成: $http_proxy"

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate
echo "✅ 虚拟环境已激活"

# 检查环境变量
echo "🔍 检查环境配置..."
if [ -z "$COHERE_API_KEY" ]; then
    echo "⚠️  警告: COHERE_API_KEY 未设置，重排功能将使用降级模式"
else
    echo "✅ COHERE_API_KEY 已设置"
fi

if [ -z "$GEMINI_API_KEY" ] && [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ 错误: 未设置 GEMINI_API_KEY 或 OPENAI_API_KEY"
    echo "   请在 .env 文件中配置API密钥"
    exit 1
else
    echo "✅ LLM API密钥已配置"
fi

echo
echo "🚀 启动Streamlit UI界面..."
echo "📍 访问地址: http://localhost:8501"
echo "⏹️  停止服务: 按 Ctrl+C"
echo

# 启动streamlit
streamlit run streamlit_app.py --server.headless true --server.fileWatcherType none
