#!/bin/bash
# 德国议会RAG Streamlit应用启动脚本

set -e

echo "========================================"
echo "德国议会RAG智能问答系统 - Streamlit UI"
echo "========================================"

# 检查虚拟环境
if [ -d "venv" ]; then
    echo "[1/4] 激活虚拟环境..."
    source venv/bin/activate
else
    echo "[WARNING] 未找到虚拟环境，使用系统Python"
fi

# 检查环境变量
echo "[2/4] 检查环境变量..."
if [ ! -f ".env" ]; then
    echo "[ERROR] 未找到 .env 文件"
    echo "请复制 .env.example 为 .env 并配置API密钥"
    exit 1
fi

# 加载环境变量
set -a
source .env
set +a

# 检查必需的环境变量
REQUIRED_VARS=("OPENAI_API_KEY" "DEEPINFRA_EMBEDDING_API_KEY" "PINECONE_VECTOR_DATABASE_API_KEY")
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo "[ERROR] 缺少环境变量: $var"
        exit 1
    fi
done
echo "    环境变量检查通过"

# 检查Streamlit是否安装
echo "[3/4] 检查Streamlit..."
if ! command -v streamlit &> /dev/null; then
    echo "    安装Streamlit..."
    pip install streamlit -q
fi
echo "    Streamlit已就绪"

# 启动Streamlit
echo "[4/4] 启动Streamlit应用..."
echo ""
echo "========================================"
echo "访问地址: http://localhost:8501"
echo "按 Ctrl+C 停止服务"
echo "========================================"
echo ""

streamlit run streamlit_app.py \
    --server.port 8501 \
    --server.address 0.0.0.0 \
    "$@"
