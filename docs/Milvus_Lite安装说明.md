# Milvus Lite 安装和使用说明

## ✅ 重要更新

**好消息**：`pymilvus 2.2+` 版本已经**内置了 Milvus Lite 功能**，无需单独安装 `milvus-lite` 包！

---

## 📦 安装步骤

### 第 1 步：安装依赖

```bash
pip install -r requirements.txt
```

这会安装 `pymilvus==2.4.8`，它已经包含了 Milvus Lite 功能。

### 第 2 步：验证安装

```bash
python -c "import pymilvus; print(f'pymilvus版本: {pymilvus.__version__}')"
```

预期输出：
```
pymilvus版本: 2.4.8
```

---

## 🚀 使用 Milvus Lite

### 配置文件（`.env`）

确保配置为 lite 模式：

```bash
# Milvus模式
MILVUS_MODE=lite

# Milvus Lite 数据库文件路径
MILVUS_LITE_PATH=./milvus_data/milvus_lite.db
```

### 连接方式

Milvus Lite 使用**本地文件**作为数据库，连接方式非常简单：

```python
from pymilvus import connections

# 连接到 Milvus Lite（使用文件路径）
connections.connect(
    alias="default",
    uri="./milvus_data/milvus_lite.db"  # 本地文件路径
)
```

### 与 Docker Milvus 的区别

| 特性 | Milvus Lite | Docker Milvus |
|------|------------|---------------|
| **连接方式** | `uri="文件路径"` | `host="localhost", port=19530` |
| **需要 Docker** | ❌ 不需要 | ✅ 需要 |
| **数据存储** | 本地文件 (.db) | Docker 容器内 |
| **启动方式** | 自动创建 | 需要启动容器 |

---

## 🎯 完整使用流程

### 方式一：直接运行（推荐）

```bash
# 1. 确保配置正确
cat .env | grep MILVUS_MODE
# 应该显示: MILVUS_MODE=lite

# 2. 运行环境检查
python check_env.py

# 3. 构建索引（首次运行）
python build_index.py

# 4. 启动问答系统
python main.py
```

### 方式二：Python 代码使用

```python
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType

# 1. 连接 Milvus Lite
connections.connect(
    alias="default",
    uri="./milvus_data/milvus_lite.db"
)

# 2. 创建 Collection
fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=1536),
    FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
]
schema = CollectionSchema(fields=fields)
collection = Collection(name="test_collection", schema=schema)

# 3. 插入数据
import numpy as np
vectors = np.random.rand(10, 1536).tolist()
texts = [f"text_{i}" for i in range(10)]
collection.insert([vectors, texts])

# 4. 创建索引
index_params = {
    "index_type": "IVF_FLAT",
    "metric_type": "L2",
    "params": {"nlist": 128}
}
collection.create_index(field_name="vector", index_params=index_params)

# 5. 加载到内存
collection.load()

# 6. 搜索
search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
results = collection.search(
    data=[vectors[0]],
    anns_field="vector",
    param=search_params,
    limit=5
)

print(f"找到 {len(results[0])} 条结果")
```

---

## 🔍 验证 Milvus Lite 是否正常工作

### 测试脚本

创建 `test_milvus_lite.py`:

```python
"""测试 Milvus Lite 连接"""

from pymilvus import connections, utility
import os

def test_milvus_lite():
    db_path = "./milvus_data/milvus_lite.db"
    
    # 确保目录存在
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    print(f"连接 Milvus Lite: {db_path}")
    
    try:
        # 连接
        connections.connect(alias="default", uri=db_path)
        
        print("✅ 连接成功!")
        
        # 列出 Collections
        collections = utility.list_collections()
        print(f"当前 Collections: {collections}")
        
        # 断开连接
        connections.disconnect(alias="default")
        print("✅ 测试完成")
        
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_milvus_lite()
```

运行测试：
```bash
python test_milvus_lite.py
```

预期输出：
```
连接 Milvus Lite: ./milvus_data/milvus_lite.db
✅ 连接成功!
当前 Collections: []
✅ 测试完成
```

---

## 📊 数据存储

### 文件结构

```
项目目录/
├── milvus_data/              # Milvus Lite 数据目录
│   └── milvus_lite.db       # 数据库文件
│   └── milvus_lite.db-wal   # WAL 日志文件（可能存在）
│   └── milvus_lite.db-shm   # 共享内存文件（可能存在）
├── .env
├── requirements.txt
└── main.py
```

### 查看数据库大小

```bash
# Windows PowerShell
Get-ChildItem -Recurse milvus_data | Measure-Object -Property Length -Sum | Select-Object @{Name="Size(MB)"; Expression={[math]::Round($_.Sum/1MB, 2)}}

# Linux/Mac
du -sh milvus_data/
```

---

## 🐛 常见问题

### Q1: 找不到 `milvus-lite` 包

**答**：不需要单独安装！`pymilvus 2.2+` 已经内置了 Milvus Lite 功能。

**解决方案**：
```bash
# 只需安装 pymilvus
pip install pymilvus==2.4.8
```

### Q2: 连接时出错

**错误**：
```
Error: cannot connect to milvus lite
```

**解决方案**：
1. 确保使用**文件路径**而不是 `host:port`
2. 确保目录有写权限

```python
# ✅ 正确（Milvus Lite）
connections.connect(uri="./milvus_data/milvus_lite.db")

# ❌ 错误（这是 Docker Milvus 的方式）
connections.connect(host="localhost", port=19530)
```

### Q3: 数据文件在哪里？

**答**：在 `./milvus_data/milvus_lite.db`

可以直接删除这个文件来清空所有数据：
```bash
# Windows
Remove-Item -Recurse -Force milvus_data

# Linux/Mac
rm -rf milvus_data
```

### Q4: 如何备份数据？

**答**：直接复制数据库文件

```bash
# 备份
cp -r milvus_data milvus_data_backup

# 恢复
cp -r milvus_data_backup milvus_data
```

### Q5: Milvus Lite 有什么限制？

**答**：
- ✅ 功能完整，支持所有基本操作
- ✅ 适合开发、测试、小规模应用
- ⚠️ 性能不如完整版 Milvus
- ⚠️ 不支持分布式部署
- ⚠️ 建议数据量 < 100万条

**我们的项目（2.1万条）完全没问题！**

---

## 🔄 切换模式

### 从 Milvus Lite 切换到 Docker

```bash
# 1. 修改 .env
MILVUS_MODE=local

# 2. 启动 Docker
docker run -d --name milvus -p 19530:19530 milvusdb/milvus:latest

# 3. 重新构建索引
python build_index.py
```

### 从 Docker 切换回 Milvus Lite

```bash
# 1. 修改 .env
MILVUS_MODE=lite

# 2. 直接运行（无需 Docker）
python build_index.py
python main.py
```

---

## 📚 参考资源

- **pymilvus 官方文档**: https://milvus.io/docs/install-pymilvus.md
- **Milvus Lite 介绍**: https://milvus.io/docs/milvus_lite.md
- **API 参考**: https://milvus.io/api-reference/pymilvus/v2.4.x/About.md

---

## ✅ 总结

### 关键点

1. **无需单独安装** `milvus-lite`
2. **pymilvus 2.2+** 已内置 Milvus Lite
3. **连接方式**：使用文件路径而非 host:port
4. **完全无需 Docker**
5. **数据存储在本地文件**

### 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 运行系统
python main.py
```

就这么简单！🎉

---

**最后更新**: 2025-10-31
