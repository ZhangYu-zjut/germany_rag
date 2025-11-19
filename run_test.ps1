# 一键运行测试脚本
# 在同一会话中设置环境变量并立即运行测试

# 设置环境变量（使用正斜杠避免转义问题）
$env:GOOGLE_APPLICATION_CREDENTIALS = "f:/vscode_project/tj_germany/heroic-cedar-476803-e1-fe50591663ce.json"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Vertex AI 环境变量测试" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 验证文件存在
if (Test-Path $env:GOOGLE_APPLICATION_CREDENTIALS) {
    Write-Host "✅ 凭证文件找到" -ForegroundColor Green
    Write-Host "   路径: $env:GOOGLE_APPLICATION_CREDENTIALS" -ForegroundColor White
} else {
    Write-Host "❌ 凭证文件未找到" -ForegroundColor Red
    Write-Host "   路径: $env:GOOGLE_APPLICATION_CREDENTIALS" -ForegroundColor White
    exit 1
}

Write-Host ""
Write-Host "正在运行诊断工具..." -ForegroundColor Yellow
Write-Host ""

# 立即在同一会话中运行 Python
python diagnose_env.py

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "如果上面显示环境变量已设置，继续测试 Vertex AI 连接..." -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$continue = Read-Host "是否继续测试 Vertex AI 连接？(y/n)"
if ($continue -eq 'y' -or $continue -eq 'Y') {
    Write-Host ""
    Write-Host "正在测试 Vertex AI 连接..." -ForegroundColor Yellow
    python test_vertex_embedding.py
}
