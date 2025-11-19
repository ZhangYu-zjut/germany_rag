#!/bin/bash

# 迁移重启监控脚本

echo "🔍 德国议会数据迁移重启监控"
echo "============================="

while true; do
    echo -e "\n📊 $(date '+%Y-%m-%d %H:%M:%S') 状态报告:"
    echo "----------------------------------------------------"
    
    # 检查进程状态
    echo "🔍 进程状态:"
    PROCESS_INFO=$(ps aux | grep "batch_migrate_2015_2025.py" | grep -v grep)
    if [ -n "$PROCESS_INFO" ]; then
        echo "   ✅ 迁移进程运行中"
        echo "   $PROCESS_INFO" | awk '{print "   ├─ PID: "$2" | CPU: "$3"% | 内存: "$4"% | 命令: "$11}'
        
        # GPU状态
        if command -v nvidia-smi &> /dev/null; then
            echo -e "\n🖥️  GPU状态:"
            nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits | head -1 | awk -F',' '{printf "   ├─ GPU利用率: %s%% | 显存: %sMB/%sMB | 温度: %s°C\n", $1, $2, $3, $4}'
        fi
    else
        echo "   ❌ 迁移进程未运行"
    fi
    
    # 检查日志文件
    echo -e "\n📋 日志状态:"
    if [ -f "migration_2015_2025_restart.log" ]; then
        LOG_SIZE=$(du -h migration_2015_2025_restart.log | cut -f1)
        LOG_LINES=$(wc -l < migration_2015_2025_restart.log)
        echo "   ├─ 日志大小: $LOG_SIZE"
        echo "   ├─ 日志行数: $LOG_LINES"
        
        # 显示最新的进度信息
        echo "   └─ 最新进度:"
        tail -n 5 migration_2015_2025_restart.log | grep -E "(进度|完成|开始|年份)" | tail -3 | sed 's/^/      /'
    else
        echo "   ❌ 日志文件不存在"
    fi
    
    # 检查检查点文件
    echo -e "\n💾 检查点状态:"
    if [ -f "batch_migration_progress.json" ]; then
        python3 -c "
import json
with open('batch_migration_progress.json', 'r') as f:
    data = json.load(f)
    completed = len(data.get('completed_years', []))
    total = len(data.get('tasks_status', []))
    print(f'   ├─ 已完成年份: {completed}/{total}')
    print(f'   └─ 完成年份: {data.get(\"completed_years\", [])}')
" 2>/dev/null || echo "   ❌ 无法读取检查点文件"
    else
        echo "   ❌ 检查点文件不存在"
    fi
    
    echo ""
    echo "=======================================按 Ctrl+C 退出监控"
    
    # 等待10秒
    sleep 10
done
