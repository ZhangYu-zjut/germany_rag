# Docker Desktop 安装指南

## 🚀 最简单的方法

### 方法一：官网直接下载（推荐）

1. **访问官网**：https://www.docker.com/products/docker-desktop/
2. **点击下载** "Docker Desktop for Windows"
3. **运行安装程序** `Docker Desktop Installer.exe`
4. **勾选选项**：
   - ✅ Use WSL 2 instead of Hyper-V
   - ✅ Add shortcut to desktop
5. **等待安装完成** 并重启
6. **启动 Docker Desktop** 从开始菜单

---

### 方法二：使用自动安装脚本

在 **PowerShell（管理员）** 中运行：

```powershell
# 右键点击 PowerShell，选择"以管理员身份运行"
.\install_docker.ps1
```

该脚本会自动：
- ✅ 检查系统要求
- ✅ 启用 WSL 2
- ✅ 下载 Docker Desktop
- ✅ 自动安装

---

## 📋 详细步骤（手动安装）

### 步骤 1：启用 WSL 2

在 **PowerShell（管理员）** 中运行：

```powershell
# 1. 启用 WSL
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart

# 2. 启用虚拟机平台
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

# 3. 重启电脑
Restart-Computer
```

### 步骤 2：下载 WSL 2 更新包

重启后，访问并下载：
**https://aka.ms/wsl2kernel**

双击安装下载的文件。

### 步骤 3：设置 WSL 2 为默认

```powershell
wsl --set-default-version 2
```

### 步骤 4：下载并安装 Docker Desktop

1. 访问：**https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe**
2. 下载完成后双击安装
3. 安装过程中保持默认选项
4. 安装完成后重启

### 步骤 5：启动 Docker Desktop

1. 从开始菜单打开 "Docker Desktop"
2. 接受服务条款
3. 等待 Docker Engine 启动（任务栏图标变绿）

---

## ✅ 验证安装

安装完成后，在 PowerShell 中运行：

```powershell
# 1. 检查版本
docker --version

# 应该显示类似：
# Docker version 24.0.7, build afdd53b

# 2. 检查运行状态
docker info

# 3. 运行测试容器
docker run hello-world

# 应该显示：
# Hello from Docker!
# This message shows that your installation appears to be working correctly.
```

如果都成功，说明 Docker 安装完成！

---

## 🔧 常见问题

### Q1: WSL 2 安装失败

**错误**: "The WSL 2 Linux kernel is now installed using a separate MSI update package"

**解决**:
1. 下载：https://aka.ms/wsl2kernel
2. 安装下载的更新包
3. 重启 Docker Desktop

---

### Q2: Docker Desktop 启动失败

**错误**: "Docker Desktop failed to start"

**解决**:
1. 确保已启用虚拟化（在 BIOS 中）
2. 运行：
   ```powershell
   # 检查虚拟化是否启用
   Get-ComputerInfo | Select-Object -Property HyperVisorPresent, HyperVRequirementVirtualizationFirmwareEnabled
   
   # 如果返回 True，说明已启用
   ```
3. 如果未启用，需要进入 BIOS 启用 "Virtualization Technology" 或 "VT-x"

---

### Q3: 需要管理员权限

**错误**: "Docker Desktop requires elevated privileges"

**解决**:
- 右键点击 Docker Desktop 图标
- 选择 "以管理员身份运行"

---

## 🎯 安装后配置

### 1. 配置资源分配

打开 Docker Desktop → Settings → Resources → Advanced：

- **CPU**: 建议分配 2-4 个核心
- **Memory**: 建议分配 4-8 GB
- **Disk**: 根据需要调整

### 2. 启用自动启动

Settings → General：
- ✅ 勾选 "Start Docker Desktop when you log in"

### 3. 配置镜像加速（可选，中国用户推荐）

Settings → Docker Engine，添加：

```json
{
  "registry-mirrors": [
    "https://mirror.ccs.tencentyun.com",
    "https://docker.mirrors.ustc.edu.cn"
  ]
}
```

点击 "Apply & Restart"

---

## 📦 Windows 版本要求

| Windows 版本 | 最低 Build | 是否支持 |
|-------------|-----------|---------|
| Windows 11 Home | 22000+ | ✅ |
| Windows 11 Pro | 22000+ | ✅ |
| Windows 10 Home | 19044+ | ✅ |
| Windows 10 Pro | 19041+ | ✅ |
| Windows 10 Enterprise | 19041+ | ✅ |
| 更低版本 | - | ❌ |

**查看您的版本**：
```powershell
winver
```

---

## 🚀 安装完成后的操作

### 启动 Milvus

```powershell
# 1. 确保 Docker Desktop 正在运行
# 2. 运行启动脚本
.\start_milvus.ps1
```

### 运行索引构建

```powershell
python build_index.py
```

---

## 📞 获取帮助

如果遇到问题：

1. **Docker 官方文档**: https://docs.docker.com/desktop/windows/
2. **WSL 2 文档**: https://docs.microsoft.com/zh-cn/windows/wsl/
3. **查看日志**: Docker Desktop → Troubleshoot → View logs

---

## 📝 总结

**推荐流程**：

1. ✅ 下载 Docker Desktop：https://www.docker.com/products/docker-desktop/
2. ✅ 安装并重启
3. ✅ 启动 Docker Desktop
4. ✅ 验证：`docker run hello-world`
5. ✅ 运行：`.\start_milvus.ps1`

**预计时间**: 15-30 分钟（包括下载）

祝您安装顺利！🎉
