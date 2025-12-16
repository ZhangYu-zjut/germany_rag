#!/usr/bin/env python3
"""
Keep-Alive脚本 - 防止Render免费版服务休眠

使用方法：
1. 在本地或另一台服务器上运行此脚本
2. 或使用外部Cron服务（如cron-job.org）定期访问你的Render URL

外部Cron服务推荐：
- https://cron-job.org (免费)
- https://uptimerobot.com (免费监控)
- GitHub Actions (免费)
"""

import requests
import time
import os
from datetime import datetime

# 你的Render应用URL
RENDER_APP_URL = os.getenv("RENDER_APP_URL", "https://your-app.onrender.com")

# 健康检查端点
HEALTH_ENDPOINT = "/_stcore/health"

# 检查间隔（秒）- Render免费版15分钟休眠，设置为10分钟
CHECK_INTERVAL = 600  # 10分钟

def keep_alive():
    """发送健康检查请求"""
    url = f"{RENDER_APP_URL}{HEALTH_ENDPOINT}"
    try:
        response = requests.get(url, timeout=30)
        status = "✅ OK" if response.status_code == 200 else f"⚠️ {response.status_code}"
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {status} - {url}")
        return response.status_code == 200
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ Error: {e}")
        return False

def main():
    """主循环"""
    print("=" * 50)
    print("Render Keep-Alive Service")
    print(f"Target: {RENDER_APP_URL}")
    print(f"Interval: {CHECK_INTERVAL}s ({CHECK_INTERVAL//60}min)")
    print("=" * 50)

    while True:
        keep_alive()
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
