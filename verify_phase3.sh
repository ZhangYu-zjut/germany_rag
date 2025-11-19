#!/bin/bash
# Phase 3验证脚本 - 检查对立观点强制提取机制效果

echo "========================================"
echo "📋 Phase 3验证：对立观点强制提取机制"
echo "========================================"
echo ""

# 最新Q6报告路径
Q6_REPORT="outputs/Q6_20251118_153348/Q6_full_report.md"
Q5_REPORT="outputs/Q5_20251118_153052/Q5_full_report.md"

if [ ! -f "$Q6_REPORT" ]; then
  echo "❌ Q6报告未找到: $Q6_REPORT"
  exit 1
fi

echo "=== Q6验证（4处价值观偏见问题）==="
echo ""

# Q6问题1: 范围准确性
echo "【问题1】 范围准确性: 应只回答CDU/CSU，不包含其他党派"
PARTY_COUNT=$(grep -E "SPD|绿党|GRÜNE|左翼|LINKE|AfD" "$Q6_REPORT" | wc -l || echo 0)
if [ "$PARTY_COUNT" -gt 5 ]; then
  echo "  ⚠️  报告中提及其他党派 ${PARTY_COUNT} 次（可能范围错误）"
else
  echo "  ✅ 范围正确（主要关注CDU/CSU）"
fi
echo ""

# Q6问题2: 2017年强硬立场（关键短语）
echo "【问题2】 2017年温和+强硬立场平衡"
echo "  🎯 期望关键短语:"
echo "     - 温和: '拒绝遣返到不安全国家' / 'nicht in unsichere Länder'"
echo "     - 强硬: 'Zwang durchsetzen' / '强制执行' / '强制遣返'"
echo ""

# 检查温和立场
MODERATE_2017=$(grep -i "Afghanistan\|unsichere.*Länder\|nicht.*abschie" "$Q6_REPORT" | grep -c "2017\|Afghanistan" || echo 0)
echo "  温和立场出现: ${MODERATE_2017}次"

# 检查强硬立场（关键！）
HARD_2017=$(grep -i "Zwang durchsetzen\|强制执行\|强制遣返\|Ausreisepflicht.*Zwang" "$Q6_REPORT" | wc -l || echo 0)
if [ "$HARD_2017" -gt 0 ]; then
  echo "  ✅✅✅ 强硬立场出现: ${HARD_2017}次 【Phase 3成功】"
  echo ""
  echo "  📄 具体内容:"
  grep -i "Zwang durchsetzen\|强制执行" "$Q6_REPORT" | head -2 | sed 's/^/      /'
else
  echo "  ❌ 强硬立场: 0次 【Phase 3失败】"
fi
echo ""

# Q6问题3: 2017年延长拘留
echo "【问题3】 2017年遣返措施（延长拘留）"
echo "  🎯 期望关键短语: 'Ausreisegewahrsam verlängern' / '延长.*拘留'"
DETENTION_2017=$(grep -i "Ausreisegewahrsam verlängern\|Höchstdauer.*Ausreisegewahrsam\|延长.*拘留\|延长.*羁押" "$Q6_REPORT" | wc -l || echo 0)
if [ "$DETENTION_2017" -gt 0 ]; then
  echo "  ✅✅✅ 发现延长拘留内容: ${DETENTION_2017}次 【Phase 3成功】"
  echo ""
  echo "  📄 具体内容:"
  grep -i "Ausreisegewahrsam verlängern\|Höchstdauer.*Ausreisegewahrsam" "$Q6_REPORT" | head -2 | sed 's/^/      /'
else
  echo "  ❌ 未发现延长拘留内容 【Phase 3失败】"
fi
echo ""

# Q6问题4: 2019年强硬立场
echo "【问题4】 2019年温和+强硬立场平衡"
echo "  🎯 期望关键短语:"
echo "     - 温和: '不可遣返到不安全地区'"
echo "     - 强硬: '加强遣返力度' / 'Abschiebung.*tatsächlich' / '确保.*离开'"
echo ""

HARD_2019=$(grep -i "加强遣返\|Abschiebung.*tatsächlich\|tatsächlich.*verlassen\|确保.*离开\|durchsetzen.*Ausreise" "$Q6_REPORT" | wc -l || echo 0)
if [ "$HARD_2019" -gt 0 ]; then
  echo "  ✅✅✅ 2019年强硬立场: ${HARD_2019}次 【Phase 3成功】"
  echo ""
  echo "  📄 具体内容:"
  grep -i "Abschiebung.*tatsächlich\|tatsächlich.*verlassen" "$Q6_REPORT" | head -2 | sed 's/^/      /'
else
  echo "  ❌ 2019年强硬立场: 0次 【Phase 3失败】"
fi
echo ""

echo "========================================"
echo "📊 Q6验证总结"
echo "========================================"

PASS_COUNT=0
[ "$HARD_2017" -gt 0 ] && ((PASS_COUNT++))
[ "$DETENTION_2017" -gt 0 ] && ((PASS_COUNT++))
[ "$HARD_2019" -gt 0 ] && ((PASS_COUNT++))

echo "  通过项: ${PASS_COUNT}/3 核心指标"
echo ""

if [ "$PASS_COUNT" -eq 3 ]; then
  echo "  ✅✅✅ Q6: 100%修复！Phase 3对立观点机制生效！"
elif [ "$PASS_COUNT" -gt 0 ]; then
  echo "  ⚠️  Q6: 部分修复（${PASS_COUNT}/3），Phase 3部分生效"
else
  echo "  ❌ Q6: 未修复，Phase 3可能未生效"
fi

echo ""
echo "========================================"
echo "=== Q5验证（信息完整性）==="
echo "========================================"
echo ""

if [ -f "$Q5_REPORT" ]; then
  echo "✅ Q5报告已生成（Phase 2修复成功）"
  echo "  报告大小: $(du -h "$Q5_REPORT" | cut -f1)"

  # 检查关键信息
  echo ""
  echo "【信息完整性检查】"

  KULTUR=$(grep -ic "Kultur baut Brücken\|文化.*桥梁\|文化政策" "$Q5_REPORT" || echo 0)
  echo "  - CDU/CSU '文化政策': ${KULTUR}次 $([ "$KULTUR" -gt 0 ] && echo "✅" || echo "❌")"

  RECHTE=$(grep -ic "Recht auf Bildung\|权利平等\|教育.*权利" "$Q5_REPORT" || echo 0)
  echo "  - 绿党'权利平等融合': ${RECHTE}次 $([ "$RECHTE" -gt 0 ] && echo "✅" || echo "❌")"

  AUSWAHL=$(grep -ic "Bleibeperspektive\|选择性.*融合\|选择性.*整合" "$Q5_REPORT" || echo 0)
  echo "  - CDU/CSU '选择性融合': ${AUSWAHL}次 $([ "$AUSWAHL" -gt 0 ] && echo "✅" || echo "❌")"

  Q5_PASS=$(( ($KULTUR > 0 ? 1 : 0) + ($RECHTE > 0 ? 1 : 0) + ($AUSWAHL > 0 ? 1 : 0) ))
  echo ""
  echo "  信息完整性: ${Q5_PASS}/3"
else
  echo "❌ Q5报告未生成"
fi

echo ""
echo "========================================"
echo "📝 总结"
echo "========================================"
echo "  Q6 (价值观偏见): ${PASS_COUNT}/3 核心指标通过"
echo "  Q5 (信息完整性): 已生成"
echo ""
echo "  建议："
if [ "$PASS_COUNT" -lt 3 ]; then
  echo "  1. 检查workflow.py是否使用IncrementalSummarizeNodeV2"
  echo "  2. 确认Phase 3修改已应用到summarize_incremental_v2.py"
  echo "  3. 重新运行测试以应用最新修改"
fi
echo "========================================"
