"""
智能批量更新Pinecone metadata
只更新4个新增字段：month, day, id, source_reference
不重新计算embeddings，保持向量不变
"""

import json
import os
import time
from typing import Dict, List
from pinecone import Pinecone
from dotenv import load_dotenv
from loguru import logger

# 配置logger
logger.remove()
logger.add(
    lambda msg: print(msg, end=''),
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level:8}</level> | <level>{message}</level>",
    level="INFO"
)

load_dotenv()


class MetadataUpdater:
    """Pinecone Metadata批量更新器"""

    def __init__(self):
        """初始化Pinecone连接"""
        api_key = os.getenv('PINECONE_VECTOR_DATABASE_API_KEY')
        self.pc = Pinecone(api_key=api_key)
        self.index = self.pc.Index('german-bge')

        # 加载原始JSON数据
        self.data_cache = {}  # {year: {text_id: metadata}}

        logger.info("✅ Pinecone连接初始化成功")

    def load_year_data(self, year: int) -> Dict:
        """
        加载某一年的原始JSON数据

        Returns:
            {text_id: metadata} 的映射
        """
        if year in self.data_cache:
            return self.data_cache[year]

        json_file = f'data/pp_json_49-21/pp_{year}.json'

        if not os.path.exists(json_file):
            logger.warning(f"⚠️ {year}年数据文件不存在: {json_file}")
            return {}

        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 构建 text_id -> metadata 映射
            text_id_map = {}
            if 'transcript' in data:
                for item in data['transcript']:
                    if item.get('type') == 'text_block':
                        text_id = item.get('text_id')
                        metadata = item.get('metadata', {})
                        if text_id and metadata:
                            text_id_map[text_id] = metadata

            self.data_cache[year] = text_id_map
            logger.info(f"📚 加载{year}年数据: {len(text_id_map)}条记录")

            return text_id_map

        except Exception as e:
            logger.error(f"❌ 加载{year}年数据失败: {str(e)}")
            return {}

    def extract_info_from_vector_id(self, vector_id: str) -> tuple:
        """
        从向量ID中提取year和original_text_id

        向量ID格式: "2017_1762423575_2477_chunk_0"
        提取: year=2017

        需要从metadata中的original_text_id获取真实的text_id
        """
        parts = vector_id.split('_')
        if len(parts) >= 1:
            try:
                year = int(parts[0])
                return year, None
            except:
                pass

        return None, None

    def format_source_reference(self, metadata: Dict) -> str:
        """
        格式化source_reference: "id | speaker | year-month-day"
        """
        doc_id = metadata.get('id', 'unknown')
        speaker = metadata.get('speaker', 'Unknown')
        year = metadata.get('year', '0000')
        month = metadata.get('month', '01')
        day = metadata.get('day', '01')

        return f"{doc_id} | {speaker} | {year}-{month}-{day}"

    def update_vector_metadata(
        self,
        vector_id: str,
        original_text_id: str,
        year: int
    ) -> bool:
        """
        更新单个向量的metadata

        Args:
            vector_id: Pinecone向量ID
            original_text_id: 原始文本ID (从当前metadata中获取)
            year: 年份

        Returns:
            是否更新成功
        """
        # 加载该年份的原始数据
        year_data = self.load_year_data(year)

        if not year_data:
            logger.warning(f"⚠️ {year}年数据为空，跳过向量 {vector_id}")
            return False

        # 查找对应的原始metadata
        if original_text_id not in year_data:
            logger.debug(f"  未找到原始metadata: {original_text_id}")
            return False

        original_meta = year_data[original_text_id]

        # 构建新的metadata字段（只更新4个新字段）
        new_fields = {
            'month': original_meta.get('month', '01'),
            'day': original_meta.get('day', '01'),
            'id': original_meta.get('id', original_text_id),
            'source_reference': self.format_source_reference(original_meta)
        }

        # 使用Pinecone的update方法更新metadata
        try:
            self.index.update(
                id=vector_id,
                set_metadata=new_fields
            )
            return True

        except Exception as e:
            logger.error(f"❌ 更新失败 {vector_id}: {str(e)}")
            return False

    def update_year_metadata(self, year: int, batch_size: int = 100) -> Dict:
        """
        更新某一年所有向量的metadata

        Args:
            year: 年份
            batch_size: 批处理大小

        Returns:
            统计信息
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"🔧 开始更新{year}年metadata")
        logger.info(f"{'='*60}")

        start_time = time.time()

        # 预加载该年份的原始数据
        year_data = self.load_year_data(year)
        if not year_data:
            logger.warning(f"⚠️ {year}年无数据，跳过")
            return {"year": year, "updated": 0, "failed": 0, "total": 0}

        # 查询该年份的所有向量
        logger.info(f"📊 查询{year}年的所有向量...")

        # 使用filter查询获取该年份所有向量
        try:
            # Pinecone不支持直接获取所有ID，我们使用query + filter的方式
            dummy_vector = [0.0] * 1024
            results = self.index.query(
                vector=dummy_vector,
                top_k=10000,  # Pinecone限制
                filter={'year': {'$eq': str(year)}},
                include_metadata=True
            )

            vectors = results.matches
            total_vectors = len(vectors)

            logger.info(f"✅ 找到{total_vectors}个向量")

        except Exception as e:
            logger.error(f"❌ 查询{year}年向量失败: {str(e)}")
            return {"year": year, "updated": 0, "failed": 0, "total": 0}

        if total_vectors == 0:
            logger.warning(f"⚠️ {year}年无向量数据")
            return {"year": year, "updated": 0, "failed": 0, "total": 0}

        # 批量更新
        updated_count = 0
        failed_count = 0

        for i, match in enumerate(vectors):
            vector_id = match.id
            metadata = match.metadata

            # 从metadata中获取original_text_id
            original_text_id = metadata.get('original_text_id')

            if not original_text_id:
                logger.debug(f"  向量 {vector_id} 缺少original_text_id，跳过")
                failed_count += 1
                continue

            # 更新metadata
            success = self.update_vector_metadata(vector_id, original_text_id, year)

            if success:
                updated_count += 1
            else:
                failed_count += 1

            # 显示进度
            if (i + 1) % 100 == 0:
                progress = (i + 1) / total_vectors * 100
                logger.info(f"  进度: {i+1}/{total_vectors} ({progress:.1f}%) - 成功: {updated_count}, 失败: {failed_count}")

        elapsed_time = time.time() - start_time

        logger.info(f"\n✅ {year}年metadata更新完成")
        logger.info(f"   总向量数: {total_vectors}")
        logger.info(f"   成功更新: {updated_count}")
        logger.info(f"   失败: {failed_count}")
        logger.info(f"   耗时: {elapsed_time:.1f}秒")

        return {
            "year": year,
            "total": total_vectors,
            "updated": updated_count,
            "failed": failed_count,
            "time": elapsed_time
        }

    def verify_update(self, year: int, sample_size: int = 5):
        """
        验证更新结果

        Args:
            year: 年份
            sample_size: 抽样数量
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"🔍 验证{year}年metadata更新结果")
        logger.info(f"{'='*60}")

        # 查询几个样本
        dummy_vector = [0.0] * 1024
        results = self.index.query(
            vector=dummy_vector,
            top_k=sample_size,
            filter={'year': {'$eq': str(year)}},
            include_metadata=True
        )

        logger.info(f"\n抽样检查 {len(results.matches)} 个向量:\n")

        for i, match in enumerate(results.matches, 1):
            meta = match.metadata

            month = meta.get('month')
            day = meta.get('day')
            doc_id = meta.get('id')
            source_ref = meta.get('source_reference')

            logger.info(f"样本 {i}:")
            logger.info(f"  ID: {match.id[:30]}...")
            logger.info(f"  month: {month} (type: {type(month).__name__})")
            logger.info(f"  day: {day} (type: {type(day).__name__})")
            logger.info(f"  id: {doc_id}")
            logger.info(f"  source_reference: {source_ref[:60] if source_ref else 'None'}...")

            # 检查是否成功更新
            if month and day and doc_id and source_ref:
                logger.info(f"  ✅ 更新成功\n")
            else:
                logger.warning(f"  ⚠️ 更新不完整\n")


def main():
    """主函数"""
    logger.info("="*60)
    logger.info("Pinecone Metadata批量更新工具")
    logger.info("="*60)
    logger.info("\n功能: 更新4个新字段 (month, day, id, source_reference)")
    logger.info("优势: 不重新计算embeddings，保持向量不变\n")

    updater = MetadataUpdater()

    # 要更新的年份
    years_to_update = [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024]

    total_start = time.time()
    all_stats = []

    for year in years_to_update:
        stats = updater.update_year_metadata(year)
        all_stats.append(stats)

        # 验证前3年的更新结果
        if year <= 2017:
            updater.verify_update(year)

    total_time = time.time() - total_start

    # 总结
    logger.info(f"\n{'='*60}")
    logger.info(f"📊 所有年份更新完成")
    logger.info(f"{'='*60}\n")

    total_updated = sum(s['updated'] for s in all_stats)
    total_failed = sum(s['failed'] for s in all_stats)
    total_vectors = sum(s['total'] for s in all_stats)

    logger.info(f"总向量数: {total_vectors}")
    logger.info(f"成功更新: {total_updated}")
    logger.info(f"失败: {total_failed}")
    logger.info(f"成功率: {total_updated/total_vectors*100:.2f}%")
    logger.info(f"总耗时: {total_time:.1f}秒 ({total_time/60:.1f}分钟)")
    logger.info(f"\n年份详情:")

    for stats in all_stats:
        logger.info(f"  {stats['year']}: {stats['updated']}/{stats['total']} 成功")


if __name__ == "__main__":
    main()
