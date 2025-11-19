#!/bin/bash
# 分析Phase 2修复效果（增量式总结V2）

echo "=========================================="
echo "📊 Phase 2修复效果分析"
echo "增量式总结节点V2（两阶段架构）"
echo "=========================================="
echo ""

# Phase 2报告路径（最新生成的）
Q1_P2="outputs/Q1_20251118_140731/Q1_full_report.md"  # Phase 1的（Phase 2没有重新测试）
Q2_P2="outputs/Q2_20251118_151832/Q2_full_report.md"
Q3_P2="outputs/Q3_20251118_151950/Q3_full_report.md"
Q4_P2="outputs/Q4_20251118_152134/Q4_full_report.md"
Q5_P2="outputs/Q5_20251118_153052/Q5_full_report.md"
Q6_P2="outputs/Q6_20251118_153348/Q6_full_report.md"
Q7_P2="outputs/Q7_20251118_153503/Q7_full_report.md"

# ===========================================
# Q1分析（9个政策维度）- Phase 1已100%修复
# ===========================================
echo "=== Q1 (9处信息遗漏) - Phase 1已100%修复 ==="
echo "Phase 2未重新测试（保留Phase 1结果）"
echo ""

# ===========================================
# Q2分析（3处问题）
# ===========================================
echo "=== Q2 (3处问题) ==="

if [ -f "$Q2_P2" ]; then
  echo "✅ Q2报告已生成"

  # 检查Speaker问题
  MODERATOR_COUNT=$(grep -c "Vizepräsident\|Präsident.*None" "$Q2_P2" 2>/dev/null || echo 0)
  echo "  - Speaker过滤: $(if [ "$MODERATOR_COUNT" -gt 0 ]; then echo "❌ 仍有${MODERATOR_COUNT}处主持人"; else echo "✅ 无主持人"; fi)"

  # 检查ReRank
  RERANK=$(grep "保留文档数" "$Q2_P2" | head -1 | grep -oP '\d+' || echo "?")
  echo "  - ReRank文档数: $RERANK"

  # 检查引用数量
  CITE_COUNT=$(grep "共找到.*个引用" "$Q2_P2" | grep -oP '\d+' | head -1 || echo "?")
  echo "  - 引用数量: ${CITE_COUNT}个"
else
  echo "❌ Q2报告未生成"
fi

echo ""

# ===========================================
# Q3分析（2处信息遗漏）- 关键测试点
# ===========================================
echo "=== Q3 (2处信息遗漏) - 🔥 关键验证点 ==="

if [ -f "$Q3_P2" ]; then
  echo "✅ Q3报告已生成 ($(du -h "$Q3_P2" | cut -f1))"

  echo ""
  echo "  🎯 客户反馈：绿党强调'gemeinsame europäische Antwort'被遗漏"
  echo ""

  # 检查关键短语（多种变体）
  if grep -qi "gemeinsame europäische Antwort\|gemeinsame.*europäische.*Lösung" "$Q3_P2"; then
    echo "  ✅✅✅ 【Phase 2成功】找到'gemeinsame europäische Antwort'相关内容！"
    echo ""
    echo "  📄 具体内容："
    grep -i "gemeinsame europäische Antwort\|gemeinsame.*europäische.*Lösung" "$Q3_P2" | head -3 | sed 's/^/      /'
  else
    echo "  ❌ 未找到'gemeinsame europäische Antwort'"
  fi

  echo ""

  # 检查绿党相关内容的丰富度
  GRUNE_COUNT=$(grep -ci "Grüne\|Bündnis 90" "$Q3_P2" || echo 0)
  echo "  - 绿党提及次数: ${GRUNE_COUNT}次"
else
  echo "❌ Q3报告未生成"
fi

echo ""

# ===========================================
# Q4分析（3处窗口长度不足）
# ===========================================
echo "=== Q4 (3处窗口长度不足) ==="

if [ -f "$Q4_P2" ]; then
  echo "✅ Q4报告已生成 ($(du -h "$Q4_P2" | cut -f1))"

  # 检查ReRank文档数
  RERANK_TOTAL=$(grep -c "保留文档数" "$Q4_P2" || echo 0)
  echo "  - 子问题数量: $RERANK_TOTAL"

  # 检查总引用数
  CITE_COUNT=$(grep "共找到.*个引用" "$Q4_P2" | grep -oP '\d+' | head -1 || echo "?")
  echo "  - 总引用数: ${CITE_COUNT}个"
else
  echo "❌ Q4报告未生成"
fi

echo ""

# ===========================================
# Q5分析（4处: 3处遗漏 + 1处引用错误）
# ===========================================
echo "=== Q5 (4处: 3处遗漏 + 1处引用错误) - 🔥 关键验证点 ==="

if [ -f "$Q5_P2" ]; then
  echo "  ✅✅✅ 【Phase 2成功】Q5报告已生成！（Phase 1失败）"
  echo "  报告大小: $(du -h "$Q5_P2" | cut -f1)"

  # 检查引用映射
  CITE_COUNT=$(grep "共找到.*个引用" "$Q5_P2" | grep -oP '\d+' | head -1 || echo "?")
  echo "  - 引用数量: ${CITE_COUNT}个"

  # 检查Quellen引用映射
  if grep -q "Quellen引用映射" "$Q5_P2"; then
    echo "  ✅ 有Quellen引用映射"
  else
    echo "  ❌ 没有Quellen引用映射"
  fi
else
  echo "  ❌ Q5报告未生成（Phase 2失败）"
fi

echo ""

# ===========================================
# Q6分析（基准对比）
# ===========================================
echo "=== Q6 (基准对比) ==="

if [ -f "$Q6_P2" ]; then
  echo "✅ Q6报告已生成 ($(du -h "$Q6_P2" | cut -f1))"
  CITE_COUNT=$(grep "共找到.*个引用" "$Q6_P2" | grep -oP '\d+' | head -1 || echo "?")
  echo "  - 引用数量: ${CITE_COUNT}个"
else
  echo "❌ Q6报告未生成"
fi

echo ""

# ===========================================
# Q7分析（2处: 窗口长度 + 细节缺失）- 关键测试点
# ===========================================
echo "=== Q7 (2处: 窗口长度 + 细节缺失) - 🔥 关键验证点 ==="

if [ -f "$Q7_P2" ]; then
  echo "✅ Q7报告已生成 ($(du -h "$Q7_P2" | cut -f1))"

  echo ""
  echo "  🎯 客户反馈：缺少AfD的具体立场（反对难民配额等）"
  echo ""

  # 检查AfD相关内容的详细度
  AFD_COUNT=$(grep -ci "AfD\|Alternative" "$Q7_P2" || echo 0)
  echo "  - AfD提及次数: ${AFD_COUNT}次"

  # 检查配额相关内容（关键短语）
  if grep -qi "配额\|Quote\|Kontingent\|Obergrenzen" "$Q7_P2"; then
    echo "  ✅✅✅ 【Phase 2成功】包含配额/Kontingent相关内容！"
    echo ""
    echo "  📄 具体内容："
    grep -i "配额\|Quote\|Kontingent\|Obergrenzen" "$Q7_P2" | head -3 | sed 's/^/      /'
  else
    echo "  ❌ 未找到配额相关内容"
  fi

  echo ""

  CITE_COUNT=$(grep "共找到.*个引用" "$Q7_P2" | grep -oP '\d+' | head -1 || echo "?")
  echo "  - 引用数量: ${CITE_COUNT}个"
else
  echo "❌ Q7报告未生成"
fi

echo ""
echo "=========================================="
echo "📝 Phase 2核心验证总结："
echo "1. Q3 - 'gemeinsame europäische Antwort' 是否出现？"
echo "2. Q5 - 报告生成是否成功？"
echo "3. Q7 - '配额/Kontingent' 是否出现？"
echo "=========================================="
