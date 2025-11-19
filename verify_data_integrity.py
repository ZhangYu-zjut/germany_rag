#!/usr/bin/env python3
"""
验证Pinecone数据的完整性、准确性和一致性
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import json
from collections import defaultdict
import time

# 加载环境变量
project_root = Path(__file__).parent
sys.path.append(str(project_root))
load_dotenv(project_root / ".env", override=True)

from pinecone import Pinecone
from src.utils.logger import setup_logger

logger = setup_logger()


def get_year_statistics(index, year: str, sample_size: int = 1000):
    """
    获取某年的统计信息
    由于Pinecone的top_k限制，使用采样方法估算
    """
    try:
        # 尝试获取尽可能多的样本
        result = index.query(
            vector=[0.01] * 1024,
            top_k=10000,  # Pinecone最大限制
            filter={"year": {"$eq": year}},
            include_metadata=True
        )

        if not result.matches:
            return {
                "year": year,
                "count": 0,
                "metadata_issues": [],
                "sample_metadata": []
            }

        # 分析元数据完整性
        metadata_issues = []
        speakers = set()
        parties = set()
        dates = set()

        required_fields = ["speaker", "date", "group", "year", "month", "day"]

        for match in result.matches[:min(100, len(result.matches))]:  # 检查前100个
            metadata = match.metadata

            # 检查必需字段
            for field in required_fields:
                if field not in metadata or metadata[field] in [None, "", "未知", "Unknown"]:
                    metadata_issues.append({
                        "id": match.id,
                        "missing_field": field,
                        "metadata": metadata
                    })

            # 收集统计信息
            speakers.add(metadata.get("speaker", "未知"))
            parties.add(metadata.get("group", "未知"))
            dates.add(metadata.get("date", "未知"))

        return {
            "year": year,
            "sampled_count": len(result.matches),
            "estimated_total": len(result.matches),  # 如果<10000说明是准确数字
            "is_exact": len(result.matches) < 10000,
            "unique_speakers": len(speakers),
            "unique_parties": len(parties),
            "unique_dates": len(dates),
            "metadata_issues_count": len(metadata_issues),
            "metadata_issues_sample": metadata_issues[:5],  # 只保留前5个示例
            "sample_speakers": list(speakers)[:5],
            "sample_parties": list(parties)[:5],
            "sample_dates": list(dates)[:5]
        }

    except Exception as e:
        logger.error(f"获取{year}年统计失败: {str(e)}")
        return {
            "year": year,
            "error": str(e)
        }


def verify_metadata_consistency(index):
    """验证元数据一致性"""
    logger.info("\n" + "="*80)
    logger.info("🔍 验证Pinecone数据完整性")
    logger.info("="*80)

    # 1. 获取总体统计
    logger.info("\n📊 1. 总体统计")
    logger.info("-" * 40)

    stats = index.describe_index_stats()
    total_vectors = stats.get("total_vector_count", 0)
    logger.info(f"总向量数: {total_vectors:,}")

    # 2. 按年份统计
    logger.info("\n📊 2. 按年份详细统计")
    logger.info("-" * 40)

    year_stats = {}
    total_sampled = 0

    for year in range(2015, 2026):
        year_str = str(year)
        logger.info(f"\n正在分析 {year_str}年...")

        stat = get_year_statistics(index, year_str)
        year_stats[year_str] = stat

        if "error" in stat:
            logger.error(f"  ❌ {year_str}: {stat['error']}")
        else:
            count = stat.get("sampled_count", 0)
            total_sampled += count
            is_exact = stat.get("is_exact", False)

            logger.info(f"  {'✅' if count > 0 else '❌'} {year_str}: {count:,} vectors {'(精确)' if is_exact else '(采样)'}")
            logger.info(f"     唯一发言人: {stat['unique_speakers']}")
            logger.info(f"     唯一党派: {stat['unique_parties']}")
            logger.info(f"     唯一日期: {stat['unique_dates']}")

            if stat['metadata_issues_count'] > 0:
                logger.warning(f"     ⚠️  元数据问题: {stat['metadata_issues_count']} 个向量存在缺失字段")
                logger.warning(f"     示例缺失字段: {stat['metadata_issues_sample'][0]['missing_field'] if stat['metadata_issues_sample'] else 'N/A'}")

        time.sleep(0.5)  # 避免API速率限制

    # 3. 总结
    logger.info("\n" + "="*80)
    logger.info("📈 统计总结")
    logger.info("="*80)
    logger.info(f"Pinecone总向量数: {total_vectors:,}")
    logger.info(f"采样统计向量数: {total_sampled:,}")

    if total_sampled < total_vectors:
        logger.warning(f"⚠️  差异: {total_vectors - total_sampled:,} 个向量未被统计（可能超出查询限制）")

    # 4. 元数据问题汇总
    logger.info("\n" + "="*80)
    logger.info("🔍 元数据质量分析")
    logger.info("="*80)

    total_issues = sum(stat.get("metadata_issues_count", 0) for stat in year_stats.values() if "error" not in stat)

    if total_issues > 0:
        logger.warning(f"\n⚠️  发现 {total_issues} 个元数据问题")

        for year_str, stat in year_stats.items():
            if "error" not in stat and stat.get("metadata_issues_count", 0) > 0:
                logger.warning(f"\n{year_str}年问题示例:")
                for issue in stat["metadata_issues_sample"]:
                    logger.warning(f"  - ID: {issue['id']}")
                    logger.warning(f"    缺失字段: {issue['missing_field']}")
                    logger.warning(f"    元数据: {issue['metadata']}")
    else:
        logger.info("\n✅ 所有元数据质量良好，无缺失字段")

    # 5. 保存结果
    logger.info("\n" + "="*80)
    logger.info("💾 保存验证结果")
    logger.info("="*80)

    result = {
        "total_vectors": total_vectors,
        "total_sampled": total_sampled,
        "year_statistics": year_stats,
        "metadata_issues_total": total_issues
    }

    output_file = project_root / "data_integrity_report.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    logger.info(f"✅ 验证结果已保存到: {output_file}")

    return result


def investigate_2025_metadata_issue(index):
    """专门调查2025年元数据问题"""
    logger.info("\n" + "="*80)
    logger.info("🔍 深度调查2025年元数据异常")
    logger.info("="*80)

    # 获取2025年的样本数据
    result = index.query(
        vector=[0.01] * 1024,
        top_k=50,
        filter={"year": {"$eq": "2025"}},
        include_metadata=True
    )

    if not result.matches:
        logger.error("❌ 2025年无数据")
        return

    logger.info(f"\n获取到 {len(result.matches)} 个2025年样本")
    logger.info("-" * 40)

    # 分析元数据
    metadata_analysis = defaultdict(int)
    speaker_values = defaultdict(int)
    date_values = defaultdict(int)

    for i, match in enumerate(result.matches[:10], 1):  # 详细分析前10个
        metadata = match.metadata

        logger.info(f"\n样本 {i}:")
        logger.info(f"  ID: {match.id}")
        logger.info(f"  Score: {match.score:.4f}")
        logger.info(f"  元数据:")
        for key, value in metadata.items():
            logger.info(f"    {key}: {value}")

            # 统计缺失情况
            if value in [None, "", "未知", "Unknown"]:
                metadata_analysis[f"{key}_missing"] += 1

            if key == "speaker":
                speaker_values[str(value)] += 1
            if key == "date":
                date_values[str(value)] += 1

    # 统计分析
    logger.info("\n" + "="*80)
    logger.info("📊 2025年元数据统计")
    logger.info("="*80)

    all_speakers = set()
    all_dates = set()
    missing_speaker = 0
    missing_date = 0

    for match in result.matches:
        metadata = match.metadata
        speaker = metadata.get("speaker", "未知")
        date = metadata.get("date", "未知")

        all_speakers.add(speaker)
        all_dates.add(date)

        if speaker in [None, "", "未知", "Unknown"]:
            missing_speaker += 1
        if date in [None, "", "未知", "Unknown"]:
            missing_date += 1

    logger.info(f"\n唯一发言人数: {len(all_speakers)}")
    logger.info(f"发言人列表: {list(all_speakers)[:10]}")
    logger.info(f"缺失发言人的向量: {missing_speaker}/{len(result.matches)}")

    logger.info(f"\n唯一日期数: {len(all_dates)}")
    logger.info(f"日期列表: {list(all_dates)[:10]}")
    logger.info(f"缺失日期的向量: {missing_date}/{len(result.matches)}")

    # 检查原始数据文件
    logger.info("\n" + "="*80)
    logger.info("🔍 检查2025年原始数据文件")
    logger.info("="*80)

    data_file = project_root / "data" / "pp_json_49-21" / "pp_2025.json"
    if data_file.exists():
        logger.info(f"✅ 找到原始数据文件: {data_file}")

        try:
            with open(data_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            logger.info(f"原始数据记录数: {len(data)}")

            # 检查前几条记录
            logger.info("\n原始数据示例（前3条）:")
            for i, record in enumerate(data[:3], 1):
                logger.info(f"\n记录 {i}:")
                logger.info(f"  speaker: {record.get('speaker', '未知')}")
                logger.info(f"  date: {record.get('date', '未知')}")
                logger.info(f"  group: {record.get('group', '未知')}")
                logger.info(f"  text长度: {len(record.get('text', ''))}")

        except Exception as e:
            logger.error(f"❌ 读取原始数据失败: {str(e)}")
    else:
        logger.error(f"❌ 未找到原始数据文件: {data_file}")


if __name__ == "__main__":
    try:
        # 连接Pinecone
        logger.info("🔗 连接Pinecone...")
        pc = Pinecone(api_key=os.getenv("PINECONE_VECTOR_DATABASE_API_KEY"))
        index = pc.Index("german-bge")
        logger.info("✅ Pinecone连接成功\n")

        # 执行验证
        result = verify_metadata_consistency(index)

        # 专门调查2025年
        investigate_2025_metadata_issue(index)

        logger.info("\n" + "="*80)
        logger.info("✅ 数据完整性验证完成")
        logger.info("="*80)

    except Exception as e:
        logger.error(f"❌ 验证过程出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        exit(1)
