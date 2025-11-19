"""
文本分块器模块
负责将长文本分割成适合向量化的小块
保留完整的metadata信息
"""

from typing import List, Dict, Any
from langchain.text_splitter import RecursiveCharacterTextSplitter
from src.config import settings
from src.utils import logger


class ParliamentTextSplitter:
    """
    德国议会演讲文本分块器
    
    功能:
    1. 将长演讲文本分割成小块
    2. 每个chunk保留完整的metadata
    3. 支持自定义chunk大小和重叠
    4. 智能处理段落边界
    """
    
    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
        separators: List[str] = None
    ):
        """
        初始化文本分块器
        
        Args:
            chunk_size: 分块大小(字符数),默认从配置读取
            chunk_overlap: 重叠大小(字符数),默认从配置读取
            separators: 分隔符列表,用于智能分块
        """
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
        
        # 优化的分隔符：优先段落→德语句子→中文句子→其他
        # 目的：避免在句子中间截断，保证信息完整性
        self.separators = separators or [
            "\n\n",  # 1. 段落分隔符（最高优先级）
            "\n",    # 2. 换行符
            ". ",    # 3. 德语/英语句号+空格（关键：避免句中截断）
            "! ",    # 4. 感叹号+空格
            "? ",    # 5. 问号+空格
            "; ",    # 6. 分号+空格
            "。",    # 7. 中文句号
            "；",    # 中文分号
            ", ",    # 8. 逗号+空格（较低优先级）
            "，",    # 中文逗号
            " ",     # 9. 空格（最后才按词分割）
            ""       # 10. 字符级别（终极回退）
        ]
        
        # 初始化LangChain的文本分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=self.separators,
            length_function=len,
            is_separator_regex=False
        )
        
        logger.info(
            f"初始化文本分块器: chunk_size={self.chunk_size}, "
            f"overlap={self.chunk_overlap}"
        )
    
    def split_speeches(
        self,
        speeches: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        对演讲列表进行分块
        
        Args:
            speeches: 演讲数据列表,每条包含metadata和speech
        
        Returns:
            分块后的数据列表,每个chunk包含:
            - text: 分块文本内容
            - metadata: 原始metadata + chunk_id
        """
        all_chunks = []
        
        logger.info(f"开始分块: {len(speeches)}条演讲")
        
        for speech_data in speeches:
            chunks = self._split_single_speech(speech_data)
            all_chunks.extend(chunks)
        
        logger.success(f"分块完成: {len(speeches)}条演讲 -> {len(all_chunks)}个chunks")
        
        return all_chunks
    
    def _split_single_speech(
        self,
        speech_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        对单条演讲进行分块
        
        Args:
            speech_data: 单条演讲数据
        
        Returns:
            该演讲的所有chunks
        """
        metadata = speech_data['metadata']
        speech_text = speech_data['speech']
        
        # 如果文本长度小于chunk_size,直接返回
        if len(speech_text) <= self.chunk_size:
            return [{
                'text': speech_text,
                'metadata': {
                    **metadata,
                    'chunk_id': 0,
                    'total_chunks': 1,
                    'chunk_size': len(speech_text)
                }
            }]
        
        # 使用text_splitter分割文本
        text_chunks = self.text_splitter.split_text(speech_text)
        
        # 为每个chunk添加metadata
        chunks = []
        for i, chunk_text in enumerate(text_chunks):
            chunk_data = {
                'text': chunk_text,
                'metadata': {
                    **metadata,  # 继承所有原始metadata
                    'chunk_id': i,  # chunk序号
                    'total_chunks': len(text_chunks),  # 总chunk数
                    'chunk_size': len(chunk_text)  # 当前chunk大小
                }
            }
            chunks.append(chunk_data)
        
        return chunks
    
    def get_chunk_statistics(
        self,
        chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        获取分块统计信息
        
        Args:
            chunks: 分块数据列表
        
        Returns:
            统计信息字典
        """
        total_chunks = len(chunks)
        chunk_sizes = [chunk['metadata']['chunk_size'] for chunk in chunks]
        
        stats = {
            'total_chunks': total_chunks,
            'avg_chunk_size': sum(chunk_sizes) / total_chunks if total_chunks > 0 else 0,
            'min_chunk_size': min(chunk_sizes) if chunk_sizes else 0,
            'max_chunk_size': max(chunk_sizes) if chunk_sizes else 0,
            'total_characters': sum(chunk_sizes)
        }
        
        logger.info("分块统计:")
        logger.info(f"  总chunk数: {stats['total_chunks']}")
        logger.info(f"  平均大小: {stats['avg_chunk_size']:.0f} 字符")
        logger.info(f"  大小范围: {stats['min_chunk_size']} - {stats['max_chunk_size']} 字符")
        
        return stats


if __name__ == "__main__":
    # 测试文本分块器
    from src.data_loader.loader import ParliamentDataLoader
    
    # 加载数据
    loader = ParliamentDataLoader()
    speeches = loader.load_data()
    
    print(f"\n加载了 {len(speeches)} 条演讲")
    
    # 初始化分块器
    splitter = ParliamentTextSplitter()
    
    # 分块处理
    chunks = splitter.split_speeches(speeches[:100])  # 测试前100条
    
    # 获取统计信息
    stats = splitter.get_chunk_statistics(chunks)
    
    # 显示示例
    print("\n=== Chunk示例 ===")
    for i, chunk in enumerate(chunks[:3], 1):
        print(f"\nChunk {i}:")
        print(f"  发言人: {chunk['metadata'].get('speaker')}")
        print(f"  党派: {chunk['metadata'].get('group')}")
        print(f"  年份: {chunk['metadata'].get('year')}")
        print(f"  Chunk ID: {chunk['metadata'].get('chunk_id')}/{chunk['metadata'].get('total_chunks')-1}")
        print(f"  文本长度: {chunk['metadata'].get('chunk_size')} 字符")
        print(f"  内容预览: {chunk['text'][:100]}...")
