#!/bin/bash
LOG_FILE="test_phase1_verification_20251118_001556.log"
CHECK_INTERVAL=30

echo "🔍 开始监控第一阶段验证测试..."
echo "📋 日志文件: $LOG_FILE"
echo "⏰ 检查间隔: ${CHECK_INTERVAL}秒"
echo ""

while true; do
    if [ ! -f "$LOG_FILE" ]; then
        echo "⚠️  日志文件不存在，等待创建..."
        sleep $CHECK_INTERVAL
        continue
    fi
    
    # 检查是否完成
    if grep -q "🎉 测试完成!" "$LOG_FILE" 2>/dev/null; then
        echo ""
        echo "=========================================="
        echo "✅ 测试已完成！"
        echo "=========================================="
        
        # 提取关键统计
        echo ""
        echo "📊 测试统计："
        grep "完成测试:" "$LOG_FILE" | tail -1
        grep "失败:" "$LOG_FILE" | tail -1
        grep "平均耗时:" "$LOG_FILE" | tail -1
        
        echo ""
        echo "📁 输出目录："
        ls -d outputs/Q*_20251118_* 2>/dev/null | tail -7
        
        echo ""
        echo "✅ 监控完成，测试已结束"
        break
    fi
    
    # 检查是否有错误
    if grep -q "insufficient quota" "$LOG_FILE" 2>/dev/null; then
        echo ""
        echo "❌ 检测到API配额不足错误！"
        tail -20 "$LOG_FILE" | grep -A 5 "insufficient quota"
        break
    fi
    
    # 显示当前进度
    CURRENT_Q=$(grep -oP '问题 \d+/7' "$LOG_FILE" | tail -1)
    CURRENT_NODE=$(grep -oP '\[.*Node\]' "$LOG_FILE" | tail -1)
    
    if [ -n "$CURRENT_Q" ]; then
        echo "[$(date +%H:%M:%S)] 进度: $CURRENT_Q | 当前节点: $CURRENT_NODE"
    fi
    
    sleep $CHECK_INTERVAL
done
