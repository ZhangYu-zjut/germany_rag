"""
党派名称映射器和元数据丰富器
将各种党派名称变体统一映射到标准名称，并丰富chunks的元数据
"""

import csv
from pathlib import Path
from typing import Dict, Optional, List, Any
import re


class PartyMapper:
    """
    党派名称映射器
    
    功能:
    1. 加载党派映射表
    2. 将各种变体名称映射到标准名称
    3. 提供中文名称查询
    4. 支持模糊匹配
    """
    
    def __init__(self, mapping_file: str = "data/party_mapping.csv"):
        """
        初始化映射器
        
        Args:
            mapping_file: 映射表CSV文件路径
        """
        self.mapping_file = Path(mapping_file)
        self.mapping_dict: Dict[str, Dict] = {}
        self.standard_to_chinese: Dict[str, str] = {}
        
        self._load_mapping()
    
    def _load_mapping(self):
        """加载映射表"""
        if not self.mapping_file.exists():
            print(f"⚠️  警告: 映射表文件不存在: {self.mapping_file}")
            return
        
        with open(self.mapping_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                original = row['original_name']
                standard = row['standard_name']
                chinese = row['chinese_name']
                
                # 建立原始名称到标准名称的映射
                self.mapping_dict[original] = {
                    'standard_name': standard,
                    'chinese_name': chinese,
                    'active_period': row.get('active_period', ''),
                    'notes': row.get('notes', '')
                }
                
                # 建立标准名称到中文名称的映射
                self.standard_to_chinese[standard] = chinese
        
        print(f"✅ 已加载 {len(self.mapping_dict)} 条党派映射记录")
    
    def normalize(self, party_name: str) -> str:
        """
        将党派名称标准化
        
        Args:
            party_name: 原始党派名称
            
        Returns:
            标准化后的党派名称
        """
        # 去除前后空白
        party_name = party_name.strip()
        
        # 直接查找映射
        if party_name in self.mapping_dict:
            return self.mapping_dict[party_name]['standard_name']
        
        # 去除多余空格和换行后再查找
        cleaned_name = re.sub(r'\s+', ' ', party_name)
        if cleaned_name in self.mapping_dict:
            return self.mapping_dict[cleaned_name]['standard_name']
        
        # 如果找不到映射,返回原始名称
        return party_name
    
    def get_chinese_name(self, party_name: str) -> str:
        """
        获取党派的中文名称
        
        Args:
            party_name: 党派名称（原始或标准）
            
        Returns:
            中文名称
        """
        # 先标准化
        standard_name = self.normalize(party_name)
        
        # 查找中文名称
        return self.standard_to_chinese.get(standard_name, party_name)
    
    def get_info(self, party_name: str) -> Optional[Dict]:
        """
        获取党派的完整信息
        
        Args:
            party_name: 党派名称
            
        Returns:
            包含标准名称、中文名称、活动期等信息的字典
        """
        # 先尝试直接查找
        if party_name in self.mapping_dict:
            return self.mapping_dict[party_name]
        
        # 尝试清理后查找
        cleaned_name = re.sub(r'\s+', ' ', party_name.strip())
        if cleaned_name in self.mapping_dict:
            return self.mapping_dict[cleaned_name]
        
        return None
    
    def is_known_party(self, party_name: str) -> bool:
        """
        检查是否是已知的党派
        
        Args:
            party_name: 党派名称
            
        Returns:
            True如果在映射表中找到
        """
        return party_name.strip() in self.mapping_dict or \
               re.sub(r'\s+', ' ', party_name.strip()) in self.mapping_dict
    
    def get_all_standard_names(self) -> list[str]:
        """
        获取所有标准党派名称列表（去重）
        
        Returns:
            标准党派名称列表
        """
        return sorted(set(self.standard_to_chinese.keys()))
    
    def get_all_variants(self, standard_name: str) -> list[str]:
        """
        获取某个标准党派的所有变体名称
        
        Args:
            standard_name: 标准党派名称
            
        Returns:
            所有变体名称列表
        """
        variants = []
        for original, info in self.mapping_dict.items():
            if info['standard_name'] == standard_name:
                variants.append(original)
        return variants


# 全局单例
_mapper_instance: Optional[PartyMapper] = None


def get_party_mapper() -> PartyMapper:
    """
    获取全局党派映射器单例
    
    Returns:
        PartyMapper实例
    """
    global _mapper_instance
    if _mapper_instance is None:
        _mapper_instance = PartyMapper()
    return _mapper_instance


class MetadataMapper:
    """
    元数据丰富器
    用于丰富chunks的元数据，特别是添加党派中文名称等
    """
    
    def __init__(self):
        """初始化元数据映射器"""
        self.party_mapper = get_party_mapper()
    
    def enrich_chunks(
        self,
        chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        丰富chunks的元数据
        
        Args:
            chunks: 分块数据列表，每个chunk包含text和metadata
        
        Returns:
            丰富后的chunks列表，metadata中添加了group_chinese等字段
        """
        enriched_chunks = []
        
        for chunk in chunks:
            metadata = chunk.get('metadata', {}).copy()
            
            # 添加党派中文名称
            group = metadata.get('group', '')
            if group:
                metadata['group_chinese'] = self.party_mapper.get_chinese_name(group)
                # 标准化党派名称
                metadata['group_standard'] = self.party_mapper.normalize(group)
            
            # 添加其他可能需要丰富的字段
            # 例如：text_id（如果不存在）
            if 'text_id' not in metadata:
                # 从文件名或其他字段生成text_id
                file_name = metadata.get('file', '')
                speaker = metadata.get('speaker', '')
                year = metadata.get('year', '')
                chunk_id = metadata.get('chunk_id', 0)
                
                # 生成简单的text_id
                text_id = f"{file_name}_{speaker}_{year}_{chunk_id}".replace(' ', '_')
                metadata['text_id'] = text_id
            
            enriched_chunks.append({
                'text': chunk.get('text', ''),
                'metadata': metadata
            })
        
        return enriched_chunks
    
    def batch_enrich_chunks(
        self,
        chunks: List[Dict[str, Any]],
        batch_size: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        批量丰富chunks的元数据（与enrich_chunks相同，但支持批处理）
        
        Args:
            chunks: 分块数据列表
            batch_size: 批处理大小（当前未使用，保留接口兼容性）
        
        Returns:
            丰富后的chunks列表
        """
        return self.enrich_chunks(chunks)


if __name__ == "__main__":
    # 测试党派映射器
    mapper = PartyMapper()
    
    print("\n=== 党派映射器测试 ===\n")
    
    # 测试一些常见变体
    test_cases = [
        "CDU/CSU",
        "SPD",
        "GRÜNE",
        "BÜNDNIS 90/DIE GRÜNEN",
        "DIE LINKE",
        "PDS",
        "AfD",
        "None",
        "Fraktionslos",
        "FDP-Gast",
    ]
    
    print("标准化测试:")
    print("-" * 60)
    for party in test_cases:
        standard = mapper.normalize(party)
        chinese = mapper.get_chinese_name(party)
        print(f"{party:30s} -> {standard:20s} ({chinese})")
    
    print("\n\n所有标准党派名称:")
    print("-" * 60)
    for i, party in enumerate(mapper.get_all_standard_names(), 1):
        chinese = mapper.get_chinese_name(party)
        print(f"{i:2d}. {party:30s} ({chinese})")
    
    print("\n\n绿党的所有变体:")
    print("-" * 60)
    variants = mapper.get_all_variants("BÜNDNIS 90/DIE GRÜNEN")
    for variant in variants:
        print(f"  - {variant}")
    
    # 测试MetadataMapper
    print("\n\n=== MetadataMapper测试 ===\n")
    metadata_mapper = MetadataMapper()
    
    # 创建测试chunks
    test_chunks = [
        {
            'text': '测试文本1',
            'metadata': {
                'speaker': 'Angela Merkel',
                'group': 'CDU/CSU',
                'year': '2019',
                'file': 'pp_2019.json',
                'chunk_id': 0
            }
        },
        {
            'text': '测试文本2',
            'metadata': {
                'speaker': 'Test Speaker',
                'group': 'BÜNDNIS 90/DIE GRÜNEN',
                'year': '2020',
                'file': 'pp_2020.json',
                'chunk_id': 1
            }
        }
    ]
    
    enriched = metadata_mapper.enrich_chunks(test_chunks)
    
    print("元数据丰富结果:")
    print("-" * 60)
    for i, chunk in enumerate(enriched, 1):
        meta = chunk['metadata']
        print(f"\nChunk {i}:")
        print(f"  党派(德): {meta.get('group')}")
        print(f"  党派(中): {meta.get('group_chinese')}")
        print(f"  标准名称: {meta.get('group_standard')}")
        print(f"  text_id: {meta.get('text_id')}")
