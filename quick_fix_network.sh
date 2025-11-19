#!/bin/bash
# 快速修复网络问题

echo "🔧 快速修复网络连接"
echo "=============================================="

WINDOWS_HOST=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}')
echo "Windows主机IP: $WINDOWS_HOST"
echo ""

# 方案1: 临时禁用代理，让基础网络工作
echo "方案1: 临时禁用代理（让网络先工作）"
echo "----------------------------------------"
unset http_proxy https_proxy ALL_PROXY HTTP_PROXY HTTPS_PROXY
echo "✅ 代理已临时禁用"
echo "   当前网络状态: 直接连接（不使用代理）"
echo ""

# 测试基础网络
echo "🧪 测试基础网络连接:"
if timeout 3 curl -s http://www.baidu.com > /dev/null 2>&1; then
    echo "✅ 基础网络正常！"
    echo ""
    echo "📋 当前状态:"
    echo "   - 代理: 已禁用（临时）"
    echo "   - 网络: 正常工作"
    echo ""
    echo "💡 如果要恢复代理，请："
    echo "   1. 确保Windows上Clash正常运行"
    echo "   2. 运行: source ~/.bashrc"
    echo "   3. 测试: curl ipinfo.io"
else
    echo "❌ 基础网络也失败，可能是系统网络问题"
fi

echo ""
echo "=============================================="
echo "🔧 方案2: 尝试修复代理连接"
echo "----------------------------------------"

# 重新设置代理
export http_proxy="http://${WINDOWS_HOST}:7890"
export https_proxy="http://${WINDOWS_HOST}:7890"
export ALL_PROXY="http://${WINDOWS_HOST}:7890"

echo "已重新设置代理: http://${WINDOWS_HOST}:7890"
echo ""

# 测试代理连接
echo "🧪 测试代理连接:"
if timeout 3 curl -s http://www.baidu.com > /dev/null 2>&1; then
    echo "✅ 代理连接成功！"
    echo "   网络已恢复正常"
else
    echo "❌ 代理连接失败"
    echo ""
    echo "⚠️  代理无法使用，但基础网络正常"
    echo "   请在Windows上检查："
    echo "   1. Clash是否正常运行"
    echo "   2. '允许局域网连接'是否启用"
    echo "   3. 日志中是否有 'X [Inbound] start failed' 错误"
    echo ""
    echo "💡 如果着急使用网络，当前已切换到直接连接模式"
fi







