# Milvus Lite 在 Linux 上的安装和使用指南

## 概述

Milvus Lite 是 Milvus 的轻量级版本，适用于本地开发和测试，无需 Docker。在 Linux 环境下，Milvus Lite 支持 Ubuntu 20.04+ 系统。

## 系统要求

- **操作系统**: Ubuntu 20.04 或更高版本（或其他兼容的 Linux 发行版）
- **Python**: 3.7 或更高版本
- **CPU**: 支持 SSE4.2、AVX、AVX2 指令集（大多数现代 CPU 都支持）

## 安装方式

### 方式1：安装独立的 milvus-lite 包（推荐）

```bash
pip install milvus-lite
```

### 方式2：安装带 milvus-lite 支持的 pymilvus

```bash
pip install -U 'pymilvus[milvus-lite]'
```

### 方式3：如果方式1和2都不行，使用 Docker 模式

```bash
# 启动 Milvus Docker 容器
docker run -d --name milvus -p 19530:19530 milvusdb/milvus:latest

# 然后在 .env 文件中设置
MILVUS_MODE=local
```

## 配置

在 `.env` 文件中设置：

```bash
# 使用 Milvus Lite 模式
MILVUS_MODE=lite

# Milvus Lite 数据文件路径（可选，默认 ./milvus_data/milvus_lite.db）
MILVUS_LITE_PATH=./milvus_data/milvus_lite.db
```

## 验证安装

运行以下命令验证安装：

```bash
python3 -c "from milvus_lite import server; print('Milvus Lite 安装成功')"
```

如果成功，应该看到 "Milvus Lite 安装成功"。

## 常见问题

### Q1: 安装失败，提示找不到 milvus-lite 包

**解决方案**：
1. 确保使用 Python 3.7+
2. 更新 pip: `pip install --upgrade pip`
3. 尝试使用方式2: `pip install -U 'pymilvus[milvus-lite]'`

### Q2: 导入错误 `No module named 'milvus_lite'`

**解决方案**：
1. 检查是否在正确的虚拟环境中
2. 重新安装: `pip install milvus-lite`
3. 如果仍不行，使用 Docker 模式

### Q3: 在非 Ubuntu 系统上无法使用 Milvus Lite

**解决方案**：
Milvus Lite 目前仅官方支持 Ubuntu 20.04+ 和 macOS 11.0+。如果您的系统不兼容，请使用 Docker 模式：

```bash
# 启动 Milvus Docker 容器
docker run -d --name milvus -p 19530:19530 milvusdb/milvus:latest

# 设置环境变量
export MILVUS_MODE=local
```

### Q4: CPU 指令集不支持

检查 CPU 是否支持所需指令集：

```bash
cat /proc/cpuinfo | grep -o 'sse4_2\|avx\|avx2\|avx512'
```

如果没有输出，说明 CPU 可能不支持，建议使用 Docker 模式。

### Q5: 端口 19530 已被占用

**解决方案**：
1. 检查端口占用: `netstat -tuln | grep 19530`
2. 停止占用端口的进程
3. 或修改 Milvus Lite 的端口（需要修改代码）

## 使用 Docker 模式（备选方案）

如果 Milvus Lite 无法使用，可以使用 Docker 模式：

### 1. 安装 Docker

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install docker.io docker-compose

# 启动 Docker 服务
sudo systemctl start docker
sudo systemctl enable docker
```

### 2. 启动 Milvus Docker 容器

```bash
docker run -d \
  --name milvus \
  -p 19530:19530 \
  -p 9091:9091 \
  -v milvus_data:/var/lib/milvus \
  milvusdb/milvus:latest
```

### 3. 配置环境变量

在 `.env` 文件中设置：

```bash
MILVUS_MODE=local
MILVUS_LOCAL_HOST=localhost
MILVUS_LOCAL_PORT=19530
```

## 测试连接

运行测试脚本验证连接：

```bash
python3 tests/test_end_to_end_real.py
```

或者直接测试 Milvus 客户端：

```bash
python3 -c "
from src.vectordb.client import MilvusClient
with MilvusClient() as client:
    print('✅ Milvus 连接成功')
    print(f'模式: {client.mode}')
"
```

## 性能对比

| 模式 | 资源占用 | 启动速度 | 适用场景 |
|------|---------|---------|---------|
| Milvus Lite | 低 | 快 | 开发、测试、小规模数据 |
| Docker 模式 | 中 | 中 | 生产环境、大规模数据 |
| 云端模式 | - | - | 生产环境、高可用性 |

## 注意事项

1. **数据持久化**: Milvus Lite 的数据存储在本地文件（`.db` 文件）中，确保有足够的磁盘空间
2. **版本兼容性**: 确保 pymilvus 版本 >= 2.4.2
3. **系统兼容性**: Milvus Lite 主要在 Ubuntu 上测试，其他 Linux 发行版可能需要使用 Docker 模式
4. **资源限制**: Milvus Lite 适合小到中等规模的数据，大规模数据建议使用 Docker 或云端模式

## 参考资源

- [Milvus 官方文档](https://milvus.io/docs)
- [Milvus Lite 文档](https://milvus.io/docs/milvus_lite.md)
- [pymilvus GitHub](https://github.com/milvus-io/pymilvus)

