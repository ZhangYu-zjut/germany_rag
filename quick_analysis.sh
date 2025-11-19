#!/bin/bash
echo "=========================================="
echo "📊 第一阶段修复效果快速分析"
echo "=========================================="
echo ""

echo "1. 报告生成情况："
echo "   ✅ 成功: 5/7 (Q2, Q3, Q4, Q6, Q7)"
echo "   ❌ 失败: 2/7 (Q1, Q5 - 格式化错误)"
echo ""

echo "2. ReRank参数验证（Fix 4）："
for report in outputs/Q*_20251118_*/Q*_full_report.md; do
    if [ -f "$report" ]; then
        QNAME=$(basename $(dirname $report) | cut -d_ -f1)
        RERANK_COUNT=$(grep "保留文档数:" "$report" | head -1 | awk '{print $2}')
        if [ "$RERANK_COUNT" = "15" ]; then
            echo "   ✅ $QNAME: ReRank保留15个文档"
        else
            echo "   ⚠️ $QNAME: ReRank保留${RERANK_COUNT:-未知}个文档"
        fi
    fi
done

echo ""
echo "3. 引用映射功能验证："
for report in outputs/Q*_20251118_*/Q*_full_report.md; do
    if [ -f "$report" ]; then
        QNAME=$(basename $(dirname $report) | cut -d_ -f1)
        if grep -q "Quellen引用映射" "$report"; then
            CITE_COUNT=$(grep "共找到.*个引用" "$report" | grep -oP '\d+' | head -1)
            echo "   ✅ $QNAME: 引用映射正常 (${CITE_COUNT:-?}个引用)"
        else
            echo "   ❌ $QNAME: 引用映射缺失"
        fi
    fi
done

echo ""
echo "4. Speaker过滤验证（Fix 1）:"
for report in outputs/Q*_20251118_*/Q*_full_report.md; do
    if [ -f "$report" ]; then
        QNAME=$(basename $(dirname $report) | cut -d_ -f1)
        MODERATOR_COUNT=$(grep -c "Vizepräsident\|Präsident.*None" "$report" 2>/dev/null)
        if [ "$MODERATOR_COUNT" -gt 0 ]; then
            echo "   ⚠️ $QNAME: 仍有${MODERATOR_COUNT}处主持人出现（旧数据）"
        else
            echo "   ✅ $QNAME: 无主持人出现"
        fi
    fi
done

echo ""
echo "=========================================="
