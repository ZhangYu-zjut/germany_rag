#!/bin/bash
LOG_FILE="test_phase1_verification_20251118_001556.log"
CHECK_INTERVAL=1800  # 30分钟 = 1800秒
MAX_WAIT=14400       # 最多等待4小时 = 14400秒
ELAPSED=0

echo "=========================================="
echo "🤖 自动验证系统已启动"
echo "=========================================="
echo "📋 监控日志: $LOG_FILE"
echo "⏰ 检查间隔: 30分钟"
echo "⏳ 最大等待: 4小时"
echo ""

while [ $ELAPSED -lt $MAX_WAIT ]; do
    # 计算当前等待时间（分钟）
    MINUTES=$((ELAPSED / 60))
    
    echo "[$(date +%H:%M:%S)] 等待中... (已等待 ${MINUTES} 分钟)"
    
    # 检查测试是否完成
    if grep -q "🎉 测试完成!" "$LOG_FILE" 2>/dev/null; then
        echo ""
        echo "=========================================="
        echo "✅ 测试已完成！开始分析结果..."
        echo "=========================================="
        echo ""
        
        # 提取测试统计
        echo "📊 测试统计："
        grep -A 3 "完成测试:" "$LOG_FILE" | tail -4
        
        echo ""
        echo "📁 生成的报告："
        ls -lh outputs/Q*_20251118_*/Q*_full_report.md 2>/dev/null
        REPORT_COUNT=$(ls outputs/Q*_20251118_*/Q*_full_report.md 2>/dev/null | wc -l)
        echo "共生成 $REPORT_COUNT 个报告"
        
        echo ""
        echo "=========================================="
        echo "✅ 监控任务完成，请查看结果"
        echo "=========================================="
        exit 0
    fi
    
    # 检查是否有错误
    if tail -100 "$LOG_FILE" | grep -q "insufficient quota" 2>/dev/null; then
        echo ""
        echo "❌ 检测到API配额不足错误！"
        echo "测试可能无法完成，请检查日志"
        exit 1
    fi
    
    # 显示当前进度
    CURRENT_Q=$(grep -oP '问题 \d+/7' "$LOG_FILE" | tail -1)
    if [ -n "$CURRENT_Q" ]; then
        echo "   当前进度: $CURRENT_Q"
    fi
    
    # 等待30分钟
    sleep $CHECK_INTERVAL
    ELAPSED=$((ELAPSED + CHECK_INTERVAL))
done

echo ""
echo "⏰ 已等待最大时长（4小时），测试可能遇到问题"
echo "请手动检查日志: $LOG_FILE"
exit 2
