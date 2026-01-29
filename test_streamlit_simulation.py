#!/usr/bin/env python3
"""
Streamlit 调用方式模拟脚本

模拟 Streamlit 前端调用后端 API 的方式进行测试。
本质上与 API 测试相同，但使用 Streamlit 相同的超时配置（1200秒）。

用法:
    python test_streamlit_simulation.py              # 测试所有7个问题
    python test_streamlit_simulation.py --question 1 # 只测试第1个问题
    python test_streamlit_simulation.py --question 3 # 只测试第3个问题
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from pathlib import Path

import requests
from dotenv import load_dotenv

# 加载环境变量
project_root = Path(__file__).parent
load_dotenv(project_root / ".env", override=True)

# ========== 配置（与 Streamlit 完全一致）==========
API_URL = os.getenv("API_URL", "http://localhost:8000")
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "1200"))  # 默认20分钟超时

# 时区配置：UTC+8（北京时间）
UTC_PLUS_8 = timezone(timedelta(hours=8))

# ========== 7个标准测试问题（德语）==========
STANDARD_QUESTIONS = [
    {
        "id": "Q1",
        "question": "Wie hat sich die Position der CDU/CSU zur Flüchtlingspolitik seit 2015 verändert?",
        "desc": "CDU/CSU难民政策变化(2015至今)",
        "type": "变化类"
    },
    {
        "id": "Q2",
        "question": "Welche unterschiedlichen Positionen vertraten die Parteien im Jahr 2017 zum Thema Fachkräfteeinwanderungsgesetz?",
        "desc": "2017年各党派专业人才移民法立场",
        "type": "对比类"
    },
    {
        "id": "Q3",
        "question": "Wie war die Position der Grünen zur Migrationsfrage im Jahr 2015?",
        "desc": "2015年绿党移民问题立场",
        "type": "总结类"
    },
    {
        "id": "Q4",
        "question": "Wie wurde das Thema Familiennachzug für Flüchtlinge zwischen 2015 und 2018 im Bundestag diskutiert?",
        "desc": "2015-2018难民家庭团聚讨论",
        "type": "变化类"
    },
    {
        "id": "Q5",
        "question": "Vergleichen Sie die Integrationspolitik der Unionsparteien und der Grünen zwischen 2015 und 2017.",
        "desc": "2015-2017联盟党与绿党融合政策对比",
        "type": "对比类"
    },
    {
        "id": "Q6",
        "question": "Wie hat sich die Migrationspolitik der CDU/CSU zwischen 2017 und 2019 entwickelt?",
        "desc": "2017-2019 CDU/CSU移民政策变化",
        "type": "变化类"
    },
    {
        "id": "Q7",
        "question": "Welche Position vertrat die AfD im Jahr 2018 zur Flüchtlingspolitik?",
        "desc": "2018年AfD难民政策观点",
        "type": "总结类"
    }
]


def get_current_time_str() -> str:
    """获取当前UTC+8时间字符串"""
    return datetime.now(UTC_PLUS_8).strftime("%Y-%m-%d %H:%M:%S")


def check_api_health() -> Dict[str, Any]:
    """检查API服务健康状态（与Streamlit相同）"""
    try:
        response = requests.get(f"{API_URL}/api/v1/health", timeout=10)
        if response.status_code == 200:
            return {"healthy": True, "data": response.json()}
        else:
            return {"healthy": False, "error": f"HTTP {response.status_code}"}
    except requests.exceptions.ConnectionError:
        return {"healthy": False, "error": "无法连接到API服务"}
    except requests.exceptions.Timeout:
        return {"healthy": False, "error": "API服务响应超时"}
    except Exception as e:
        return {"healthy": False, "error": str(e)}


def call_api(question: str, deep_thinking: bool = False, verbose: bool = True) -> Dict[str, Any]:
    """
    调用API进行问答（使用异步轮询模式，与Streamlit完全相同）

    Args:
        question: 用户问题
        deep_thinking: 是否启用深度分析模式
        verbose: 是否显示轮询进度

    Returns:
        API响应结果
    """
    try:
        # 步骤1: 提交异步任务
        submit_endpoint = f"{API_URL}/api/v1/ask/async"
        payload = {
            "question": question,
            "deep_thinking": deep_thinking
        }

        submit_response = requests.post(
            submit_endpoint,
            json=payload,
            timeout=30
        )

        if submit_response.status_code != 200:
            return {
                "success": False,
                "error": f"提交任务失败: HTTP {submit_response.status_code}",
                "detail": submit_response.text
            }

        job_data = submit_response.json()
        job_id = job_data.get("job_id")

        if not job_id:
            return {"success": False, "error": "服务器未返回任务ID"}

        if verbose:
            print(f"  任务已提交 (ID: {job_id})，轮询中...", end="", flush=True)

        # 步骤2: 轮询任务状态
        status_endpoint = f"{API_URL}/api/v1/jobs/{job_id}"
        poll_interval = 3
        max_polls = API_TIMEOUT // poll_interval

        for poll_count in range(max_polls):
            time.sleep(poll_interval)

            try:
                status_response = requests.get(status_endpoint, timeout=10)

                if status_response.status_code != 200:
                    continue

                status_data = status_response.json()
                job_status = status_data.get("status")

                if verbose and poll_count % 10 == 0:
                    print(".", end="", flush=True)

                if job_status == "completed":
                    if verbose:
                        print(" 完成!")
                    result = status_data.get("result")
                    if result:
                        return {"success": True, "data": result}
                    else:
                        return {"success": False, "error": "任务完成但无结果返回"}

                elif job_status == "failed":
                    if verbose:
                        print(" 失败!")
                    error_msg = status_data.get("error", "未知错误")
                    return {"success": False, "error": f"任务失败: {error_msg}"}

            except requests.exceptions.RequestException:
                continue

        if verbose:
            print(" 超时!")
        return {"success": False, "error": f"任务超时（{API_TIMEOUT}秒）"}

    except requests.exceptions.Timeout:
        return {"success": False, "error": "提交任务超时"}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "无法连接到API服务"}
    except Exception as e:
        return {"success": False, "error": f"请求失败: {str(e)}"}


def test_single_question(q: Dict[str, str], index: int, total: int) -> Dict[str, Any]:
    """测试单个问题"""
    print(f"\n{'='*70}")
    print(f"[{index}/{total}] 测试 {q['id']}: {q['desc']}")
    print(f"类型: {q['type']}")
    print(f"问题: {q['question'][:80]}...")
    print(f"开始时间: {get_current_time_str()}")
    print("-" * 70)

    start_time = time.time()
    result = call_api(q["question"], deep_thinking=False)
    elapsed = time.time() - start_time

    test_result = {
        "id": q["id"],
        "desc": q["desc"],
        "type": q["type"],
        "question": q["question"],
        "success": result.get("success", False),
        "time": round(elapsed),
        "sub_q": 0,
        "sources": 0,
        "answer_len": 0,
        "years": [],
        "error": None
    }

    if result.get("success"):
        data = result.get("data", {})
        answer = data.get("answer", "")
        metadata = data.get("metadata", {})

        test_result["sub_q"] = metadata.get("sub_questions_count", 0)
        test_result["sources"] = metadata.get("total_sources", 0)
        test_result["answer_len"] = len(answer)
        test_result["years"] = metadata.get("years_covered", [])

        print(f"✓ 成功 | 耗时: {elapsed:.1f}秒")
        print(f"  子问题: {test_result['sub_q']} | 来源: {test_result['sources']} | 答案长度: {test_result['answer_len']}")
        if test_result["years"]:
            print(f"  覆盖年份: {', '.join(test_result['years'])}")
    else:
        test_result["error"] = result.get("error", "未知错误")
        print(f"✗ 失败 | 耗时: {elapsed:.1f}秒")
        print(f"  错误: {test_result['error']}")

    return test_result


def run_tests(question_indices: Optional[List[int]] = None) -> Dict[str, Any]:
    """
    运行测试

    Args:
        question_indices: 要测试的问题索引列表（1-7），None表示测试全部
    """
    print("=" * 70)
    print("Streamlit 调用方式模拟测试")
    print("=" * 70)
    print(f"API地址: {API_URL}")
    print(f"超时设置: {API_TIMEOUT}秒 ({API_TIMEOUT/60:.1f}分钟)")
    print(f"测试时间: {get_current_time_str()}")

    # 检查API健康状态
    print("\n检查API服务状态...")
    health = check_api_health()
    if not health.get("healthy"):
        print(f"✗ API服务不可用: {health.get('error')}")
        print("请先启动API服务: python api_server.py")
        sys.exit(1)
    print(f"✓ API服务正常")

    # 确定要测试的问题
    if question_indices:
        questions_to_test = []
        for idx in question_indices:
            if 1 <= idx <= 7:
                questions_to_test.append(STANDARD_QUESTIONS[idx - 1])
            else:
                print(f"警告: 忽略无效的问题索引 {idx}（有效范围: 1-7）")
        if not questions_to_test:
            print("错误: 没有有效的问题可测试")
            sys.exit(1)
    else:
        questions_to_test = STANDARD_QUESTIONS

    print(f"\n将测试 {len(questions_to_test)} 个问题")

    # 运行测试
    results = []
    total_start = time.time()

    for i, q in enumerate(questions_to_test, 1):
        result = test_single_question(q, i, len(questions_to_test))
        results.append(result)

    total_time = time.time() - total_start

    # 生成报告
    report = generate_report(results, total_time)

    return report


def generate_report(results: List[Dict], total_time: float) -> Dict[str, Any]:
    """生成测试报告"""
    success_count = sum(1 for r in results if r["success"])

    print("\n")
    print("=" * 70)
    print("测试报告")
    print("=" * 70)

    # 表格输出
    print(f"\n{'ID':<6}{'描述':<35}{'成功':<6}{'时间':<10}{'子问题':<8}{'来源':<8}{'答案长度':<10}")
    print("-" * 90)

    for r in results:
        status = "✓" if r["success"] else "✗"
        time_str = f"{r['time']}秒"
        print(f"{r['id']:<6}{r['desc']:<35}{status:<6}{time_str:<10}{r['sub_q']:<8}{r['sources']:<8}{r['answer_len']:<10}")

    print("-" * 90)
    print(f"成功率: {success_count}/{len(results)} | 总耗时: {total_time:.1f}秒 ({total_time/60:.1f}分钟)")

    if success_count == len(results):
        print("\n🎉 所有测试通过！")
    else:
        failed = [r["id"] for r in results if not r["success"]]
        print(f"\n⚠️ 失败的测试: {', '.join(failed)}")

    # 构建完整报告
    report = {
        "test_time": get_current_time_str(),
        "api_url": API_URL,
        "api_timeout": API_TIMEOUT,
        "total_questions": len(results),
        "success_count": success_count,
        "total_time_sec": round(total_time),
        "avg_time_sec": round(total_time / len(results), 2) if results else 0,
        "results": results
    }

    # 保存报告到文件
    report_file = project_root / "test_streamlit_simulation_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n报告已保存到: {report_file}")

    return report


def main():
    parser = argparse.ArgumentParser(
        description="模拟 Streamlit 调用方式测试 API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python test_streamlit_simulation.py              # 测试所有7个问题
    python test_streamlit_simulation.py -q 1         # 只测试Q1
    python test_streamlit_simulation.py -q 1 3 7     # 测试Q1、Q3、Q7
    python test_streamlit_simulation.py --list       # 列出所有问题
        """
    )
    parser.add_argument(
        "-q", "--question",
        type=int,
        nargs="+",
        metavar="N",
        help="要测试的问题编号（1-7），可指定多个"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="列出所有测试问题"
    )

    args = parser.parse_args()

    if args.list:
        print("标准测试问题列表:")
        print("-" * 80)
        for i, q in enumerate(STANDARD_QUESTIONS, 1):
            print(f"{i}. [{q['id']}] {q['desc']} ({q['type']})")
            print(f"   {q['question']}")
            print()
        return

    run_tests(args.question)


if __name__ == "__main__":
    main()
