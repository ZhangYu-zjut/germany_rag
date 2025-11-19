# PowerShell 启动脚本
# 设置环境变量并运行 Python 脚本

# 设置环境变量（使用正斜杠）
$env:GOOGLE_APPLICATION_CREDENTIALS = "f:/vscode_project/tj_germany/heroic-cedar-476803-e1-fe50591663ce.json"

Write-Host "✅ 环境变量已设置" -ForegroundColor Green
Write-Host "   GOOGLE_APPLICATION_CREDENTIALS = $env:GOOGLE_APPLICATION_CREDENTIALS" -ForegroundColor Cyan

# 验证文件存在
if (Test-Path $env:GOOGLE_APPLICATION_CREDENTIALS) {
    Write-Host "✅ 凭证文件存在" -ForegroundColor Green
} else {
    Write-Host "❌ 凭证文件不存在: $env:GOOGLE_APPLICATION_CREDENTIALS" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=" * 80
Write-Host "现在可以运行以下命令:" -ForegroundColor Yellow
Write-Host "=" * 80
Write-Host ""
Write-Host "1. 测试连接:" -ForegroundColor Cyan
Write-Host "   python test_vertex_embedding.py"
Write-Host ""
Write-Host "2. 构建索引:" -ForegroundColor Cyan
Write-Host "   python build_index_vertex.py"
Write-Host ""
Write-Host "3. 运行系统:" -ForegroundColor Cyan
Write-Host "   python main.py"
Write-Host ""
