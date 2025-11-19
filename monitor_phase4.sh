#!/bin/bash
echo "🔍 Phase 4测试监控启动..."
echo ""

for i in {1..20}; do
    sleep 15
    
    echo "⏱️  检查点 $i ($(date +%H:%M:%S)):"
    
    # 检查日志文件大小
    if [ -f "test_phase4_q6_final.log" ]; then
        SIZE=$(wc -l < test_phase4_q6_final.log)
        echo "   日志行数: $SIZE"
        
        # 检查关键进度
        if grep -q "Query扩展" test_phase4_q6_final.log 2>/dev/null; then
            echo "   ✅ Query扩展已启动"
        fi
        
        if grep -q "检索完成" test_phase4_q6_final.log 2>/dev/null; then
            echo "   ✅ 检索阶段完成"
        fi
        
        if grep -q "报告已生成\|测试完成" test_phase4_q6_final.log 2>/dev/null; then
            echo "   ✅✅✅ 测试完成！"
            echo ""
            echo "📊 最终结果:"
            tail -30 test_phase4_q6_final.log | grep -E "Zwang|关键短语|✅|❌" | head -15
            exit 0
        fi
        
        # 检查错误
        if grep -qi "error\|traceback\|failed" test_phase4_q6_final.log 2>/dev/null; then
            echo "   ⚠️  发现错误，查看日志:"
            tail -20 test_phase4_q6_final.log
            exit 1
        fi
    else
        echo "   ⏳ 等待日志文件生成..."
    fi
    
    echo ""
done

echo "⏰ 监控超时（5分钟），请手动检查日志"
