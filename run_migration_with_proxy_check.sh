#!/bin/bash
# 带代理检查的迁移脚本
# 自动检测代理是否可用，如果不可用则临时禁用

echo "🔍 检查代理服务状态"

# 检查代理是否可用
if timeout 2 curl -x http://127.0.0.1:7890 -s http://www.baidu.com > /dev/null 2>&1; then
    echo "✅ 代理服务可用，使用代理"
    export http_proxy=http://127.0.0.1:7890
    export https_proxy=http://127.0.0.1:7890
    export ALL_PROXY=http://127.0.0.1:7890
else
    echo "⚠️  代理服务不可用，临时禁用代理"
    unset http_proxy https_proxy ALL_PROXY
fi

echo "🚀 开始迁移..."
cd /home/zhangyu/project/rag_germant
source venv/bin/activate
python3 migrate_2015_optimal_config.py








