#!/bin/bash
# 监控Phase 2测试进度

LOG_FILE="test_phase2_verification_20251118_150551.log"

echo "=========================================="
echo "🔍 Phase 2测试监控"
echo "=========================================="
echo ""

while true; do
    # 检查日志文件大小
    SIZE=$(du -h "$LOG_FILE" 2>/dev/null | cut -f1)

    # 检查已完成的测试数量
    COMPLETED=$(grep -c "✅.*测试完成" "$LOG_FILE" 2>/dev/null || echo 0)

    # 检查是否有报告生成
    REPORTS=$(grep -c "FullRef.*完整引用报告已生成" "$LOG_FILE" 2>/dev/null || echo 0)

    # 检查最新的节点
    LATEST_NODE=$(grep -oP '\[.*Node\]' "$LOG_FILE" 2>/dev/null | tail -1)

    # 检查是否有错误
    ERRORS=$(grep -c "ERROR\|错误\|失败" "$LOG_FILE" 2>/dev/null || echo 0)

    echo "[$(date +%H:%M:%S)] 日志大小: $SIZE | 已完成: $COMPLETED/7 | 报告: $REPORTS/7 | 错误: $ERRORS | 最新节点: $LATEST_NODE"

    # 检查是否全部完成
    if [ "$COMPLETED" -eq 7 ]; then
        echo ""
        echo "=========================================="
        echo "✅ 所有测试已完成！"
        echo "=========================================="

        # 统计报告生成情况
        echo ""
        echo "📊 报告生成情况："
        ls outputs/Q*_$(date +%Y%m%d)*/ 2>/dev/null | grep -oP 'Q\d' | sort | uniq -c

        echo ""
        echo "📄 生成的报告："
        ls outputs/Q*_$(date +%Y%m%d)*/Q*_full_report.md 2>/dev/null || echo "无报告"

        exit 0
    fi

    sleep 60  # 每60秒检查一次
done
