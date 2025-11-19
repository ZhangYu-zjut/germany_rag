#!/bin/bash
# 2015-2025年数据迁移监控脚本

cd /home/zhangyu/project/rag_germant

echo "🎯 2015-2025年数据迁移实时监控"
echo "======================================="

while true; do
    clear
    
    # 检查进程状态
    echo "🔍 进程状态:"
    ps aux | grep batch_migrate | grep -v grep | while IFS= read -r line; do
        pid=$(echo "$line" | awk '{print $2}')
        cpu=$(echo "$line" | awk '{print $3}')
        mem=$(echo "$line" | awk '{print $4}')
        time=$(echo "$line" | awk '{print $10}')
        echo "   PID: $pid | CPU: ${cpu}% | 内存: ${mem}% | 运行时间: $time"
    done
    
    if ! ps aux | grep batch_migrate | grep -v grep > /dev/null; then
        echo "   ❌ 迁移进程未运行"
    fi
    
    echo ""
    
    # 检查GPU使用情况
    echo "🖥️  GPU状态:"
    nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits 2>/dev/null | while IFS=',' read -r util mem_used mem_total temp; do
        echo "   GPU利用率: ${util}% | 显存: ${mem_used}/${mem_total}MB | 温度: ${temp}°C"
    done || echo "   无法获取GPU信息"
    
    echo ""
    
    # 显示最新日志
    echo "📋 最新日志 (最后10行):"
    echo "---------------------------------------"
    tail -n 10 migration_2015_2025.log 2>/dev/null | while IFS= read -r line; do
        # 高亮关键信息
        if [[ $line == *"迁移完成"* ]]; then
            echo -e "\033[32m$line\033[0m"  # 绿色
        elif [[ $line == *"ERROR"* ]] || [[ $line == *"失败"* ]]; then
            echo -e "\033[31m$line\033[0m"  # 红色
        elif [[ $line == *"进度"* ]] || [[ $line == *"任务进度"* ]]; then
            echo -e "\033[33m$line\033[0m"  # 黄色
        else
            echo "$line"
        fi
    done || echo "   日志文件不存在或为空"
    
    echo ""
    echo "======================================="
    echo "按 Ctrl+C 退出监控 | 刷新间隔: 10秒"
    echo "📁 完整日志: tail -f migration_2015_2025.log"
    echo "======================================="
    
    sleep 10
done
