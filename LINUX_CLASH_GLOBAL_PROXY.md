# Linux Clash 全局代理配置指南

## ✅ 当前状态

- ✅ Linux Clash 已运行 (`./cfw`)
- ✅ 端口7890已监听
- ✅ 全局代理模式已启用
- ✅ 代理地址: `http://127.0.0.1:7890`

## 🎯 快速使用

### 启动Clash

```bash
cd ~/Clash\ for\ Windows-0.20.39-x64-linux
./cfw
```

### 检查代理状态

```bash
check_proxy
```

### 手动启用/禁用代理

```bash
# 启用全局代理
enable_proxy

# 禁用代理（直接连接）
disable_proxy
```

### 测试代理连接

```bash
# 测试IP地址（应该显示代理服务器IP）
curl ipinfo.io

# 测试网络连接
curl http://www.google.com
```

## 📋 配置说明

### 代理环境变量

全局代理模式下，以下环境变量已自动设置：

```bash
http_proxy=http://127.0.0.1:7890
https_proxy=http://127.0.0.1:7890
ALL_PROXY=http://127.0.0.1:7890
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890
no_proxy=localhost,127.0.0.1,::1
```

### 自动配置

`.bashrc`已配置为：
- ✅ 启动时自动检测Clash并启用代理
- ✅ 如果Clash不可用，自动切换到直接连接模式
- ✅ 提供便捷函数：`check_proxy`, `enable_proxy`, `disable_proxy`

## 🔧 常见操作

### 新开终端自动启用代理

配置已在`.bashrc`中，新开终端会自动：
1. 检测本地Clash是否可用
2. 如果可用，自动启用全局代理
3. 如果不可用，使用直接连接模式

### 检查Clash是否运行

```bash
# 检查进程
ps aux | grep clash

# 检查端口监听
netstat -tlnp | grep 7890
# 或
ss -tlnp | grep 7890
```

### 重启代理

```bash
# 如果代理不可用，重新启用
enable_proxy
```

## 🚨 故障排查

### 问题1: 代理不可用

**症状**: `check_proxy`显示代理不可用

**解决**:
1. 确认Clash正在运行: `ps aux | grep clash`
2. 如果未运行，启动: `./cfw`
3. 等待几秒后运行: `enable_proxy`

### 问题2: 代理设置丢失

**症状**: 新开终端后代理未启用

**解决**:
- 运行 `enable_proxy` 手动启用
- 或检查Clash是否正常运行

### 问题3: 需要临时禁用代理

**解决**:
```bash
disable_proxy
```

## 📊 验证代理是否生效

### 方法1: 检查IP地址

```bash
curl ipinfo.io
```

如果显示代理服务器的IP（非你的真实IP），说明代理生效。

### 方法2: 检查环境变量

```bash
echo $http_proxy
# 应该显示: http://127.0.0.1:7890
```

### 方法3: 使用check_proxy函数

```bash
check_proxy
```

## 💡 提示

1. **Clash必须运行**: 全局代理需要Clash进程运行
2. **自动检测**: 配置会自动检测Clash是否可用
3. **fallback机制**: 如果Clash不可用，自动切换到直接连接
4. **便捷函数**: 使用`check_proxy`、`enable_proxy`、`disable_proxy`管理代理

## 🎯 当前配置总结

| 项目 | 状态 | 说明 |
|------|------|------|
| Clash进程 | ✅ 运行中 | 进程ID: 4794 |
| 端口监听 | ✅ 已监听 | *:7890 |
| 代理地址 | ✅ 已设置 | http://127.0.0.1:7890 |
| 全局模式 | ✅ 已启用 | 所有流量通过代理 |
| 自动配置 | ✅ 已配置 | .bashrc自动检测 |

---

**配置完成！** 全局代理模式已启用，所有网络流量将通过本地Clash代理。







