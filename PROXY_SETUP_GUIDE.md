# 代理设置指南

## ✅ 当前配置状态

**强制代理模式已启用** - 所有网络请求都会通过代理 `http://127.0.0.1:7890`

## 📋 代理环境变量

```bash
http_proxy=http://127.0.0.1:7890
https_proxy=http://127.0.0.1:7890
ALL_PROXY=http://127.0.0.1:7890
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890
no_proxy=localhost,127.0.0.1,::1  # 本地地址不走代理
```

## 🚀 启动代理服务

### 方法1: Clash for Windows (WSL2环境)

1. **在Windows主机上启动Clash**
   - 打开Clash for Windows
   - 确保"允许局域网连接"已启用
   - 确认端口设置为7890

2. **在WSL2中测试连接**
   ```bash
   curl ipinfo.io
   ```

### 方法2: 其他代理软件

如果您使用其他代理软件（V2Ray、Shadowsocks等），请确保：
- HTTP代理端口设置为 **7890**
- 允许局域网连接（WSL2需要）

## 🔍 验证代理是否工作

```bash
# 方法1: 检查代理状态
check_proxy

# 方法2: 测试网络连接
curl ipinfo.io

# 方法3: 检查代理端口
netstat -tlnp | grep 7890
```

## ⚠️ 常见问题

### 问题1: curl连接被拒绝
**原因**: 代理服务未启动
**解决**: 在Windows上启动Clash或其他代理软件

### 问题2: Claude Code无法连接
**原因**: 代理服务未运行或配置错误
**解决**: 
1. 确认代理服务已启动
2. 运行 `check_proxy` 检查状态
3. 测试 `curl ipinfo.io` 验证网络

### 问题3: 临时禁用代理（仅当前会话）
```bash
unset http_proxy https_proxy ALL_PROXY HTTP_PROXY HTTPS_PROXY
```

### 问题4: 临时启用代理（仅当前会话）
```bash
export http_proxy=http://127.0.0.1:7890
export https_proxy=http://127.0.0.1:7890
export ALL_PROXY=http://127.0.0.1:7890
```

## 📝 配置文件位置

代理设置已保存在：`~/.bashrc` (第119-140行)

## 🎯 使用说明

- **新终端窗口**: 自动应用强制代理设置
- **当前会话**: 已应用强制代理设置
- **Claude Code**: 会自动使用代理设置

## 💡 提示

如果代理服务未运行，所有网络请求会失败。请确保：
1. ✅ Clash或其他代理软件已启动
2. ✅ 允许局域网连接已启用
3. ✅ 端口7890正确配置








