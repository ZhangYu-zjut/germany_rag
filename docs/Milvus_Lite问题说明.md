# Milvus Lite 问题说明

## 问题描述

运行 `python build_index.py` 时出现错误：
```
ModuleNotFoundError: No module named 'milvus_lite'
```

## 根本原因

1. **pymilvus 2.4.8** 声称内置 Milvus Lite，但实际运行时仍需要 `milvus_lite` 模块
2. **pymilvus 2.6.3** 更新后，`milvus_lite` 变成了可选依赖，但安装 `pymilvus[milvus_lite]` 时提示：
   ```
   WARNING: pymilvus 2.6.3 does not provide the extra 'milvus_lite'
   ```
3. PyPI 上**没有独立的 `milvus-lite` 包**

## 技术分析

### pymilvus 版本对比

| 版本 | Milvus Lite 支持 | 说明 |
|------|-----------------|------|
| 2.4.8 | ❌ 声称内置但不可用 | 运行时仍需要 milvus_lite 模块 |
| 2.6.3 | ❌ 可选依赖但无法安装 | 提示 `does not provide the extra 'milvus_lite'` |

### 错误堆栈

```python
File "pymilvus/orm/connections.py", line 382
    from milvus_lite.server_manager import server_manager_instance
ModuleNotFoundError: No module named 'milvus_lite'
```

## 解决方案

### ✅ 方案1: 使用 Docker 运行 Milvus（推荐）

这是**官方推荐**的方式，稳定可靠。

#### 步骤：

1. **修改配置** - 将 `.env` 中的 `MILVUS_MODE` 改为 `local`：
   ```bash
   MILVUS_MODE=local
   ```

2. **启动 Milvus Docker 容器**：
   ```powershell
   docker run -d --name milvus \
     -p 19530:19530 \
     -p 9091:9091 \
     -v milvus_data:/var/lib/milvus \
     milvusdb/milvus:latest
   ```

3. **验证连接**：
   ```powershell
   python -c "from pymilvus import connections; connections.connect(host='localhost', port='19530'); print('✅ 连接成功')"
   ```

4. **运行索引构建**：
   ```powershell
   python build_index.py
   ```

#### Docker 管理命令：

```powershell
# 启动容器
docker start milvus

# 停止容器
docker stop milvus

# 查看日志
docker logs milvus

# 查看状态
docker ps -a | Select-String milvus
```

---

### ⚠️ 方案2: 使用内存模式（临时测试）

如果只是临时测试，可以使用 pymilvus 的内存模式：

```python
from pymilvus import MilvusClient

# 使用内存模式
client = MilvusClient(":memory:")
```

**缺点**：
- 数据不持久化
- 重启后数据丢失
- 不适合生产环境

---

### ❌ 方案3: Milvus Lite（暂不可用）

Milvus Lite 在 Windows 上目前**不可用**，原因：
1. pymilvus 包中未包含 milvus_lite 模块
2. 没有独立的 milvus-lite PyPI 包
3. 可能需要从源码编译（复杂且不推荐）

**状态**: ❌ 暂时不推荐使用

---

## 最佳实践

### 推荐配置

**.env 文件**:
```bash
# 向量数据库配置
MILVUS_MODE=local  # 使用 Docker 模式

# 本地 Milvus 配置（Docker 模式）
MILVUS_LOCAL_HOST=localhost
MILVUS_LOCAL_PORT=19530
```

### Docker Compose 配置（可选）

如果想要更方便的管理，可以创建 `docker-compose.yml`：

```yaml
version: '3.5'

services:
  milvus:
    image: milvusdb/milvus:latest
    container_name: milvus
    ports:
      - "19530:19530"
      - "9091:9091"
    volumes:
      - milvus_data:/var/lib/milvus
    environment:
      ETCD_USE_EMBED: "true"
      COMMON_STORAGETYPE: local

volumes:
  milvus_data:
```

启动命令：
```powershell
docker-compose up -d
```

---

## 验证 Milvus 运行状态

### 1. 检查 Docker 容器

```powershell
docker ps -a | Select-String milvus
```

预期输出：
```
milvus   milvusdb/milvus:latest   Up 5 minutes   0.0.0.0:19530->19530/tcp
```

### 2. 测试连接

```powershell
python -c "from pymilvus import connections, utility; connections.connect(host='localhost', port='19530'); print('Version:', utility.get_server_version()); print('✅ Milvus 运行正常')"
```

### 3. 查看日志

```powershell
docker logs milvus --tail 50
```

---

## 常见问题

### Q1: Docker 启动失败

**错误**: `Cannot connect to the Docker daemon`

**解决**:
1. 确保 Docker Desktop 已启动
2. 检查 Docker 服务状态
3. 重启 Docker Desktop

---

### Q2: 端口被占用

**错误**: `port is already allocated`

**解决**:
```powershell
# 查找占用端口的进程
netstat -ano | findstr :19530

# 停止旧容器
docker stop milvus
docker rm milvus

# 重新启动
docker run -d --name milvus -p 19530:19530 milvusdb/milvus:latest
```

---

### Q3: 数据持久化

**问题**: 如何确保数据不丢失？

**解决**: 使用 Docker 卷挂载（上面的命令已包含）：
```powershell
-v milvus_data:/var/lib/milvus
```

数据会保存在 Docker 卷中，即使容器删除也不会丢失。

---

## 更新配置文件

已更新以下文件：

### `.env`
```bash
# 从
MILVUS_MODE=lite

# 改为
MILVUS_MODE=local
```

### `requirements.txt`
```bash
# 确保使用正确的版本
pymilvus==2.6.3  # 最新稳定版
```

---

## 总结

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **Docker (local)** | ✅ 稳定可靠<br>✅ 官方支持<br>✅ 数据持久化 | ❌ 需要 Docker | ⭐⭐⭐⭐⭐ |
| 内存模式 | ✅ 无需安装 | ❌ 数据不持久<br>❌ 仅测试用 | ⭐⭐ |
| Milvus Lite | ✅ 无需 Docker | ❌ 当前不可用 | ❌ |

**最终建议**: 使用 **Docker 模式**，已在 `.env` 中配置好，只需启动 Docker 容器即可。

---

## 下一步操作

1. **启动 Milvus Docker**:
   ```powershell
   docker run -d --name milvus -p 19530:19530 -p 9091:9091 -v milvus_data:/var/lib/milvus milvusdb/milvus:latest
   ```

2. **验证连接**:
   ```powershell
   python diagnose_milvus.py
   ```

3. **运行索引构建**:
   ```powershell
   python build_index.py
   ```

完成！🎉
