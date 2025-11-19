#!/bin/bash
# WSL2代理转发设置脚本
# 即使Clash的Allow LAN有问题，也能通过此方法使用代理

echo "🔧 设置WSL2代理转发"
echo "=============================================="

# 获取Windows主机IP
WINDOWS_HOST=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}')
if [ -z "$WINDOWS_HOST" ]; then
    echo "❌ 无法获取Windows主机IP"
    exit 1
fi

echo "Windows主机IP: $WINDOWS_HOST"
echo ""

# 检查socat是否安装
if ! command -v socat &> /dev/null; then
    echo "📦 安装socat..."
    sudo apt-get update -qq > /dev/null 2>&1
    sudo apt-get install -y socat > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "❌ socat安装失败"
        exit 1
    fi
    echo "✅ socat安装完成"
fi

# 检查7890端口是否被占用
if lsof -Pi :7890 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  端口7890已被占用，尝试停止现有进程..."
    pkill -f "socat.*7890" 2>/dev/null
    sleep 1
fi

# 启动socat转发
echo "🚀 启动端口转发..."
echo "   从 WSL2:7890 → Windows $WINDOWS_HOST:7890"

# 在后台启动socat
nohup socat TCP-LISTEN:7890,fork,reuseaddr TCP:$WINDOWS_HOST:7890 > /tmp/socat_proxy.log 2>&1 &
SOCAT_PID=$!

sleep 2

# 检查是否启动成功
if ps -p $SOCAT_PID > /dev/null; then
    echo "✅ 端口转发已启动 (PID: $SOCAT_PID)"
    echo ""
    
    # 设置代理环境变量使用本地转发
    export http_proxy="http://127.0.0.1:7890"
    export https_proxy="http://127.0.0.1:7890"
    export ALL_PROXY="http://127.0.0.1:7890"
    export HTTP_PROXY="http://127.0.0.1:7890"
    export HTTPS_PROXY="http://127.0.0.1:7890"
    
    echo "📊 代理环境变量已设置:"
    echo "   http_proxy: $http_proxy"
    echo "   https_proxy: $https_proxy"
    echo ""
    
    # 测试代理
    echo "🧪 测试代理连接..."
    if curl -s --max-time 5 ipinfo.io > /dev/null 2>&1; then
        echo "✅ 代理连接成功！"
        echo ""
        echo "📋 使用说明:"
        echo "   1. 代理已设置为: http://127.0.0.1:7890"
        echo "   2. 转发进程PID: $SOCAT_PID"
        echo "   3. 停止转发: kill $SOCAT_PID"
        echo ""
        echo "🧪 测试实际访问:"
        curl -s --max-time 5 ipinfo.io | head -5
    else
        echo "❌ 代理连接失败"
        echo "   请检查："
        echo "   1. Windows上的Clash是否正常运行"
        echo "   2. Windows防火墙是否允许Clash"
        echo "   3. 查看日志: tail -f /tmp/socat_proxy.log"
        kill $SOCAT_PID 2>/dev/null
        exit 1
    fi
else
    echo "❌ 端口转发启动失败"
    echo "   查看日志: cat /tmp/socat_proxy.log"
    exit 1
fi








