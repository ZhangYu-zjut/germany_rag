"""
优化版Pinecone Metadata批量更新器
使用多线程并发加速，预计5-10分钟完成17万向量的metadata更新
"""

import json
import os
import time
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed
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


class OptimizedMetadataUpdater:
    """优化版Pinecone Metadata批量更新器（多线程）"""

    def __init__(self, max_workers: int = 20):
        """
        初始化Pinecone连接

        Args:
            max_workers: 并发线程数，默认20
        """
        api_key = os.getenv('PINECONE_VECTOR_DATABASE_API_KEY')
        self.pc = Pinecone(api_key=api_key)
        self.index = self.pc.Index('german-bge')
        self.max_workers = max_workers

        # 加载原始JSON数据缓存
        self.data_cache = {}  # {year: {text_id: metadata}}

        logger.info(f"✅ Pinecone连接初始化成功 (并发线程: {max_workers})")

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

    def update_single_vector(
        self,
        vector_id: str,
        original_text_id: str,
        year: int
    ) -> tuple[bool, str]:
        """
        更新单个向量的metadata（线程安全）

        Args:
            vector_id: Pinecone向量ID
            original_text_id: 原始文本ID
            year: 年份

        Returns:
            (是否成功, 错误信息)
        """
        try:
            # 查找原始metadata
            year_data = self.data_cache.get(year, {})

            if not year_data:
                return False, f"年份{year}数据未加载"

            if original_text_id not in year_data:
                return False, f"未找到原始metadata: {original_text_id}"

            original_meta = year_data[original_text_id]

            # 构建新的metadata字段（只更新4个新字段）
            new_fields = {
                'month': original_meta.get('month', '01'),
                'day': original_meta.get('day', '01'),
                'id': original_meta.get('id', original_text_id),
                'source_reference': self.format_source_reference(original_meta)
            }

            # 使用Pinecone的update方法更新metadata
            self.index.update(
                id=vector_id,
                set_metadata=new_fields
            )

            return True, ""

        except Exception as e:
            return False, str(e)

    def get_all_vectors_for_year(self, year: int) -> List[tuple]:
        """
        获取某年所有向量的ID和original_text_id (使用list API分页获取)

        Returns:
            [(vector_id, original_text_id), ...]
        """
        logger.info(f"📊 查询{year}年的所有向量...")

        all_vectors = []

        try:
            # 使用list()方法分页获取所有向量ID
            # list()返回一个generator，每次yield一个字符串列表（100个ID）
            page_count = 0

            for id_batch in self.index.list(prefix=f'{year}_'):
                page_count += 1

                # id_batch是一个字符串列表，例如: ['2016_xxx_0', '2016_xxx_1', ...]
                if not id_batch:
                    break

                # Fetch这批向量的metadata
                fetch_result = self.index.fetch(ids=id_batch)

                # 提取original_text_id
                for vec_id in id_batch:
                    if vec_id in fetch_result.vectors:
                        vec = fetch_result.vectors[vec_id]
                        original_text_id = vec.metadata.get('original_text_id')

                        if original_text_id:
                            all_vectors.append((vec_id, original_text_id))

                # 每10页显示一次进度
                if page_count % 10 == 0:
                    logger.info(f"  已获取 {page_count} 页，共 {len(all_vectors)} 个向量...")

            logger.info(f"✅ {year}年共找到 {len(all_vectors)} 个向量 (分{page_count}页)")
            return all_vectors

        except Exception as e:
            logger.error(f"❌ 查询{year}年向量失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    def update_year_metadata_parallel(self, year: int) -> Dict:
        """
        使用多线程并发更新某一年所有向量的metadata

        Args:
            year: 年份

        Returns:
            统计信息
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"🔧 开始更新{year}年metadata (并发模式)")
        logger.info(f"{'='*60}")

        start_time = time.time()

        # 1. 预加载该年份的原始数据
        year_data = self.load_year_data(year)
        if not year_data:
            logger.warning(f"⚠️ {year}年无数据，跳过")
            return {"year": year, "updated": 0, "failed": 0, "total": 0}

        # 2. 获取所有向量
        vectors = self.get_all_vectors_for_year(year)
        total_vectors = len(vectors)

        if total_vectors == 0:
            logger.warning(f"⚠️ {year}年无向量数据")
            return {"year": year, "updated": 0, "failed": 0, "total": 0}

        # 3. 多线程并发更新
        logger.info(f"🚀 启动{self.max_workers}个并发线程进行更新...")

        updated_count = 0
        failed_count = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_vector = {
                executor.submit(
                    self.update_single_vector,
                    vector_id,
                    original_text_id,
                    year
                ): (vector_id, original_text_id)
                for vector_id, original_text_id in vectors
            }

            # 收集结果并显示进度
            for i, future in enumerate(as_completed(future_to_vector), 1):
                success, error_msg = future.result()

                if success:
                    updated_count += 1
                else:
                    failed_count += 1
                    if failed_count <= 5:  # 只显示前5个错误
                        vector_id, _ = future_to_vector[future]
                        logger.debug(f"  更新失败 {vector_id}: {error_msg}")

                # 每100个显示一次进度
                if i % 100 == 0 or i == total_vectors:
                    progress = i / total_vectors * 100
                    logger.info(
                        f"  进度: {i}/{total_vectors} ({progress:.1f}%) - "
                        f"成功: {updated_count}, 失败: {failed_count}"
                    )

        elapsed_time = time.time() - start_time

        logger.info(f"\n✅ {year}年metadata更新完成")
        logger.info(f"   总向量数: {total_vectors}")
        logger.info(f"   成功更新: {updated_count}")
        logger.info(f"   失败: {failed_count}")
        logger.info(f"   耗时: {elapsed_time:.1f}秒 ({elapsed_time/60:.1f}分钟)")
        logger.info(f"   速度: {total_vectors/elapsed_time:.1f} 向量/秒")

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

        success_count = 0
        for i, match in enumerate(results.matches, 1):
            meta = match.metadata

            month = meta.get('month')
            day = meta.get('day')
            doc_id = meta.get('id')
            source_ref = meta.get('source_reference')

            logger.info(f"样本 {i}:")
            logger.info(f"  ID: {match.id[:40]}...")
            logger.info(f"  month: {month} (type: {type(month).__name__})")
            logger.info(f"  day: {day} (type: {type(day).__name__})")
            logger.info(f"  id: {doc_id}")
            logger.info(f"  source_reference: {source_ref[:60] if source_ref else 'None'}...")

            # 检查是否成功更新
            if month and day and doc_id and source_ref:
                logger.info(f"  ✅ 更新成功\n")
                success_count += 1
            else:
                logger.warning(f"  ⚠️ 更新不完整\n")

        logger.info(f"验证成功率: {success_count}/{len(results.matches)} ({success_count/len(results.matches)*100:.1f}%)")


def main():
    """主函数"""
    logger.info("="*60)
    logger.info("Pinecone Metadata批量更新工具（优化版）")
    logger.info("="*60)
    logger.info("\n功能: 使用多线程并发更新metadata")
    logger.info("优势: 5-10分钟完成17万向量更新\n")

    # 创建更新器（20个并发线程）
    updater = OptimizedMetadataUpdater(max_workers=20)

    # 要更新的年份
    years_to_update = [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024]

    total_start = time.time()
    all_stats = []

    for year in years_to_update:
        stats = updater.update_year_metadata_parallel(year)
        all_stats.append(stats)

        # 验证前3年的更新结果
        if year <= 2017:
            # 等待3秒让Pinecone同步
            logger.info(f"\n⏳ 等待3秒让Pinecone同步数据...")
            time.sleep(3)
            updater.verify_update(year, sample_size=3)

    total_time = time.time() - total_start

    # 总结
    logger.info(f"\n{'='*60}")
    logger.info(f"📊 所有年份更新完成")
    logger.info(f"{'='*60}\n")

    total_updated = sum(s['updated'] for s in all_stats)
    total_failed = sum(s['failed'] for s in all_stats)
    total_vectors = sum(s['total'] for s in all_stats)

    logger.info(f"总向量数: {total_vectors:,}")
    logger.info(f"成功更新: {total_updated:,}")
    logger.info(f"失败: {total_failed:,}")
    logger.info(f"成功率: {total_updated/total_vectors*100:.2f}%")
    logger.info(f"总耗时: {total_time:.1f}秒 ({total_time/60:.1f}分钟)")
    logger.info(f"平均速度: {total_vectors/total_time:.1f} 向量/秒")
    logger.info(f"\n年份详情:")

    for stats in all_stats:
        logger.info(f"  {stats['year']}: {stats['updated']}/{stats['total']} 成功 ({stats['time']:.1f}秒)")


if __name__ == "__main__":
    main()
