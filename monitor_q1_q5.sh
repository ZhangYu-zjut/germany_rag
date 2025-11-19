#!/bin/bash
# 监控Q1和Q5测试进度
MAX_WAIT=600  # 最多等待10分钟
INTERVAL=30   # 每30秒检查一次
ELAPSED=0

echo "=========================================="
echo "🔍 Q1和Q5测试监控已启动"
echo "=========================================="
echo ""

while [ $ELAPSED -lt $MAX_WAIT ]; do
    MINUTES=$((ELAPSED / 60))
    echo "[$(date +%H:%M:%S)] 等待中... (已等待 ${MINUTES} 分钟)"

    # 检查是否有新的Q1和Q5报告生成
    Q1_NEW=$(ls outputs/Q1_*_13*/Q1_full_report.md 2>/dev/null | wc -l)
    Q5_NEW=$(ls outputs/Q5_*_13*/Q5_full_report.md 2>/dev/null | wc -l)

    if [ "$Q1_NEW" -gt 0 ] && [ "$Q5_NEW" -gt 0 ]; then
        echo ""
        echo "=========================================="
        echo "✅ Q1和Q5报告已生成！"
        echo "=========================================="
        echo ""

        echo "📊 验证结果："

        # Q1 ReRank验证
        Q1_RERANK=$(grep "保留文档数" outputs/Q1_*_13*/Q1_full_report.md 2>/dev/null | head -1)
        echo "Q1 ReRank: $Q1_RERANK"

        # Q5 ReRank验证
        Q5_RERANK=$(grep "保留文档数" outputs/Q5_*_13*/Q5_full_report.md 2>/dev/null | head -1)
        echo "Q5 ReRank: $Q5_RERANK"

        echo ""
        echo "✅ 监控任务完成！可以开始分析Q1的9个政策维度。"
        exit 0
    elif [ "$Q1_NEW" -gt 0 ]; then
        echo "   Q1已完成，Q5进行中..."
    elif [ "$Q5_NEW" -gt 0 ]; then
        echo "   Q5已完成，Q1进行中..."
    else
        echo "   Q1和Q5均未完成"
    fi

    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
done

echo ""
echo "⏰ 等待超时（10分钟），请手动检查测试状态"
exit 2
