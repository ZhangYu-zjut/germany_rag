#!/bin/bash
echo "=== 快速状态检查 ==="
echo ""
echo "📊 当前进度："
tail -20 test_phase1_verification_20251118_001556.log | grep -E "(问题 \d+/7|处理子问题|完成)" | tail -5
echo ""
echo "⏰ 运行时长："
START_TIME=$(head -50 test_phase1_verification_20251118_001556.log | grep "2025-11-18" | head -1 | cut -d' ' -f1-2)
CURRENT_TIME=$(date "+%Y-%m-%d %H:%M:%S")
echo "  开始: $START_TIME"
echo "  当前: $CURRENT_TIME"
echo ""
echo "📁 已生成报告："
ls -lh outputs/Q*_20251118_*/Q*_full_report.md 2>/dev/null | wc -l
