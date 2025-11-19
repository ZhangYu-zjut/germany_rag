"""
Milvus客户端模块
管理与Milvus向量数据库的连接
"""

from pymilvus import connections, utility
from typing import Optional
from src.config import settings
from src.utils import logger


class MilvusClient:
    """
    Milvus数据库客户端
    
    功能:
    1. 管理Milvus连接(本地/云端)
    2. 连接池管理
    3. 健康检查
    """
    
    def __init__(
        self,
        alias: str = "default",
        mode: Optional[str] = None
    ):
        """
        初始化Milvus客户端
        
        Args:
            alias: 连接别名
            mode: 连接模式(local/cloud),默认从配置读取
        """
        self.alias = alias
        self.mode = mode or settings.milvus_mode
        self.is_connected = False
        self.max_retries = 3  # 最大重试次数
        self.retry_delay = 1.0  # 重试延迟(秒)
        
        logger.info(f"初始化Milvus客户端: mode={self.mode}, alias={self.alias}")
    
    def connect(self):
        """
        建立Milvus连接
        根据配置连接Milvus Lite/本地Docker/云端
        """
        try:
            if self.mode == "lite":
                self._connect_lite()
            elif self.mode == "local":
                self._connect_local()
            elif self.mode == "cloud":
                self._connect_cloud()
            else:
                raise ValueError(f"不支持的Milvus模式: {self.mode}")
            
            self.is_connected = True
            logger.success(f"Milvus连接成功: mode={self.mode}")
            
            # 输出Milvus服务器信息
            self._print_server_info()
            
        except Exception as e:
            logger.error(f"Milvus连接失败: {e}")
            raise
    
    def _connect_lite(self):
        """连接Milvus Lite(轻量级版本,无需Docker)"""
        import os
        
        # 确保数据目录存在
        db_path = os.path.abspath(settings.milvus_lite_path)
        db_dir = os.path.dirname(db_path) if os.path.dirname(db_path) else "."
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"创建数据目录: {db_dir}")
        
        # 获取数据库文件路径（Milvus Lite需要文件路径）
        if not db_path.endswith('.db'):
            db_path = os.path.join(db_path, 'milvus_lite.db')
        
        logger.info(f"连接Milvus Lite (数据路径: {db_path})")
        
        # 方法1: 尝试使用 pymilvus 2.4.2+ 内置的 Milvus Lite（推荐）
        try:
            from milvus import default_server
            
            # 检查服务器是否已启动
            if not default_server.started:
                logger.info("启动 Milvus Lite 嵌入式服务器（pymilvus 内置）...")
                default_server.set_base_dir(db_dir)
                default_server.start()
                logger.success("Milvus Lite 服务器启动成功")
            else:
                logger.info("Milvus Lite 服务器已在运行")
            
            # 连接到 Milvus Lite 服务器
            connections.connect(
                alias=self.alias,
                host="127.0.0.1",
                port=default_server.listen_port
            )
            
            logger.success("Milvus Lite连接成功（使用 pymilvus 内置版本）")
            # 保存服务器引用以便后续停止
            self._milvus_lite_server = default_server
            return
            
        except ImportError:
            logger.debug("pymilvus 内置 Milvus Lite 不可用，尝试独立包...")
        except Exception as e:
            logger.debug(f"使用 pymilvus 内置 Milvus Lite 失败: {e}，尝试其他方式...")
        
        # 方法2: 尝试使用独立的 milvus-lite 包（向后兼容）
        try:
            from milvus_lite import server
            
            # 创建或获取Milvus Lite服务器实例
            # 使用单例模式，避免重复启动
            if not hasattr(self, '_milvus_lite_server'):
                logger.info("启动 Milvus Lite 嵌入式服务器（独立包）...")
                self._milvus_lite_server = server.Server(
                    db_file=db_path,
                    address="127.0.0.1:19530"  # 默认地址和端口
                )
                self._milvus_lite_server.start()
                logger.success("Milvus Lite服务器启动成功")
            
            # 连接到Milvus Lite服务器
            connections.connect(
                alias=self.alias,
                host="127.0.0.1",
                port=19530
            )
            
            logger.success("Milvus Lite连接成功（使用独立包）")
            return
            
        except ImportError:
            logger.debug("milvus_lite 独立包不可用...")
        except Exception as e:
            logger.debug(f"使用 milvus_lite 独立包失败: {e}")
        
        # 方法3: 尝试直接连接（如果 Milvus 服务已在运行）
        try:
            connections.connect(
                alias=self.alias,
                host="127.0.0.1",
                port=19530
            )
            logger.success("Milvus Lite连接成功（使用已有连接）")
            return
        except Exception as e:
            logger.debug(f"直接连接失败: {e}")
        
        # 如果所有方法都失败，提供安装指导
        pymilvus_version = self._get_pymilvus_version()
        raise ValueError(
            f"无法连接Milvus Lite。\n"
            f"\n请选择以下方式之一安装：\n"
            f"1. 安装/升级 pymilvus（推荐，已包含 Milvus Lite）：\n"
            f"   pip install -U pymilvus>=2.4.2\n"
            f"\n2. 或安装独立的 milvus-lite 包（备选）：\n"
            f"   pip install milvus-lite\n"
            f"\n3. 或者使用本地 Docker 模式（设置 MILVUS_MODE=local）：\n"
            f"   使用 Docker 运行: docker run -d --name milvus -p 19530:19530 milvusdb/milvus:latest\n"
            f"\n当前 pymilvus 版本: {pymilvus_version}\n"
            f"注意：Milvus Lite 目前仅支持 Ubuntu 20.04+ 和 macOS 11.0+ 系统"
        )
    
    def _get_pymilvus_version(self):
        """获取pymilvus版本"""
        try:
            import pymilvus
            return pymilvus.__version__
        except:
            return "未知"
    
    def _connect_local(self):
        """连接本地Milvus"""
        logger.info(
            f"连接本地Milvus: "
            f"{settings.milvus_local_host}:{settings.milvus_local_port}"
        )
        
        connections.connect(
            alias=self.alias,
            host=settings.milvus_local_host,
            port=settings.milvus_local_port
        )
    
    def _connect_cloud(self):
        """连接云端Milvus"""
        logger.info(f"连接云端Milvus: {settings.milvus_cloud_uri}")
        
        if not settings.milvus_cloud_uri or not settings.milvus_cloud_token:
            raise ValueError("云端模式需要配置MILVUS_CLOUD_URI和MILVUS_CLOUD_TOKEN")
        
        connections.connect(
            alias=self.alias,
            uri=settings.milvus_cloud_uri,
            token=settings.milvus_cloud_token
        )
    
    def _print_server_info(self):
        """打印Milvus服务器信息"""
        try:
            # 获取版本信息
            server_version = utility.get_server_version(using=self.alias)
            logger.info(f"Milvus服务器版本: {server_version}")
            
        except Exception as e:
            logger.warning(f"无法获取服务器信息: {e}")
    
    def disconnect(self):
        """断开Milvus连接"""
        try:
            connections.disconnect(alias=self.alias)
            self.is_connected = False
            
            # 如果是Milvus Lite模式，停止服务器
            if self.mode == "lite" and hasattr(self, '_milvus_lite_server'):
                try:
                    logger.info("停止Milvus Lite服务器...")
                    # 检查服务器类型并停止
                    if hasattr(self._milvus_lite_server, 'stop'):
                        self._milvus_lite_server.stop()
                    logger.info("Milvus Lite服务器已停止")
                except Exception as e:
                    logger.warning(f"停止Milvus Lite服务器时出错: {e}")
            
            logger.info("Milvus连接已断开")
            
        except Exception as e:
            logger.error(f"断开Milvus连接失败: {e}")
    
    def health_check(self) -> bool:
        """
        健康检查
        
        Returns:
            连接是否健康
        """
        try:
            # 尝试列出collections来验证连接
            utility.list_collections(using=self.alias)
            return True
            
        except Exception as e:
            logger.warning(f"Milvus健康检查失败: {e}")
            self.is_connected = False
            return False
    
    def ensure_connection(self) -> bool:
        """
        确保连接可用，必要时重连
        
        Returns:
            连接是否成功
        """
        import time
        
        # 如果连接健康，直接返回
        if self.is_connected and self.health_check():
            return True
        
        logger.info("连接不可用，尝试重新连接...")
        
        # 尝试重连
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    logger.info(f"重连尝试 {attempt + 1}/{self.max_retries}")
                    time.sleep(self.retry_delay * attempt)  # 指数退避
                
                # 先断开现有连接
                if self.is_connected:
                    try:
                        self.disconnect()
                    except Exception as e:
                        logger.warning(f"断开连接时出错: {e}")
                
                # 重新连接
                self.connect()
                
                # 验证连接
                if self.health_check():
                    logger.info("重连成功")
                    return True
                else:
                    logger.warning("重连后健康检查失败")
                    
            except Exception as e:
                logger.error(f"重连尝试 {attempt + 1} 失败: {e}")
                if attempt == self.max_retries - 1:
                    logger.error("达到最大重试次数，连接失败")
                    return False
        
        return False
    
    def with_retry(self, operation, *args, **kwargs):
        """
        使用重试机制执行操作
        
        Args:
            operation: 要执行的操作
            *args, **kwargs: 操作参数
            
        Returns:
            操作结果
        """
        for attempt in range(self.max_retries):
            try:
                # 确保连接可用
                if not self.ensure_connection():
                    raise RuntimeError("无法建立有效连接")
                
                # 执行操作
                return operation(*args, **kwargs)
                
            except Exception as e:
                logger.warning(f"操作执行失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    logger.error("操作最终失败")
                    raise
                
                # 标记连接为不可用，下次会重连
                self.is_connected = False
    
    def list_collections(self) -> list:
        """
        列出所有collections
        
        Returns:
            collection名称列表
        """
        try:
            collections = utility.list_collections(using=self.alias)
            logger.info(f"当前collections: {collections}")
            return collections
            
        except Exception as e:
            logger.error(f"列出collections失败: {e}")
            return []
    
    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect()


if __name__ == "__main__":
    # 测试Milvus客户端
    print("\n=== Milvus客户端测试 ===")
    
    # 测试1: 连接本地Milvus
    print("\n测试1: 连接本地Milvus")
    client = MilvusClient()
    
    try:
        client.connect()
        
        # 健康检查
        is_healthy = client.health_check()
        print(f"健康检查: {'通过' if is_healthy else '失败'}")
        
        # 列出collections
        collections = client.list_collections()
        print(f"Collections: {collections}")
        
    except Exception as e:
        print(f"连接失败: {e}")
        print("提示: 请确保Milvus服务正在运行")
        print("  Docker启动: docker run -d --name milvus -p 19530:19530 milvusdb/milvus:latest")
    
    finally:
        client.disconnect()
    
    # 测试2: 使用上下文管理器
    print("\n测试2: 使用上下文管理器")
    try:
        with MilvusClient() as client:
            print(f"连接状态: {client.is_connected}")
            collections = client.list_collections()
            print(f"Collections: {collections}")
    except Exception as e:
        print(f"连接失败: {e}")
