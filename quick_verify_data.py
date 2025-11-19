#!/usr/bin/env python3
"""
快速验证Pinecone数据
只做基本检查，避免大量查询导致超时
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import json

# 加载环境变量
project_root = Path(__file__).parent
sys.path.append(str(project_root))
load_dotenv(project_root / ".env", override=True)

from pinecone import Pinecone
from src.utils.logger import setup_logger

logger = setup_logger()


def quick_verify():
    """快速验证每年数据"""
    logger.info("=" * 80)
    logger.info("🔍 快速验证Pinecone数据")
    logger.info("=" * 80)

    # 连接Pinecone
    pc = Pinecone(api_key=os.getenv("PINECONE_VECTOR_DATABASE_API_KEY"))
    index = pc.Index("german-bge")

    # 1. 总体统计
    stats = index.describe_index_stats()
    total_vectors = stats.get("total_vector_count", 0)
    logger.info(f"\n📊 总向量数: {total_vectors:,}\n")

    # 2. 按年份快速检查（每年只查1个样本）
    logger.info("📅 按年份检查:")
    logger.info("-" * 80)

    results = {}

    for year in range(2015, 2026):
        year_str = str(year)

        try:
            # 只查询1个样本来验证数据存在
            result = index.query(
                vector=[0.01] * 1024,
                top_k=1,
                filter={"year": {"$eq": year_str}},
                include_metadata=True
            )

            if result.matches:
                match = result.matches[0]
                metadata = match.metadata

                # 检查元数据完整性
                speaker = metadata.get("speaker", "")
                date = metadata.get("date", "")
                group = metadata.get("group", "")

                # 标记缺失字段
                missing = []
                if not speaker or speaker in ["未知", "Unknown"]:
                    missing.append("speaker")
                if not date or date in["未知", "Unknown"]:
                    missing.append("date")
                if not group or group in ["未知", "Unknown"]:
                    missing.append("group")

                status = "⚠️" if missing else "✅"
                missing_str = f" (缺失: {', '.join(missing)})" if missing else ""

                logger.info(f"  {status} {year_str}: 有数据 - {speaker or '未知'}, {date or '未知'}{missing_str}")

                results[year_str] = {
                    "has_data": True,
                    "sample_speaker": speaker or "未知",
                    "sample_date": date or "未知",
                    "sample_group": group or "未知",
                    "missing_fields": missing
                }
            else:
                logger.info(f"  ❌ {year_str}: 无数据")
                results[year_str] = {
                    "has_data": False
                }

        except Exception as e:
            logger.error(f"  ❌ {year_str}: 查询失败 - {str(e)}")
            results[year_str] = {
                "has_data": False,
                "error": str(e)
            }

    # 3. 专门检查2025年
    logger.info("\n" + "=" * 80)
    logger.info("🔍 2025年元数据详细检查")
    logger.info("=" * 80)

    try:
        result = index.query(
            vector=[0.01] * 1024,
            top_k=10,  # 查询10个样本
            filter={"year": {"$eq": "2025"}},
            include_metadata=True
        )

        if result.matches:
            logger.info(f"\n✅ 找到 {len(result.matches)} 个2025年样本\n")

            missing_speaker_count = 0
            missing_date_count = 0

            for i, match in enumerate(result.matches, 1):
                metadata = match.metadata
                speaker = metadata.get("speaker", "")
                date = metadata.get("date", "")
                group = metadata.get("group", "")
                text_preview = metadata.get("text", "")[:50]

                if not speaker or speaker in ["未知", "Unknown"]:
                    missing_speaker_count += 1
                if not date or date in ["未知", "Unknown"]:
                    missing_date_count += 1

                logger.info(f"样本 {i}:")
                logger.info(f"  ID: {match.id}")
                logger.info(f"  speaker: {speaker or '❌ 缺失'}")
                logger.info(f"  date: {date or '❌ 缺失'}")
                logger.info(f"  group: {group or '❌ 缺失'}")
                logger.info(f"  text: {text_preview}...")
                logger.info("")

            logger.info(f"统计:")
            logger.info(f"  缺失speaker: {missing_speaker_count}/10")
            logger.info(f"  缺失date: {missing_date_count}/10")

            results["2025_detail"] = {
                "sample_count": len(result.matches),
                "missing_speaker_ratio": f"{missing_speaker_count}/10",
                "missing_date_ratio": f"{missing_date_count}/10"
            }

        else:
            logger.error("❌ 2025年无数据")

    except Exception as e:
        logger.error(f"❌ 2025年查询失败: {str(e)}")

    # 4. 检查原始2025数据文件
    logger.info("\n" + "=" * 80)
    logger.info("📁 检查2025年原始数据文件")
    logger.info("=" * 80)

    data_file = project_root / "data" / "pp_json_49-21" / "pp_2025.json"
    if data_file.exists():
        logger.info(f"\n✅ 找到文件: {data_file}")

        try:
            with open(data_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            logger.info(f"原始记录数: {len(data)}")

            if data:
                logger.info("\n前3条记录的元数据:")
                for i, record in enumerate(data[:3], 1):
                    logger.info(f"\n记录 {i}:")
                    logger.info(f"  speaker: {record.get('speaker', '❌ 缺失')}")
                    logger.info(f"  date: {record.get('date', '❌ 缺失')}")
                    logger.info(f"  group: {record.get('group', '❌ 缺失')}")
                    logger.info(f"  text长度: {len(record.get('text', ''))} 字符")

                # 统计缺失情况
                missing_speaker = sum(1 for r in data if not r.get('speaker'))
                missing_date = sum(1 for r in data if not r.get('date'))

                logger.info(f"\n原始数据缺失统计:")
                logger.info(f"  缺失speaker: {missing_speaker}/{len(data)}")
                logger.info(f"  缺失date: {missing_date}/{len(data)}")

                results["2025_source_file"] = {
                    "total_records": len(data),
                    "missing_speaker": missing_speaker,
                    "missing_date": missing_date
                }

        except Exception as e:
            logger.error(f"❌ 读取文件失败: {str(e)}")
    else:
        logger.error(f"❌ 未找到文件: {data_file}")

    # 5. 保存结果
    output_file = project_root / "quick_verification_report.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "total_vectors": total_vectors,
            "year_check": results
        }, f, ensure_ascii=False, indent=2)

    logger.info(f"\n✅ 验证报告已保存: {output_file}")

    # 6. 总结
    logger.info("\n" + "=" * 80)
    logger.info("📊 验证总结")
    logger.info("=" * 80)

    years_with_data = sum(1 for r in results.values() if isinstance(r, dict) and r.get("has_data"))
    years_with_issues = sum(1 for r in results.values() if isinstance(r, dict) and r.get("missing_fields"))

    logger.info(f"\n有数据的年份: {years_with_data}/11")
    if years_with_issues > 0:
        logger.warning(f"⚠️  有元数据缺失的年份: {years_with_issues}")
    else:
        logger.info(f"✅ 所有年份元数据完整")


if __name__ == "__main__":
    try:
        quick_verify()
        logger.info("\n✅ 快速验证完成\n")
    except Exception as e:
        logger.error(f"❌ 验证失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        exit(1)
