# WSL2 代理配置完整指南

## 🔍 问题诊断

**当前状态**: Windows上的Clash已启动，但WSL2无法连接

**原因**: Clash默认只监听 `127.0.0.1`，WSL2需要访问Windows主机的局域网IP

## 🛠️ 解决方案

### 步骤1: 在Windows上配置Clash允许局域网连接

1. **打开Clash for Windows**
2. **进入设置 (Settings)**
3. **找到 "Allow LAN" 或 "允许局域网连接"**
4. **启用此选项** ✅
5. **确认端口设置**:
   - HTTP端口: `7890`
   - SOCKS5端口: `7891` (可选)

### 步骤2: 检查Windows防火墙

如果还是无法连接，可能需要：

1. **打开Windows防火墙设置**
2. **允许Clash通过防火墙**
   - 设置 → 隐私和安全性 → Windows安全中心 → 防火墙和网络保护
   - 允许应用通过防火墙 → 找到Clash → 确保"专用"和"公用"都已勾选

### 步骤3: 获取Windows主机IP并更新配置

WSL2会自动获取Windows主机IP，通常存储在 `/etc/resolv.conf` 中。

**自动获取脚本**:
```bash
# 获取Windows主机IP
WINDOWS_HOST=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}')
echo "Windows主机IP: $WINDOWS_HOST"
```

## 🔧 更新WSL2代理配置

### 方法1: 自动检测Windows主机IP（推荐）

修改 `~/.bashrc`，使用动态获取的Windows主机IP：

```bash
# 获取Windows主机IP（WSL2）
WINDOWS_HOST=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}')

# Set proxy for cfw (强制使用代理 - 用于Claude Code)
export http_proxy="http://${WINDOWS_HOST}:7890"
export https_proxy="http://${WINDOWS_HOST}:7890"
export ALL_PROXY="http://${WINDOWS_HOST}:7890"
export HTTP_PROXY="http://${WINDOWS_HOST}:7890"
export HTTPS_PROXY="http://${WINDOWS_HOST}:7890"
export no_proxy="localhost,127.0.0.1,::1"
```

### 方法2: 手动设置（如果IP固定）

如果您的Windows主机IP固定为 `172.18.176.1`：

```bash
export http_proxy="http://172.18.176.1:7890"
export https_proxy="http://172.18.176.1:7890"
export ALL_PROXY="http://172.18.176.1:7890"
```

## ✅ 验证配置

配置完成后，运行以下命令验证：

```bash
# 1. 检查Windows主机IP
cat /etc/resolv.conf | grep nameserver

# 2. 测试代理连接
WINDOWS_HOST=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}')
curl -x http://${WINDOWS_HOST}:7890 ipinfo.io

# 3. 检查代理状态
check_proxy
```

## 🚨 常见问题

### Q1: 为什么使用127.0.0.1不行？

**A**: WSL2中的 `127.0.0.1` 指向WSL2虚拟机内部，不是Windows主机。必须使用Windows主机的实际IP地址。

### Q2: Windows主机IP会变化吗？

**A**: 可能会变化（每次重启WSL2可能不同）。建议使用方法1（自动检测）。

### Q3: 如何确认Clash已启用"允许局域网连接"？

**A**: 
- 在Clash界面查看"Allow LAN"状态
- 或者检查Clash日志，应该显示监听 `0.0.0.0:7890` 而不是 `127.0.0.1:7890`

### Q4: 所有端口都不可达怎么办？

**A**: 
1. 确认Clash的"Allow LAN"已启用
2. 检查Windows防火墙设置
3. 尝试重启Clash
4. 检查Clash日志查看是否有错误

## 📝 快速修复命令

```bash
# 1. 获取Windows主机IP
WINDOWS_HOST=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}')

# 2. 设置代理（当前会话）
export http_proxy="http://${WINDOWS_HOST}:7890"
export https_proxy="http://${WINDOWS_HOST}:7890"
export ALL_PROXY="http://${WINDOWS_HOST}:7890"

# 3. 测试连接
curl ipinfo.io
```

## 🎯 下一步

1. ✅ 在Windows上启用Clash的"允许局域网连接"
2. ✅ 更新 `~/.bashrc` 使用Windows主机IP
3. ✅ 重新加载配置或打开新终端
4. ✅ 运行 `check_proxy` 验证








