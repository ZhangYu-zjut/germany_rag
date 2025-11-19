"""
数据加载器模块
负责从JSON文件加载德国议会演讲数据
支持部分加载和全量加载
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from tqdm import tqdm

from src.config import settings
from src.utils import logger


class ParliamentDataLoader:
    """
    德国议会数据加载器
    
    功能:
    1. 从JSON文件加载演讲数据
    2. 提取和清洗metadata
    3. 支持按年份过滤(PART模式)
    4. 支持全量加载(ALL模式)
    """
    
    def __init__(
        self,
        data_dir: Optional[str] = None,
        data_mode: Optional[str] = None,
        years: Optional[List[str]] = None
    ):
        """
        初始化数据加载器
        
        Args:
            data_dir: 数据目录路径,默认从配置读取
            data_mode: 数据模式(PART/ALL),默认从配置读取
            years: 要加载的年份列表,仅在PART模式下有效
        """
        self.data_dir = Path(data_dir or settings.data_dir)
        self.data_mode = data_mode or settings.data_mode
        self.years = years or settings.part_data_years_list
        
        logger.info(f"初始化数据加载器: 模式={self.data_mode}, 目录={self.data_dir}")
        
        if self.data_mode == "PART":
            logger.info(f"部分数据模式: 年份={self.years}")
    
    def load_data(self) -> List[Dict[str, Any]]:
        """
        根据配置加载数据
        
        Returns:
            包含所有speech数据的列表,每条数据包含metadata和speech内容
        """
        if self.data_mode == "PART":
            return self._load_partial_data()
        else:
            return self._load_all_data()
    
    def _load_partial_data(self) -> List[Dict[str, Any]]:
        """
        加载部分年份的数据
        
        Returns:
            指定年份的所有speech数据
        """
        all_data = []
        
        logger.info(f"开始加载部分数据: {len(self.years)}个年份")
        
        for year in self.years:
            file_path = self.data_dir / f"pp_{year}.json"
            
            if not file_path.exists():
                logger.warning(f"文件不存在: {file_path}")
                continue
            
            logger.info(f"加载文件: {file_path}")
            data = self._load_json_file(file_path)
            all_data.extend(data)
        
        logger.success(f"部分数据加载完成: 共{len(all_data)}条记录")
        return all_data
    
    def _load_all_data(self) -> List[Dict[str, Any]]:
        """
        加载所有年份的数据
        
        Returns:
            所有年份的speech数据
        """
        all_data = []
        
        # 获取所有JSON文件
        json_files = sorted(self.data_dir.glob("pp_*.json"))
        
        if not json_files:
            logger.error(f"未找到任何JSON文件: {self.data_dir}")
            return []
        
        logger.info(f"开始加载全量数据: {len(json_files)}个文件")
        
        for file_path in tqdm(json_files, desc="加载JSON文件"):
            logger.debug(f"加载文件: {file_path}")
            data = self._load_json_file(file_path)
            all_data.extend(data)
        
        logger.success(f"全量数据加载完成: 共{len(all_data)}条记录")
        return all_data
    
    def _load_json_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        加载单个JSON文件并提取speech数据
        
        Args:
            file_path: JSON文件路径
        
        Returns:
            该文件中所有speech数据,每条数据包含:
            - metadata: 元数据(year, speaker, group等)
            - speech: 演讲内容
            - file: 文件名
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            speeches = []
            
            # 提取session年份
            session_year = json_data.get('session', 'unknown')
            
            # 遍历transcript提取每条演讲
            for item in json_data.get('transcript', []):
                # 只处理有metadata的text_block
                if item.get('type') != 'text_block' or 'metadata' not in item:
                    continue
                
                metadata = item['metadata'].copy()
                speech = item.get('speech', '')
                
                # 跳过空演讲
                if not speech or not speech.strip():
                    continue
                
                # 清洗speaker字段中的特殊字符
                speaker = metadata.get('speaker', '')
                speaker = speaker.lstrip('„"„')
                speaker = speaker.rstrip('""„')
                speaker = speaker.strip()

                # 过滤主持人（会议主持不是真正的发言人）
                MODERATOR_TITLES = [
                    "Vizepräsident",
                    "Vizepräsidentin",
                    "Präsident",
                    "Präsidentin",
                    "Alterspräsident",
                    "Alterspräsidentin"
                ]

                # 检查speaker是否是主持人
                is_moderator = False
                for title in MODERATOR_TITLES:
                    if speaker.startswith(title):
                        is_moderator = True
                        break

                # 如果是主持人，标记并跳过此演讲
                if is_moderator:
                    metadata['speaker'] = None
                    metadata['is_moderator'] = True
                    # 跳过主持人发言
                    continue
                else:
                    metadata['speaker'] = speaker
                    metadata['is_moderator'] = False
                
                # 添加文件名
                metadata['file'] = file_path.name
                
                speeches.append({
                    'metadata': metadata,
                    'speech': speech
                })
            
            logger.debug(f"文件 {file_path.name} 提取了 {len(speeches)} 条演讲")
            return speeches
            
        except Exception as e:
            logger.error(f"加载文件 {file_path} 时出错: {e}")
            return []
    
    def get_statistics(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        获取数据统计信息
        
        Args:
            data: 演讲数据列表
        
        Returns:
            统计信息字典,包括:
            - total_count: 总记录数
            - years: 涉及的年份
            - parties: 涉及的党派
            - speakers_count: 发言人数量
        """
        from collections import Counter
        
        years = Counter()
        parties = Counter()
        speakers = set()
        
        for item in data:
            metadata = item['metadata']
            years[metadata.get('year', 'unknown')] += 1
            parties[metadata.get('group', 'None')] += 1
            speakers.add(metadata.get('speaker', 'unknown'))
        
        stats = {
            'total_count': len(data),
            'years': dict(years.most_common()),
            'parties': dict(parties.most_common(10)),  # 前10个党派
            'speakers_count': len(speakers)
        }
        
        logger.info("数据统计:")
        logger.info(f"  总记录数: {stats['total_count']}")
        logger.info(f"  年份分布: {list(stats['years'].keys())}")
        logger.info(f"  发言人数: {stats['speakers_count']}")
        
        return stats


if __name__ == "__main__":
    # 测试数据加载器
    loader = ParliamentDataLoader()
    
    # 加载数据
    data = loader.load_data()
    
    # 获取统计信息
    stats = loader.get_statistics(data)
    
    # 显示前3条数据示例
    print("\n=== 数据示例 ===")
    for i, item in enumerate(data[:3], 1):
        print(f"\n第{i}条:")
        print(f"  年份: {item['metadata'].get('year')}")
        print(f"  发言人: {item['metadata'].get('speaker')}")
        print(f"  党派: {item['metadata'].get('group')}")
        print(f"  内容长度: {len(item['speech'])} 字符")
        print(f"  内容预览: {item['speech'][:100]}...")
