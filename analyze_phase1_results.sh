#!/bin/bash
echo "=========================================="
echo "📊 第一阶段修复效果分析"
echo "=========================================="
echo ""

# 统计生成的报告数量
REPORT_COUNT=$(ls outputs/Q*_20251118_*/Q*_full_report.md 2>/dev/null | wc -l)
echo "1. 报告生成情况："
echo "   ✅ 成功生成: $REPORT_COUNT/7 个报告"
echo ""

# 检查客户反馈的关键问题
echo "2. 客户反馈问题验证（19处）："
echo ""

# Q1的9处遗漏检查
echo "   Q1 (9处信息遗漏):"
if [ -f "outputs/Q1_20251118_*/Q1_full_report.md" ]; then
    Q1_FILE=$(ls outputs/Q1_20251118_*/Q1_full_report.md 2>/dev/null | head -1)
    
    # 检查关键政策是否出现
    CHECK_ITEMS=(
        "sichere Herkunftsländer:安全来源国"
        "Grenzkontrollen:边境管控"
        "Familiennachzug:家庭团聚"
        "Abschiebung:遣返"
        "europäische Lösung:欧洲解决方案"
        "Integration:融合"
        "Asylverfahren:庇护程序"
        "Fluchtursachen:难民原因"
        "Obergrenze:上限"
    )
    
    FOUND=0
    for item in "${CHECK_ITEMS[@]}"; do
        KEYWORD=$(echo $item | cut -d: -f1)
        DESC=$(echo $item | cut -d: -f2)
        if grep -qi "$KEYWORD" "$Q1_FILE" 2>/dev/null; then
            echo "      ✅ $DESC ($KEYWORD)"
            FOUND=$((FOUND + 1))
        else
            echo "      ❌ $DESC ($KEYWORD) - 未找到"
        fi
    done
    
    echo "      修复率: $FOUND/9 ($(($FOUND * 100 / 9))%)"
else
    echo "      ⚠️ Q1报告未生成"
fi

echo ""
echo "   Q2 (3处问题):"
if [ -f "outputs/Q2_20251118_*/Q2_full_report.md" ]; then
    Q2_FILE=$(ls outputs/Q2_20251118_*/Q2_full_report.md 2>/dev/null | head -1)
    
    # 检查是否还有Vizepräsident
    if grep -q "Vizepräsident" "$Q2_FILE"; then
        echo "      ❌ Speaker过滤未生效（仍有主持人）"
    else
        echo "      ✅ Speaker过滤已生效"
    fi
    
    # 检查是否有引用映射
    if grep -q "Quellen引用映射" "$Q2_FILE"; then
        echo "      ✅ 引用映射功能正常"
    else
        echo "      ❌ 引用映射缺失"
    fi
else
    echo "      ⚠️ Q2报告未生成"
fi

echo ""
echo "3. ReRank优化验证:"
for report in outputs/Q*_20251118_*/Q*_full_report.md; do
    if [ -f "$report" ]; then
        QNAME=$(basename $(dirname $report) | cut -d_ -f1)
        RERANK_COUNT=$(grep "保留文档数:" "$report" | head -1 | grep -oP '\d+' | head -1)
        if [ "$RERANK_COUNT" = "15" ]; then
            echo "   ✅ $QNAME: ReRank保留15个文档"
        else
            echo "   ⚠️ $QNAME: ReRank保留${RERANK_COUNT}个文档"
        fi
    fi
done

echo ""
echo "=========================================="
echo "📝 详细报告位置："
ls -lh outputs/Q*_20251118_*/Q*_full_report.md 2>/dev/null
echo ""
echo "=========================================="
