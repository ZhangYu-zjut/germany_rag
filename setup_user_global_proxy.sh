#!/bin/bash
# 设置用户级全局代理配置（不需要sudo）

echo "🔧 设置用户级全局代理"
echo "=============================================="

PROXY_URL="http://127.0.0.1:7890"
NO_PROXY="localhost,127.0.0.1,::1"

echo "代理地址: $PROXY_URL"
echo ""

# 1. 更新 ~/.bashrc
echo "1. 更新 ~/.bashrc..."
if ! grep -q "# Global Proxy Settings" ~/.bashrc; then
    cat >> ~/.bashrc <<EOF

# Global Proxy Settings (Clash) - Auto-enabled
LOCAL_PROXY="http://127.0.0.1:7890"
export http_proxy="\${LOCAL_PROXY}"
export https_proxy="\${LOCAL_PROXY}"
export ALL_PROXY="\${LOCAL_PROXY}"
export HTTP_PROXY="\${LOCAL_PROXY}"
export HTTPS_PROXY="\${LOCAL_PROXY}"
export no_proxy="${NO_PROXY}"
export NO_PROXY="${NO_PROXY}"
EOF
    echo "   ✅ ~/.bashrc已更新"
else
    echo "   ⚠️  ~/.bashrc中已有代理配置"
fi
echo ""

# 2. 配置 ~/.profile (适用于所有shell)
echo "2. 配置 ~/.profile..."
if ! grep -q "# Global Proxy Settings" ~/.profile 2>/dev/null; then
    cat >> ~/.profile <<EOF

# Global Proxy Settings (Clash)
LOCAL_PROXY="http://127.0.0.1:7890"
export http_proxy="\${LOCAL_PROXY}"
export https_proxy="\${LOCAL_PROXY}"
export ALL_PROXY="\${LOCAL_PROXY}"
export HTTP_PROXY="\${LOCAL_PROXY}"
export HTTPS_PROXY="\${LOCAL_PROXY}"
export no_proxy="${NO_PROXY}"
export NO_PROXY="${NO_PROXY}"
EOF
    echo "   ✅ ~/.profile已更新"
else
    echo "   ⚠️  ~/.profile中已有代理配置"
fi
echo ""

# 3. 配置 ~/.bash_profile (如果存在)
if [ -f ~/.bash_profile ]; then
    echo "3. 配置 ~/.bash_profile..."
    if ! grep -q "# Global Proxy Settings" ~/.bash_profile; then
        cat >> ~/.bash_profile <<EOF

# Global Proxy Settings (Clash)
LOCAL_PROXY="http://127.0.0.1:7890"
export http_proxy="\${LOCAL_PROXY}"
export https_proxy="\${LOCAL_PROXY}"
export ALL_PROXY="\${LOCAL_PROXY}"
export HTTP_PROXY="\${LOCAL_PROXY}"
export HTTPS_PROXY="\${LOCAL_PROXY}"
export no_proxy="${NO_PROXY}"
export NO_PROXY="${NO_PROXY}"
EOF
        echo "   ✅ ~/.bash_profile已更新"
    else
        echo "   ⚠️  ~/.bash_profile中已有代理配置"
    fi
fi
echo ""

# 4. 配置Git代理（已配置，但确认一下）
echo "4. 确认Git代理配置..."
git config --global http.proxy "$PROXY_URL" 2>/dev/null
git config --global https.proxy "$PROXY_URL" 2>/dev/null
echo "   ✅ Git代理已配置"
echo ""

# 5. 配置npm代理（如果安装了npm）
if command -v npm &> /dev/null; then
    echo "5. 配置npm代理..."
    npm config set proxy "$PROXY_URL" 2>/dev/null
    npm config set https-proxy "$PROXY_URL" 2>/dev/null
    echo "   ✅ npm代理已配置"
else
    echo "5. npm未安装，跳过"
fi
echo ""

# 6. 配置pip代理（如果安装了pip）
if command -v pip &> /dev/null; then
    echo "6. 配置pip代理..."
    mkdir -p ~/.pip
    cat > ~/.pip/pip.conf <<EOF
[global]
proxy = $PROXY_URL
EOF
    echo "   ✅ pip代理已配置 (~/.pip/pip.conf)"
else
    echo "6. pip未安装，跳过"
fi
echo ""

# 7. 应用配置到当前会话
echo "7. 应用配置到当前会话..."
export http_proxy="$PROXY_URL"
export https_proxy="$PROXY_URL"
export ALL_PROXY="$PROXY_URL"
export HTTP_PROXY="$PROXY_URL"
export HTTPS_PROXY="$PROXY_URL"
export no_proxy="$NO_PROXY"
export NO_PROXY="$NO_PROXY"
echo "   ✅ 当前会话代理已设置"
echo ""

# 8. 测试配置
echo "8. 测试代理连接..."
if timeout 3 curl -s ipinfo.io > /dev/null 2>&1; then
    echo "   ✅ 代理连接测试成功"
    curl -s ipinfo.io | grep -E '"ip"|"city"|"country"' | head -3
else
    echo "   ⚠️  代理连接测试失败，请确保Clash正在运行"
fi
echo ""

echo "=============================================="
echo "✅ 用户级全局代理配置完成！"
echo ""
echo "📋 已配置的项目:"
echo "   ✅ ~/.bashrc (Bash shell)"
echo "   ✅ ~/.profile (所有shell)"
echo "   ✅ ~/.bash_profile (如果存在)"
echo "   ✅ Git全局代理"
if command -v npm &> /dev/null; then
    echo "   ✅ npm代理"
fi
if command -v pip &> /dev/null; then
    echo "   ✅ pip代理 (~/.pip/pip.conf)"
fi
echo ""
echo "🔄 生效方式:"
echo "   - 新开终端: 自动生效"
echo "   - 当前会话: 已生效"
echo "   - 重新登录: 自动生效"
echo ""
echo "💡 提示:"
echo "   - 确保Clash正在运行: ps aux | grep clash"
echo "   - 测试代理: curl ipinfo.io"
echo "   - 如需系统级配置，运行: sudo bash setup_global_proxy.sh"
echo ""







