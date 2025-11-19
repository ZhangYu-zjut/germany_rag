"""
配置管理模块
使用 Pydantic Settings 管理环境变量配置
支持 .env 文件加载
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Literal, List
import os


class Settings(BaseSettings):
    """
    项目配置类
    所有配置项从环境变量或 .env 文件中读取
    """
    
    # ========== LLM配置 ==========
    # 第三方代理API（用于聊天）
    openai_api_key: str = Field(
        default="",
        description="第三方API密钥（如果只测试embedding，可以为空）"
    )
    third_party_base_url: str = Field(
        default="https://api.evolink.ai/v1",
        description="第三方API基础URL"
    )
    third_party_model_name: str = Field(
        default="gemini-2.5-pro",
        description="使用的模型名称"
    )
    
    # OpenAI官方API（用于Embedding）
    openai_embedding_api_key: str = Field(
        default="",
        description="OpenAI官方API Key（用于Embedding）"
    )
    openai_embedding_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="OpenAI官方API URL"
    )
    
    # ========== Embedding配置 ==========
    # Embedding模式选择
    embedding_mode: Literal["local", "openai", "vertex", "deepinfra"] = Field(
        default="deepinfra",  # 默认使用DeepInfra（速度更快、价格更便宜）
        description="Embedding模式: local(本地免费) / openai(API) / vertex(Google Cloud) / deepinfra(DeepInfra API)"
    )
    
    # 本地Embedding配置
    local_embedding_model: str = Field(
        default="BAAI/bge-m3",
        description="本地Embedding模型名称（支持 BGE-M3 和 sentence-transformers 模型）"
    )
    local_embedding_dimension: int = Field(
        default=1024,
        description="本地Embedding向量维度（BGE-M3为1024维，sentence-transformers模型各不相同）"
    )
    
    # OpenAI Embedding配置
    openai_embedding_model: str = Field(
        default="text-embedding-3-small",
        description="OpenAI Embedding模型"
    )
    openai_embedding_dimension: int = Field(
        default=1536,
        description="OpenAI Embedding向量维度"
    )
    embedding_base_url: str | None = Field(
        default=None,
        description="Embedding API端点(如果与聊天API不同)"
    )
    
    # DeepInfra Embedding配置
    deepinfra_embedding_api_key: str = Field(
        default="",
        description="DeepInfra Embedding API Key"
    )
    deepinfra_embedding_base_url: str = Field(
        default="https://api.deepinfra.com/v1/openai",
        description="DeepInfra Embedding API Base URL"
    )
    deepinfra_embedding_model: str = Field(
        default="BAAI/bge-m3",
        description="DeepInfra Embedding模型名称"
    )
    deepinfra_embedding_dimension: int = Field(
        default=1024,
        description="DeepInfra Embedding向量维度（BAAI/bge-m3为1024维）"
    )
    
    # Vertex AI 配置
    vertex_project_id: str = Field(
        default="heroic-cedar-476803-e1",
        description="Google Cloud 项目 ID"
    )
    vertex_location: str = Field(
        default="us-central1",
        description="Vertex AI 区域"
    )
    
    # ========== 向量数据库配置 ==========
    milvus_mode: Literal["lite", "local", "cloud"] = Field(
        default="lite",
        description="Milvus模式: lite(轻量级,无需Docker) / local(本地Docker) / cloud(云端)"
    )
    
    # Milvus Lite配置(无需Docker)
    milvus_lite_path: str = Field(
        default="./milvus_data/milvus_lite.db",
        description="Milvus Lite数据库文件路径"
    )
    
    # 本地Milvus配置(Docker)
    milvus_local_host: str = Field(
        default="localhost",
        description="本地Milvus主机地址"
    )
    milvus_local_port: int = Field(
        default=19530,
        description="本地Milvus端口"
    )
    
    # 云端Milvus配置
    milvus_cloud_uri: str | None = Field(
        default=None,
        description="云端Milvus URI"
    )
    milvus_cloud_token: str | None = Field(
        default=None,
        description="云端Milvus Token"
    )
    
    # Collection配置
    milvus_collection_name: str = Field(
        default="german_parliament_speeches",
        description="Milvus Collection名称"
    )
    
    # ========== 数据配置 ==========
    data_mode: Literal["PART", "ALL"] = Field(
        default="PART",
        description="数据模式: PART(部分数据) 或 ALL(全部数据)"
    )
    
    part_data_years: str = Field(
        default="2019,2020,2021",
        description="部分数据年份(逗号分隔)"
    )
    
    data_dir: str = Field(
        default="data/pp_json_49-21",
        description="数据目录路径"
    )
    
    # ========== 文本分块配置 ==========
    chunk_size: int = Field(
        default=1000,
        description="文本分块大小"
    )
    chunk_overlap: int = Field(
        default=200,
        description="文本分块重叠大小"
    )
    
    # ========== 其他配置 ==========
    log_level: str = Field(
        default="INFO",
        description="日志级别"
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @property
    def part_data_years_list(self) -> List[str]:
        """将逗号分隔的年份字符串转换为列表"""
        return [year.strip() for year in self.part_data_years.split(",")]
    
    @property
    def embedding_dimension(self) -> int:
        """根据Embedding模式返回向量维度"""
        if self.embedding_mode == "local":
            return self.local_embedding_dimension
        elif self.embedding_mode == "openai":
            return self.openai_embedding_dimension
        elif self.embedding_mode == "deepinfra":
            return self.deepinfra_embedding_dimension
        else:  # vertex
            return 768  # Vertex AI text-embedding-004的维度
    
    @property
    def milvus_uri(self) -> str:
        """根据模式返回Milvus连接URI"""
        if self.milvus_mode == "lite":
            # Milvus Lite模式使用本地文件路径
            return self.milvus_lite_path
        elif self.milvus_mode == "local":
            return f"http://{self.milvus_local_host}:{self.milvus_local_port}"
        else:  # cloud
            if not self.milvus_cloud_uri:
                raise ValueError("云端模式下必须设置 MILVUS_CLOUD_URI")
            return self.milvus_cloud_uri
    
    @property
    def milvus_token(self) -> str | None:
        """根据模式返回Milvus Token"""
        if self.milvus_mode == "cloud":
            if not self.milvus_cloud_token:
                raise ValueError("云端模式下必须设置 MILVUS_CLOUD_TOKEN")
            return self.milvus_cloud_token
        return None


# 全局配置实例
settings = Settings()


if __name__ == "__main__":
    # 测试配置加载
    print("=== 配置加载测试 ===")
    print(f"LLM模型: {settings.third_party_model_name}")
    print(f"Embedding维度: {settings.embedding_dimension}")
    print(f"Milvus模式: {settings.milvus_mode}")
    print(f"Milvus URI: {settings.milvus_uri}")
    print(f"数据模式: {settings.data_mode}")
    print(f"部分数据年份: {settings.part_data_years_list}")
    print(f"Collection名称: {settings.milvus_collection_name}")
