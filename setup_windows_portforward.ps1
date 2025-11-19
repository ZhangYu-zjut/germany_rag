# Windows端口转发设置脚本
# 在Windows PowerShell（管理员模式）运行此脚本

Write-Host "🔧 设置Windows端口转发（WSL2代理）" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

# 检查管理员权限
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "❌ 需要管理员权限！" -ForegroundColor Red
    Write-Host "请右键PowerShell，选择'以管理员身份运行'" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ 管理员权限确认" -ForegroundColor Green
Write-Host ""

# 检查现有端口转发规则
Write-Host "1. 检查现有端口转发规则:" -ForegroundColor Yellow
$existing = netsh interface portproxy show all | Select-String "7890"
if ($existing) {
    Write-Host "   找到现有规则:" -ForegroundColor Yellow
    $existing | ForEach-Object { Write-Host "   $_" }
    Write-Host ""
    Write-Host "   是否删除现有规则并重新创建？(Y/N)" -ForegroundColor Yellow
    $response = Read-Host
    if ($response -eq "Y" -or $response -eq "y") {
        netsh interface portproxy delete v4tov4 listenport=7890 listenaddress=0.0.0.0 2>$null
        Write-Host "   ✅ 已删除现有规则" -ForegroundColor Green
    }
} else {
    Write-Host "   未找到现有规则" -ForegroundColor Green
}
Write-Host ""

# 添加端口转发规则
Write-Host "2. 添加端口转发规则:" -ForegroundColor Yellow
Write-Host "   从 0.0.0.0:7890 → 127.0.0.1:7890" -ForegroundColor White

netsh interface portproxy add v4tov4 listenport=7890 listenaddress=0.0.0.0 connectport=7890 connectaddress=127.0.0.1

if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ 端口转发规则已添加" -ForegroundColor Green
} else {
    Write-Host "   ❌ 添加失败" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 验证规则
Write-Host "3. 验证端口转发规则:" -ForegroundColor Yellow
netsh interface portproxy show all | Select-String "7890" | ForEach-Object { Write-Host "   $_" }
Write-Host ""

# 检查Clash是否运行
Write-Host "4. 检查Clash状态:" -ForegroundColor Yellow
$clashRunning = Get-Process | Where-Object { $_.ProcessName -like "*clash*" }
if ($clashRunning) {
    Write-Host "   ✅ Clash正在运行" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  Clash未运行，请启动Clash" -ForegroundColor Yellow
}
Write-Host ""

# 检查本地端口监听
Write-Host "5. 检查本地端口监听:" -ForegroundColor Yellow
$listening = netstat -an | Select-String "127.0.0.1:7890.*LISTENING"
if ($listening) {
    Write-Host "   ✅ Clash监听在127.0.0.1:7890" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  未检测到Clash监听，请确认Clash已启动" -ForegroundColor Yellow
}
Write-Host ""

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "✅ 端口转发设置完成！" -ForegroundColor Green
Write-Host ""
Write-Host "📋 下一步操作:" -ForegroundColor Cyan
Write-Host "1. 确认Clash已启动并正常运行" -ForegroundColor White
Write-Host "2. 在WSL2中运行:" -ForegroundColor White
Write-Host "   bash diagnose_proxy.sh" -ForegroundColor Yellow
Write-Host "3. 或直接测试:" -ForegroundColor White
Write-Host "   curl ipinfo.io" -ForegroundColor Yellow
Write-Host ""
Write-Host "💡 提示: 此端口转发规则会持久保存，重启后仍然有效" -ForegroundColor Cyan
Write-Host "   删除规则: netsh interface portproxy delete v4tov4 listenport=7890 listenaddress=0.0.0.0" -ForegroundColor Gray







