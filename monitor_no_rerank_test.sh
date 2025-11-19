#!/bin/bash
# 监控Q1-Q7无ReRank测试进度

LOG_FILE=$(ls -t test_phase4_NO_RERANK_Q1_Q7_*.log 2>/dev/null | head -1)

if [ -z "$LOG_FILE" ]; then
    echo "❌ 测试日志文件不存在"
    exit 1
fi

echo "======================================"
echo "📊 Q1-Q7无ReRank测试监控"
echo "日志文件: $LOG_FILE"
echo "======================================"
echo ""

# 实时监控循环
while true; do
    clear
    echo "⏰ $(date '+%Y-%m-%d %H:%M:%S')"
    echo "======================================"

    # 检查已完成的问题
    echo "📝 已完成的问题:"
    grep -E "Q[1-7].*完整引用报告已生成" "$LOG_FILE" 2>/dev/null | tail -7

    echo ""
    echo "📊 测试进度统计:"
    TOTAL=7
    COMPLETED=$(grep -c "完整引用报告已生成" "$LOG_FILE" 2>/dev/null || echo 0)
    echo "   完成: $COMPLETED / $TOTAL"

    echo ""
    echo "🔍 当前执行节点:"
    tail -30 "$LOG_FILE" 2>/dev/null | grep -E "(IntentNode|ClassifyNode|DecomposeNode|RetrieveNode|SummarizeNode|测试问题)" | tail -5

    echo ""
    echo "⚠️ 错误检测:"
    grep -i "ERROR\|Exception\|Traceback" "$LOG_FILE" 2>/dev/null | tail -3 || echo "   无错误"

    echo ""
    echo "======================================"

    # 检查是否全部完成
    if [ "$COMPLETED" -eq "$TOTAL" ]; then
        echo "✅ 所有测试已完成！"
        break
    fi

    sleep 30
done

echo ""
echo "📄 最终报告位置:"
ls -lt outputs/Q*_$(date +%Y%m%d)*/Q*_full_report.md 2>/dev/null | head -7
