#!/bin/bash
LOG="test_phase1_verification_20251118_001556.log"

while true; do
    # 检查Q1是否完成（生成了报告）
    if grep -q "问题 2/7:" "$LOG" 2>/dev/null; then
        echo ""
        echo "=========================================="
        echo "✅ Q1测试已完成！开始Q2测试"
        echo "=========================================="
        
        # 查找Q1报告
        Q1_DIR=$(ls -dt outputs/Q1_20251118_* 2>/dev/null | head -1)
        if [ -n "$Q1_DIR" ]; then
            echo "📁 Q1报告目录: $Q1_DIR"
            echo ""
            echo "📄 生成的文件："
            ls -lh "$Q1_DIR"/*.md 2>/dev/null
        fi
        break
    fi
    
    # 每30秒检查一次
    sleep 30
done
