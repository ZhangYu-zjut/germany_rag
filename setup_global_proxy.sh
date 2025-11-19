#!/bin/bash
# 设置系统级全局代理配置

echo "🔧 设置系统级全局代理"
echo "=============================================="

# 检查是否为root或有sudo权限
if [ "$EUID" -ne 0 ]; then
    echo "⚠️  需要sudo权限来设置系统级配置"
    echo "   将使用sudo执行配置..."
    SUDO_CMD="sudo"
else
    SUDO_CMD=""
fi

PROXY_URL="http://127.0.0.1:7890"
NO_PROXY="localhost,127.0.0.1,::1"

echo "代理地址: $PROXY_URL"
echo ""

# 1. 配置 /etc/environment (系统级环境变量)
echo "1. 配置系统环境变量 (/etc/environment)..."
if [ -f /etc/environment ]; then
    # 备份原文件
    $SUDO_CMD cp /etc/environment /etc/environment.backup.$(date +%Y%m%d_%H%M%S)
    echo "   ✅ 已备份原配置"
fi

# 检查是否已存在代理配置
if grep -q "http_proxy" /etc/environment 2>/dev/null; then
    echo "   ⚠️  发现已有代理配置，将更新..."
    $SUDO_CMD sed -i '/http_proxy/d; /https_proxy/d; /HTTP_PROXY/d; /HTTPS_PROXY/d; /ALL_PROXY/d; /no_proxy/d; /NO_PROXY/d' /etc/environment
fi

# 添加代理配置
$SUDO_CMD tee -a /etc/environment > /dev/null <<EOF

# Global Proxy Settings (Clash)
http_proxy="$PROXY_URL"
https_proxy="$PROXY_URL"
HTTP_PROXY="$PROXY_URL"
HTTPS_PROXY="$PROXY_URL"
ALL_PROXY="$PROXY_URL"
no_proxy="$NO_PROXY"
NO_PROXY="$NO_PROXY"
EOF

echo "   ✅ 系统环境变量已配置"
echo ""

# 2. 配置 /etc/profile.d/ (所有用户shell配置)
echo "2. 配置所有用户的shell代理 (/etc/profile.d/proxy.sh)..."
$SUDO_CMD tee /etc/profile.d/proxy.sh > /dev/null <<'EOF'
# Global Proxy Configuration for all users
# Automatically set proxy if Clash is running

LOCAL_PROXY="http://127.0.0.1:7890"

# Function to check if Clash proxy is available
proxy_available() {
    timeout 1 curl -x ${LOCAL_PROXY} -s http://www.baidu.com > /dev/null 2>&1
}

# Set proxy if available
if proxy_available; then
    export http_proxy="${LOCAL_PROXY}"
    export https_proxy="${LOCAL_PROXY}"
    export ALL_PROXY="${LOCAL_PROXY}"
    export HTTP_PROXY="${LOCAL_PROXY}"
    export HTTPS_PROXY="${LOCAL_PROXY}"
    export no_proxy="localhost,127.0.0.1,::1"
    export NO_PROXY="localhost,127.0.0.1,::1"
fi
EOF

$SUDO_CMD chmod 644 /etc/profile.d/proxy.sh
echo "   ✅ Shell代理配置已创建"
echo ""

# 3. 配置APT代理 (包管理器)
echo "3. 配置APT代理 (/etc/apt/apt.conf.d/95proxies)..."
if [ -d /etc/apt/apt.conf.d ]; then
    $SUDO_CMD tee /etc/apt/apt.conf.d/95proxies > /dev/null <<EOF
Acquire::http::Proxy "$PROXY_URL";
Acquire::https::Proxy "$PROXY_URL";
EOF
    echo "   ✅ APT代理已配置"
else
    echo "   ⚠️  APT目录不存在，跳过"
fi
echo ""

# 4. 配置Git代理
echo "4. 配置Git全局代理..."
git config --global http.proxy "$PROXY_URL" 2>/dev/null && echo "   ✅ Git HTTP代理已配置" || echo "   ⚠️  Git未安装或配置失败"
git config --global https.proxy "$PROXY_URL" 2>/dev/null && echo "   ✅ Git HTTPS代理已配置" || echo "   ⚠️  Git未安装或配置失败"
echo ""

# 5. 应用配置到当前会话
echo "5. 应用配置到当前会话..."
export http_proxy="$PROXY_URL"
export https_proxy="$PROXY_URL"
export ALL_PROXY="$PROXY_URL"
export HTTP_PROXY="$PROXY_URL"
export HTTPS_PROXY="$PROXY_URL"
export no_proxy="$NO_PROXY"
export NO_PROXY="$NO_PROXY"
echo "   ✅ 当前会话代理已设置"
echo ""

# 6. 测试配置
echo "6. 测试代理连接..."
if timeout 3 curl -s ipinfo.io > /dev/null 2>&1; then
    echo "   ✅ 代理连接测试成功"
    curl -s ipinfo.io | grep -E '"ip"|"city"|"country"' | head -3
else
    echo "   ⚠️  代理连接测试失败，请确保Clash正在运行"
fi
echo ""

echo "=============================================="
echo "✅ 全局代理配置完成！"
echo ""
echo "📋 配置说明:"
echo "   - 系统环境变量: /etc/environment"
echo "   - Shell配置: /etc/profile.d/proxy.sh"
echo "   - APT代理: /etc/apt/apt.conf.d/95proxies"
echo "   - Git代理: ~/.gitconfig"
echo ""
echo "🔄 生效方式:"
echo "   - 新开终端: 自动生效"
echo "   - 当前会话: 已生效"
echo "   - 重启系统: 自动生效"
echo ""
echo "💡 提示:"
echo "   - 确保Clash正在运行: ps aux | grep clash"
echo "   - 测试代理: curl ipinfo.io"
echo ""







