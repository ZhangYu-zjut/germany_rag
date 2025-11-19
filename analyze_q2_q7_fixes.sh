#!/bin/bash
# 分析Q2-Q7报告，评估第一阶段修复对剩余问题的影响

echo "=========================================="
echo "📊 Q2-Q7问题修复情况分析"
echo "=========================================="
echo ""

# Q2分析（3处问题）
echo "=== Q2 (3处问题) ==="
Q2_REPORT="outputs/Q2_20251118_140916/Q2_full_report.md"
if [ -f "$Q2_REPORT" ]; then
  echo "✅ Q2报告已生成"

  # 检查Speaker问题
  MODERATOR_COUNT=$(grep -c "Vizepräsident\|Präsident.*None" "$Q2_REPORT" 2>/dev/null || echo 0)
  echo "  - Speaker过滤: $(if [ "$MODERATOR_COUNT" -gt 0 ]; then echo "❌ 仍有${MODERATOR_COUNT}处主持人（旧数据）"; else echo "✅ 无主持人"; fi)"

  # 检查ReRank
  RERANK=$(grep "保留文档数" "$Q2_REPORT" | head -1 | grep -oP '\d+' || echo "?")
  echo "  - ReRank文档数: $RERANK (目标15)"

  # 检查引用数量
  CITE_COUNT=$(grep "共找到.*个引用" "$Q2_REPORT" | grep -oP '\d+' | head -1 || echo "?")
  echo "  - 引用数量: ${CITE_COUNT}个"
else
  echo "❌ Q2报告未生成"
fi

echo ""

# Q3分析（2处信息遗漏）
echo "=== Q3 (2处信息遗漏) ==="
Q3_REPORT="outputs/Q3_20251118_141033/Q3_full_report.md"
if [ -f "$Q3_REPORT" ]; then
  echo "✅ Q3报告已生成"

  # 客户反馈：绿党强调"gemeinsame europäische Antwort"被遗漏
  if grep -qi "gemeinsame europäische Antwort\|gemeinsame.*europäische.*Lösung" "$Q3_REPORT"; then
    echo "  ✅ 找到'gemeinsame europäische Antwort'相关内容"
  else
    echo "  ❌ 未找到'gemeinsame europäische Antwort'"
  fi

  # 检查绿党相关内容的丰富度
  GRUNE_COUNT=$(grep -ci "Grüne\|Bündnis 90" "$Q3_REPORT" || echo 0)
  echo "  - 绿党提及次数: ${GRUNE_COUNT}次"
else
  echo "❌ Q3报告未生成"
fi

echo ""

# Q4分析（3处窗口长度不足）
echo "=== Q4 (3处窗口长度不足) ==="
Q4_REPORT="outputs/Q4_20251118_141215/Q4_full_report.md"
if [ -f "$Q4_REPORT" ]; then
  echo "✅ Q4报告已生成 ($(du -h "$Q4_REPORT" | cut -f1))"

  # 检查ReRank文档数
  RERANK_TOTAL=$(grep -c "保留文档数" "$Q4_REPORT" || echo 0)
  echo "  - 子问题数量: $RERANK_TOTAL"

  # 检查总引用数
  CITE_COUNT=$(grep "共找到.*个引用" "$Q4_REPORT" | grep -oP '\d+' | head -1 || echo "?")
  echo "  - 总引用数: ${CITE_COUNT}个"

  # 检查是否包含具体政策细节
  if grep -qi "具体.*措施\|konkrete.*Maßnahmen\|detaillierte" "$Q4_REPORT"; then
    echo "  ✅ 包含具体措施描述"
  else
    echo "  ⚠️ 可能缺少具体措施"
  fi
else
  echo "❌ Q4报告未生成"
fi

echo ""

# Q6分析
echo "=== Q6 (基准对比) ==="
Q6_REPORT="outputs/Q6_20251118_142248/Q6_full_report.md"
if [ -f "$Q6_REPORT" ]; then
  echo "✅ Q6报告已生成 ($(du -h "$Q6_REPORT" | cut -f1))"
  CITE_COUNT=$(grep "共找到.*个引用" "$Q6_REPORT" | grep -oP '\d+' | head -1 || echo "?")
  echo "  - 引用数量: ${CITE_COUNT}个"
else
  echo "❌ Q6报告未生成"
fi

echo ""

# Q7分析（2处：窗口长度 + 细节缺失）
echo "=== Q7 (2处: 窗口长度 + 细节缺失) ==="
Q7_REPORT="outputs/Q7_20251118_142358/Q7_full_report.md"
if [ -f "$Q7_REPORT" ]; then
  echo "✅ Q7报告已生成"

  # 检查AfD相关内容的详细度
  AFD_COUNT=$(grep -ci "AfD\|Alternative" "$Q7_REPORT" || echo 0)
  echo "  - AfD提及次数: ${AFD_COUNT}次"

  # 客户反馈：缺少AfD的具体立场（反对难民配额等）
  if grep -qi "配额\|Quote\|Kontingent" "$Q7_REPORT"; then
    echo "  ✅ 包含配额/Kontingent相关内容"
  else
    echo "  ❌ 未找到配额相关内容"
  fi

  CITE_COUNT=$(grep "共找到.*个引用" "$Q7_REPORT" | grep -oP '\d+' | head -1 || echo "?")
  echo "  - 引用数量: ${CITE_COUNT}个"
else
  echo "❌ Q7报告未生成"
fi

echo ""
echo "=========================================="
echo "📝 建议："
echo "1. 查看具体报告内容，对比客户反馈"
echo "2. 如果大部分问题已解决，可能不需要增量式总结"
echo "3. 如果仍有明显遗漏，再实施第二阶段策略"
echo "=========================================="
