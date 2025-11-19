# Docker Desktop 自动安装脚本
# 需要管理员权限运行

param(
    [switch]$SkipWSL
)

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Docker Desktop 安装向导" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查管理员权限
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "❌ 此脚本需要管理员权限" -ForegroundColor Red
    Write-Host ""
    Write-Host "请右键点击 PowerShell，选择 '以管理员身份运行'，然后重新执行此脚本" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

Write-Host "✅ 管理员权限确认" -ForegroundColor Green

# 检查 Windows 版本
Write-Host ""
Write-Host "[1] 检查系统要求..." -ForegroundColor Yellow

$osInfo = Get-CimInstance Win32_OperatingSystem
$osBuild = [int]$osInfo.BuildNumber
$osVersion = $osInfo.Caption

Write-Host "   系统: $osVersion" -ForegroundColor White
Write-Host "   版本号: $osBuild" -ForegroundColor White

if ($osBuild -lt 19041) {
    Write-Host ""
    Write-Host "❌ 您的 Windows 版本过低" -ForegroundColor Red
    Write-Host "   需要 Windows 10 Build 19041 或更高" -ForegroundColor Yellow
    Write-Host "   请先更新 Windows" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ 系统版本符合要求" -ForegroundColor Green

# 检查 WSL 2
Write-Host ""
Write-Host "[2] 检查 WSL 2..." -ForegroundColor Yellow

$wslInstalled = Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux

if ($wslInstalled.State -ne "Enabled" -and -not $SkipWSL) {
    Write-Host "   WSL 未启用，正在启用..." -ForegroundColor Yellow
    
    Write-Host "   [2.1] 启用 WSL..." -ForegroundColor Cyan
    dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
    
    Write-Host "   [2.2] 启用虚拟机平台..." -ForegroundColor Cyan
    dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
    
    Write-Host ""
    Write-Host "⚠️  需要重启计算机才能继续" -ForegroundColor Yellow
    Write-Host ""
    $restart = Read-Host "是否现在重启？(y/n)"
    
    if ($restart -eq 'y' -or $restart -eq 'Y') {
        Write-Host "正在重启..." -ForegroundColor Cyan
        Restart-Computer
    } else {
        Write-Host ""
        Write-Host "请手动重启后，重新运行此脚本" -ForegroundColor Yellow
        exit 0
    }
} else {
    Write-Host "✅ WSL 已启用" -ForegroundColor Green
}

# 下载 Docker Desktop
Write-Host ""
Write-Host "[3] 下载 Docker Desktop..." -ForegroundColor Yellow

$dockerUrl = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
$installerPath = "$env:TEMP\DockerDesktopInstaller.exe"

Write-Host "   下载地址: $dockerUrl" -ForegroundColor White
Write-Host "   保存位置: $installerPath" -ForegroundColor White
Write-Host ""

try {
    Write-Host "   正在下载... (约 500MB，请耐心等待)" -ForegroundColor Cyan
    
    # 使用 BITS 下载（支持断点续传）
    Start-BitsTransfer -Source $dockerUrl -Destination $installerPath -DisplayName "Docker Desktop"
    
    Write-Host "✅ 下载完成" -ForegroundColor Green
} catch {
    Write-Host "❌ 下载失败: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "请手动下载安装程序:" -ForegroundColor Yellow
    Write-Host "  $dockerUrl" -ForegroundColor White
    exit 1
}

# 安装 Docker Desktop
Write-Host ""
Write-Host "[4] 安装 Docker Desktop..." -ForegroundColor Yellow
Write-Host "   这可能需要几分钟..." -ForegroundColor White
Write-Host ""

try {
    Start-Process -FilePath $installerPath -ArgumentList "install", "--quiet", "--accept-license" -Wait
    
    Write-Host "✅ 安装完成" -ForegroundColor Green
} catch {
    Write-Host "❌ 安装失败: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "请手动运行安装程序:" -ForegroundColor Yellow
    Write-Host "  $installerPath" -ForegroundColor White
    exit 1
}

# 清理安装文件
Write-Host ""
Write-Host "[5] 清理临时文件..." -ForegroundColor Yellow
Remove-Item $installerPath -Force
Write-Host "✅ 清理完成" -ForegroundColor Green

# 完成
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ✅ Docker Desktop 安装完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "下一步操作:" -ForegroundColor Yellow
Write-Host "  1. 从开始菜单启动 'Docker Desktop'" -ForegroundColor White
Write-Host "  2. 等待 Docker Engine 启动（图标变绿）" -ForegroundColor White
Write-Host "  3. 运行: .\start_milvus.ps1" -ForegroundColor White
Write-Host ""
Write-Host "验证安装:" -ForegroundColor Yellow
Write-Host "  docker --version" -ForegroundColor White
Write-Host "  docker run hello-world" -ForegroundColor White
Write-Host ""
