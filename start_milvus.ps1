# Milvus Docker 快速启动脚本

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Milvus Docker 快速启动" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Docker 是否运行
Write-Host "[1] 检查 Docker 状态..." -ForegroundColor Yellow
try {
    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Docker 未运行" -ForegroundColor Red
        Write-Host ""
        Write-Host "请启动 Docker Desktop 后重试" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "✅ Docker 运行正常" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker 未安装或未运行" -ForegroundColor Red
    exit 1
}

# 检查是否已有 Milvus 容器
Write-Host ""
Write-Host "[2] 检查 Milvus 容器..." -ForegroundColor Yellow

$existingContainer = docker ps -a --filter "name=milvus" --format "{{.Names}}"

if ($existingContainer) {
    Write-Host "⚠️  发现已存在的 Milvus 容器: $existingContainer" -ForegroundColor Yellow
    
    # 检查容器状态
    $containerStatus = docker ps --filter "name=milvus" --format "{{.Status}}"
    
    if ($containerStatus) {
        Write-Host "✅ Milvus 容器正在运行" -ForegroundColor Green
        Write-Host "   状态: $containerStatus" -ForegroundColor White
        
        Write-Host ""
        Write-Host "Milvus 已经在运行，无需重新启动" -ForegroundColor Green
        Write-Host ""
        Write-Host "如需重启，请先停止容器:" -ForegroundColor Yellow
        Write-Host "  docker stop milvus" -ForegroundColor White
        Write-Host "  docker rm milvus" -ForegroundColor White
        Write-Host "  然后重新运行此脚本" -ForegroundColor White
        Write-Host ""
        exit 0
    } else {
        Write-Host "ℹ️  容器存在但未运行，正在启动..." -ForegroundColor Cyan
        docker start milvus
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Milvus 容器已启动" -ForegroundColor Green
        } else {
            Write-Host "❌ 启动失败，将删除旧容器并重新创建" -ForegroundColor Red
            docker rm -f milvus
            $existingContainer = $null
        }
    }
}

# 创建新容器（如果不存在）
if (-not $existingContainer) {
    Write-Host ""
    Write-Host "[3] 创建并启动 Milvus 容器..." -ForegroundColor Yellow
    Write-Host ""
    
    docker run -d `
        --name milvus `
        -p 19530:19530 `
        -p 9091:9091 `
        -v milvus_data:/var/lib/milvus `
        milvusdb/milvus:latest
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✅ Milvus 容器创建成功！" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "❌ 创建容器失败" -ForegroundColor Red
        exit 1
    }
}

# 等待 Milvus 启动
Write-Host ""
Write-Host "[4] 等待 Milvus 启动..." -ForegroundColor Yellow
Write-Host "   这可能需要几秒钟..." -ForegroundColor White

Start-Sleep -Seconds 5

# 检查容器运行状态
$containerStatus = docker ps --filter "name=milvus" --format "{{.Status}}"

if ($containerStatus) {
    Write-Host "✅ Milvus 运行中: $containerStatus" -ForegroundColor Green
} else {
    Write-Host "❌ Milvus 未运行" -ForegroundColor Red
    Write-Host ""
    Write-Host "查看日志:" -ForegroundColor Yellow
    docker logs milvus --tail 20
    exit 1
}

# 测试连接
Write-Host ""
Write-Host "[5] 测试连接..." -ForegroundColor Yellow

$testResult = python -c "from pymilvus import connections, utility; connections.connect(host='localhost', port='19530'); print('OK')" 2>&1

if ($testResult -match "OK") {
    Write-Host "✅ 连接测试成功！" -ForegroundColor Green
} else {
    Write-Host "⚠️  连接测试失败，但容器正在运行" -ForegroundColor Yellow
    Write-Host "   请等待几秒后重试" -ForegroundColor White
}

# 显示完成信息
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ✅ Milvus 已就绪！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "连接信息:" -ForegroundColor Yellow
Write-Host "  主机: localhost" -ForegroundColor White
Write-Host "  端口: 19530" -ForegroundColor White
Write-Host ""
Write-Host "下一步:" -ForegroundColor Yellow
Write-Host "  python build_index.py" -ForegroundColor White
Write-Host ""
Write-Host "管理命令:" -ForegroundColor Yellow
Write-Host "  docker stop milvus     # 停止" -ForegroundColor White
Write-Host "  docker start milvus    # 启动" -ForegroundColor White
Write-Host "  docker logs milvus     # 查看日志" -ForegroundColor White
Write-Host ""
