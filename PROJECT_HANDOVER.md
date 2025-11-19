# 📋 德国议会智能问答RAG系统 - 项目交接文档

**文档版本**: v1.0  
**创建日期**: 2025-11-05  
**最后更新**: 2025-11-05  
**项目状态**: 开发中，部分功能已完成

---

## 📑 目录

1. [项目概述](#项目概述)
2. [技术架构](#技术架构)
3. [环境配置](#环境配置)
4. [数据情况](#数据情况)
5. [模型和API配置](#模型和api配置)
6. [向量数据库](#向量数据库)
7. [项目进展](#项目进展)
8. [存在的问题](#存在的问题)
9. [关键文件说明](#关键文件说明)
10. [快速上手指南](#快速上手指南)
11. [常见问题](#常见问题)

---

## 🎯 项目概述

### 项目名称
**德国议会智能问答RAG系统** (rag_germant)

### 项目目标
基于RAG（Retrieval-Augmented Generation）技术，构建一个能够智能问答德国联邦议院（1949-2025年）演讲记录的系统。

### 核心功能
- 📚 **数据检索**: 基于语义相似度的向量检索 + 元数据过滤
- 🤖 **智能问答**: 支持简单查询、对比类、变化类、总结类问题
- 🌊 **工作流引擎**: 基于LangGraph的CoA（Chain of Agents）处理流程
- 🔍 **混合检索**: 向量检索 + 元数据过滤（年份、党派、议员等）

### 应用场景
- 学术研究：分析德国议会历史议题演变
- 政策分析：对比不同党派在不同时期的政策立场
- 数据查询：快速检索特定议员、党派、时期的发言内容

---

## 🏗️ 技术架构

### 核心技术栈

| 组件 | 技术选型 | 版本 | 说明 |
|------|---------|------|------|
| **LLM** | Gemini 2.5 Pro | - | 通过Evolink API调用 |
| **Embedding** | BGE-M3 (本地) | 1024维 | 默认使用本地模型，支持GPU加速 |
| **向量数据库** | Pinecone | - | 当前生产环境使用 |
| **工作流框架** | LangGraph | 0.2.45 | 复杂问题处理流程 |
| **数据处理** | LangChain | 0.3.7 | 文本处理、分块、检索 |
| **Python版本** | Python 3.10+ | - | 推荐使用3.10 |

### 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                    用户问题输入                          │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              LangGraph工作流引擎                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │意图判断  │→ │问题分类  │→ │参数提取  │             │
│  └──────────┘  └──────────┘  └──────────┘             │
│       │              │              │                  │
│       ▼              ▼              ▼                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │问题拆解  │→ │数据检索  │→ │智能总结  │             │
│  └──────────┘  └──────────┘  └──────────┘             │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│               Pinecone向量数据库                         │
│  - 720,000+ 向量 (1024维)                               │
│  - 元数据索引 (年份、党派、议员等)                        │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│               BGE-M3 Embedding模型                       │
│  - 本地运行，GPU加速                                     │
│  - 1024维向量                                            │
└─────────────────────────────────────────────────────────┘
```

### 项目目录结构

```
rag_germant/
├── src/                          # 核心源代码
│   ├── config/                  # 配置管理
│   │   └── settings.py          # 环境变量配置（Pydantic）
│   ├── data_loader/             # 数据加载和处理
│   │   ├── loader.py            # JSON数据加载器
│   │   ├── splitter.py          # 文本分块器
│   │   └── mapper.py            # 元数据映射
│   ├── llm/                     # LLM和Embedding封装
│   │   ├── client.py            # Gemini LLM客户端
│   │   ├── embeddings.py        # Embedding客户端（统一接口）
│   │   ├── local_embeddings.py  # BGE-M3本地Embedding
│   │   └── vertex_embeddings.py # Vertex AI Embedding
│   ├── vectordb/                # 向量数据库客户端
│   │   ├── client.py            # Milvus客户端
│   │   ├── qdrant_client.py     # Qdrant客户端
│   │   ├── qdrant_retriever.py  # Qdrant检索器
│   │   └── retriever.py         # Milvus检索器
│   ├── graph/                   # LangGraph工作流
│   │   ├── workflow.py          # 主工作流
│   │   ├── state.py             # 状态定义
│   │   └── nodes/               # 工作流节点
│   │       ├── intent.py        # 意图判断
│   │       ├── classify.py      # 问题分类
│   │       ├── extract.py       # 参数提取
│   │       ├── decompose.py     # 问题拆解
│   │       ├── retrieve.py      # 数据检索
│   │       ├── summarize.py     # 总结生成
│   │       └── exception.py    # 异常处理
│   └── utils/                   # 工具模块
│       └── logger.py            # 日志系统
├── data/                        # 数据目录
│   ├── pp_json_49-21/          # 1949-2021年JSON数据（85个文件）
│   ├── party_mapping.csv        # 党派映射表
│   └── map.csv                  # 议员-党派动态映射表
├── docs/                        # 项目文档
├── tests/                       # 测试代码
├── venv/                        # Python虚拟环境
├── .env                         # 环境变量配置（重要！）
├── requirements.txt             # Python依赖
├── main.py                      # 主程序入口
├── build_index.py               # 索引构建脚本
└── migrate_*.py                 # 数据迁移脚本（多个）
```

---

## ⚙️ 环境配置

### 1. Python环境

**推荐版本**: Python 3.10+

```bash
# 创建虚拟环境
python3.10 -m venv venv

# 激活虚拟环境
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
```

### 2. 安装依赖（虚拟环境中已经安装过了，不需要重复安装）

```bash
pip install -r requirements.txt
```

**关键依赖**:
- `langchain==0.3.7` - LangChain框架
- `langgraph==0.2.45` - LangGraph工作流
- `sentence-transformers>=2.2.0` - 本地Embedding支持
- `FlagEmbedding>=1.2.0` - BGE-M3模型支持
- `torch>=2.0.0` - GPU加速（可选）
- `pymilvus==2.6.3` - Milvus客户端
- `qdrant-client` - Qdrant客户端（如果使用）
- `pinecone-client` - Pinecone客户端（当前使用）

### 3. 环境变量配置

**重要**: 复制 `.env.example` 到 `.env` 并填写以下配置：

```bash
# ========== LLM配置 ==========
OPENAI_API_KEY=your_evolink_api_key_here
THIRD_PARTY_BASE_URL=https://api.evolink.ai/v1
THIRD_PARTY_MODEL_NAME=gemini-2.5-pro

# ========== Embedding配置 ==========
# 模式选择: local / openai / deepinfra / vertex
EMBEDDING_MODE=local

# 本地Embedding配置（BGE-M3）
LOCAL_EMBEDDING_MODEL=BAAI/bge-m3
LOCAL_EMBEDDING_DIMENSION=1024

# DeepInfra配置（备选）
DEEPINFRA_EMBEDDING_API_KEY=your_deepinfra_key
DEEPINFRA_EMBEDDING_BASE_URL=https://api.deepinfra.com/v1/openai
DEEPINFRA_EMBEDDING_MODEL=BAAI/bge-m3

# ========== 向量数据库配置 ==========
# Pinecone配置（当前使用）
PINECONE_VECTOR_DATABASE_API_KEY=your_pinecone_api_key
PINECONE_HOST=https://your-index.svc.pinecone.io
PINECONE_REGION=us-east-1

# Milvus配置（备选）
MILVUS_MODE=lite  # lite / local / cloud
MILVUS_LITE_PATH=./milvus_data/milvus_lite.db

# Qdrant配置（备选）
QDRANT_MODE=cloud  # memory / local / cloud
QDRANT_VECTOR_DATABASE_API_KEY=your_qdrant_key
QDRANT_VECTOR_DATABASE_URL=https://your-cluster.qdrant.io

# ========== 数据配置 ==========
DATA_MODE=ALL  # PART / ALL
DATA_DIR=data/pp_json_49-21

# ========== 文本分块配置 ==========
CHUNK_SIZE=4000      # 最佳配置：4000字符
CHUNK_OVERLAP=800    # 最佳配置：800字符重叠
```

### 4. GPU配置（可选但推荐）

**BGE-M3本地Embedding支持GPU加速**，可显著提升性能：

```bash
# 检查CUDA是否可用
python -c "import torch; print(torch.cuda.is_available())"

# 如果返回True，GPU可用
# BGE-M3会自动使用GPU加速
```
系统：Linux（通过windows中的WSL开启）

**GPU配置**:
- NVIDIA GPU 4060TI
- 显存：16GB


---

## 📊 数据情况

### 数据来源
德国联邦议院1949-2025年演讲记录

### 数据规模

| 指标 | 数值 | 说明 |
|------|------|------|
| **文件数量** | JSON文件 | 每年一个文件 |
| **数据范围** | 1949-2025年 | 跨越76年 |
| **总大小** | ~1.9GB | 压缩前 |
| **总记录数** | ~810,000条 | 演讲记录 |
| **数据目录** | `data/pp_json_49-21/` | 相对项目根目录 |

### 数据格式

**JSON文件结构**:
```json
{
  "session": 2015,
  "transcript": [
    {
      "type": "text_block",
      "metadata": {
        "session": "001",
        "year": "2015",
        "month": "01",
        "day": "21",
        "speaker": "Dr. Merkel",
        "group": "CDU/CSU",
        "lp": "18"
      },
      "speech": "演讲内容..."
    }
  ]
}
```

### 元数据字段

每条记录包含以下metadata：

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `year` | string | 年份 | "2015" |
| `month` | string | 月份 | "01" |
| `day` | string | 日期 | "21" |
| `session` | string | 会议编号 | "001" |
| `speaker` | string | 发言人姓名 | "Dr. Merkel" |
| `group` | string | 党派（德语） | "CDU/CSU" |
| `lp` | string | 立法期 | "18" |
| `file` | string | 源文件名 | "pp_2015.json" |

### 数据文件列表

主要数据文件位于 `data/pp_json_49-21/`:

```
pp_1949.json  ~5.1MB
pp_1950.json  ~22MB
pp_1951.json  ~23MB
...
pp_2020.json  ~40.5MB
pp_2021.json  ~35MB
```

### 数据迁移状态

**当前状态**: 数据还未迁移到Pinecone

| 年份范围 | 状态 | 向量数量 | 索引名称 |
|---------|------|---------|---------|
| 2015-2020 |  未完成 | ~400,000+ | german-bge |
| 2021-2025 |  未完成 | ~237,389 | german-bge |
| 1949-2014 | ⏸待处理 | - | - |

**详细信息**: 见 `MIGRATION_STATUS_REPORT.md`

---

## 🤖 模型和API配置

### 1. LLM模型

**当前使用**: Gemini 2.5 Pro

| 配置项 | 值 | 说明 |
|--------|-----|------|
| **API提供商** | Evolink | 第三方代理服务 |
| **Base URL** | `https://api.evolink.ai/v1` | API端点 |
| **模型名称** | `gemini-2.5-pro` | 模型标识 |
| **API Key** | 环境变量 `OPENAI_API_KEY` | 需配置 |
| **客户端类** | `src/llm/client.py::GeminiLLMClient` | 封装类 |

**代码位置**: `src/llm/client.py`

**使用示例**:
```python
from src.llm.client import GeminiLLMClient

llm = GeminiLLMClient()
response = llm.invoke_with_prompt(
    user_message="你的问题",
    system_prompt="系统提示词"
)
```

### 2. Embedding模型

**当前使用**: BGE-M3（本地，1024维）

#### 模型选项

| 模式 | 模型 | 维度 | 位置 | 成本 | 性能 |
|------|------|------|------|------|------|
| **local** (推荐) | BGE-M3 | 1024 | 本地GPU | 免费 | 300+ emb/s |
| **deepinfra** | BGE-M3 | 1024 | DeepInfra API | 低 | 快 |
| **openai** | text-embedding-3-small | 1536 | OpenAI API | 中 | 快 |
| **vertex** | text-embedding-004 | 768 | Google Cloud | 中 | 快 |

#### BGE-M3本地模型详情

**模型位置**: 
- HuggingFace模型ID: `BAAI/bge-m3`
- 首次使用自动下载到 `~/.cache/huggingface/`
- 模型大小: ~1.2GB

**配置**:
```python
# src/config/settings.py
EMBEDDING_MODE=local
LOCAL_EMBEDDING_MODEL=BAAI/bge-m3
LOCAL_EMBEDDING_DIMENSION=1024
```

**性能优化**:
- GPU加速: 自动使用（如果可用）
- 批量处理: `batch_size=800`（16GB GPU）
- 并发数: `max_workers=20`
- 处理速度: **300+ vectors/秒**（GPU）

**代码位置**: 
- `src/llm/embeddings.py` - 统一接口
- `src/llm/local_embeddings.py` - BGE-M3实现

**使用示例**:
```python
from src.llm.embeddings import GeminiEmbeddingClient

# 自动使用配置的模式
embedding_client = GeminiEmbeddingClient()

# 单文本embedding
vector = embedding_client.embed_text("德国议会")

# 批量embedding
vectors = embedding_client.embed_batch(
    texts=["文本1", "文本2"],
    batch_size=800
)
```

### 3. API密钥管理

**所有API密钥存储在 `.env` 文件中**:

```bash
# LLM API
OPENAI_API_KEY=your_evolink_key

# Embedding API（如果使用DeepInfra）
DEEPINFRA_EMBEDDING_API_KEY=your_deepinfra_key

# 向量数据库API
PINECONE_VECTOR_DATABASE_API_KEY=your_pinecone_key
QDRANT_VECTOR_DATABASE_API_KEY=your_qdrant_key
```

**重要**: 
- ⚠️ `.env` 文件已添加到 `.gitignore`，不会提交到Git
- ⚠️ 不要将API密钥提交到版本控制
- ⚠️ 新成员需要单独获取API密钥

---

## 🗄️ 向量数据库

### 当前使用: Pinecone

**索引名称**: `german-bge`

**配置信息**:
```bash
PINECONE_VECTOR_DATABASE_API_KEY=pcsk_7Ts2j1_5swq4FCZ2bTY3wXB6hr88vK1txgm6HALTFobvWWrXqQBm7vpaixS1gFmuui4uDh
PINECONE_HOST=https://german-bge-v4vokxe.svc.aped-4627-b74a.pinecone.io
PINECONE_REGION=us-east-1
```

**索引配置**:
- **向量类型**: Dense
- **维度**: 1024（匹配BGE-M3）
- **距离度量**: Cosine
- **索引类型**: Manual Configuration

**数据状态**:
- ✅ 2015-2020年: 未迁移
- ✅ 2021-2025年: 未迁移
- ⏸️ 1949-2014年: 待处理

**代码位置**: 
- Pinecone客户端需要自行实现（当前使用直接API调用）
- 参考: `migrate_2015_optimal_config.py`

### 备选方案

#### 1. Milvus

**支持模式**:
- `lite`: 轻量级，无需Docker（推荐开发）
- `local`: Docker模式（推荐生产）
- `cloud`: 云端模式

**配置**:
```bash
MILVUS_MODE=lite
MILVUS_LITE_PATH=./milvus_data/milvus_lite.db
```

**代码位置**: `src/vectordb/client.py`

#### 2. Qdrant

**支持模式**:
- `memory`: 内存模式（开发测试）
- `local`: 本地文件模式
- `cloud`: 云端模式

**代码位置**: `src/vectordb/qdrant_client.py`

---

## 📈 项目进展

### 已完成功能 ✅

1. **✅ 数据加载模块**
   - JSON数据加载器
   - 元数据提取和映射
   - 数据统计和分析

2. **✅ 文本处理模块**
   - 文本分块器（支持自定义chunk_size和overlap）
   - 最佳配置：4000字符，800重叠

3. **✅ Embedding模块**
   - BGE-M3本地Embedding（GPU加速）
   - 多种模式支持（local/openai/deepinfra/vertex）
   - 批量处理优化

4. **✅ 向量数据库集成**
   - Pinecone集成（当前使用）
   - Milvus集成（备选）
   - Qdrant集成（备选）

5. **✅ LangGraph工作流**
   - 意图判断节点
   - 问题分类节点
   - 参数提取节点
   - 问题拆解节点
   - 数据检索节点
   - 总结生成节点
   - 异常处理节点

6. **✅ 数据迁移脚本**
   - 批量迁移脚本
   - 断点续传支持
   - 性能优化配置

### 进行中 🔄

1. **🔄 数据迁移**
   - 2015-2020年数据迁移到Pinecone（未完成）
   - 1949-2014年数据待迁移

2. **🔄 性能优化**
   - Embedding性能优化（已完成，300+ emb/s）
   - 分块策略优化（已完成，4000/800配置）

### 待完成 ⏸️

1. **⏸️ 完整数据迁移**
   - 完成2015-2020年剩余数据
   - 迁移1949-2014年历史数据

2. **⏸️ Pinecone客户端封装**
   - 创建统一的Pinecone客户端类
   - 集成到 `src/vectordb/` 模块

3. **⏸️ 测试和验证**
   - 端到端测试
   - 性能基准测试
   - 问答质量评估

4. **⏸️ 文档完善**
   - API文档
   - 部署文档
   - 用户手册

---

## ⚠️ 存在的问题

### 1. 数据迁移未完成

**问题**: 
- 2015-2020年数据未迁移到Pinecone
- 1949-2014年数据完全未迁移

**影响**: 
- 检索只能覆盖部分年份
- 历史数据查询不完整

**解决方案（不一定对，需要理性思考）**:
- 继续运行迁移脚本：`migrate_2015_optimal_config.py`
- 或使用批量迁移：`batch_migrate_2015_2025.py`

### 2. Pinecone客户端未封装

**问题**: 
- 当前直接使用Pinecone API调用
- 没有统一的客户端封装类

**影响**: 
- 代码重复
- 难以切换向量数据库

**解决方案**:
- 创建 `src/vectordb/pinecone_client.py`
- 参考 `qdrant_client.py` 的实现

### 3. 网络代理配置复杂（目前好像已经解决了，需要你进行二次确认）

**问题**: 
- WSL2环境需要配置代理才能访问外部API
- 代理配置可能影响性能

**影响**: 
- 开发和部署复杂度增加
- 可能出现连接问题

**解决方案**:
- 已在 `~/.bashrc` 配置自动代理
- 使用本地Clash代理：`http://127.0.0.1:7890`
- 参考：`GLOBAL_PROXY_SETUP_COMPLETE.md`

### 4. 配置分散

**问题**: 
- 配置项分散在多个地方
- `.env` 文件需要手动配置

**影响**: 
- 容易遗漏配置项
- 新人上手困难

**解决方案**:
- 统一使用 `.env` 模板

### 5. 测试覆盖不足

**问题**: 
- 缺少完整的测试套件
- 端到端测试不完整

**影响**: 
- 代码质量难以保证
- 重构风险高

**解决方案**:
- 补充单元测试
- 添加集成测试
- 创建测试数据

---

## 📁 关键文件说明

### 核心代码文件

| 文件路径 | 说明 | 重要性 |
|---------|------|--------|
| `src/config/settings.py` | 配置管理（Pydantic） | ⭐⭐⭐⭐⭐ |
| `src/llm/client.py` | LLM客户端封装 | ⭐⭐⭐⭐⭐ |
| `src/llm/embeddings.py` | Embedding统一接口 | ⭐⭐⭐⭐⭐ |
| `src/llm/local_embeddings.py` | BGE-M3本地实现 | ⭐⭐⭐⭐⭐ |
| `src/graph/workflow.py` | LangGraph主工作流 | ⭐⭐⭐⭐⭐ |
| `src/data_loader/loader.py` | 数据加载器 | ⭐⭐⭐⭐ |
| `src/data_loader/splitter.py` | 文本分块器 | ⭐⭐⭐⭐ |
| `src/vectordb/qdrant_client.py` | Qdrant客户端 | ⭐⭐⭐ |
| `src/vectordb/client.py` | Milvus客户端 | ⭐⭐⭐ |

### 数据迁移脚本（需要检查是否可用）

| 文件路径 | 说明 | 状态 |
|---------|------|------|
| `migrate_2015_optimal_config.py` | 2015年数据迁移（最佳配置） | ✅ 可用 |
| `migrate_2015_2020_pinecone.py` | 2015-2020年批量迁移 | ✅ 可用 |
| `batch_migrate_2015_2025.py` | 2015-2025年批量迁移 | ✅ 可用 |

### 配置和文档

| 文件路径 | 说明 |
|---------|------|
| `.env` | 环境变量配置（**重要！**） |
| `requirements.txt` | Python依赖列表 |
| `README.md` | 项目README |
| `MIGRATION_STATUS_REPORT.md` | 数据迁移状态报告 |
| `BGE_M3_PERFORMANCE_VERIFIED.md` | BGE-M3性能验证报告 |

---

## 🚀 快速上手指南

### 第一步：环境准备

```bash
# 1. 克隆项目（如果从Git）
git clone <repository_url>
cd rag_germant

# 2. 创建虚拟环境
python3.10 -m venv venv
source venv/bin/activate  # Linux/Mac

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填写API密钥
```

### 第二步：验证配置

```bash
# 检查配置加载
python -c "from src.config import settings; print(settings.embedding_mode)"

# 测试Embedding（本地BGE-M3）
python -c "from src.llm.embeddings import GeminiEmbeddingClient; c=GeminiEmbeddingClient(); print(c.embed_text('test'))"

# 测试LLM连接
python -c "from src.llm.client import GeminiLLMClient; c=GeminiLLMClient(); print(c.invoke_with_prompt('你好', '你是一个助手'))"
```

### 第三步：数据准备

```bash
# 检查数据文件
ls -lh data/pp_json_49-21/ | head -10

# 测试数据加载
python -c "from src.data_loader.loader import ParliamentDataLoader; l=ParliamentDataLoader(); d=l.load_data(); print(f'加载了{len(d)}条记录')"
```

### 第四步：构建索引（如果需要）

```bash
# 构建向量索引（Milvus/Qdrant）
python build_index.py

# 或迁移到Pinecone（当前使用）
python migrate_2015_optimal_config.py
```

### 第五步：运行问答系统

```bash
# 交互式问答
python main.py

# 或测试工作流
python test_workflow.py
```

### 常见命令

```bash
# 检查Pinecone状态
python check_pinecone_status.py

# 测试检索
python test_retrieval.py

# 性能分析
python performance_analysis.py
```

---

## ❓ 常见问题

### Q1: 如何切换Embedding模型？

**A**: 修改 `.env` 文件中的 `EMBEDDING_MODE`:

```bash
# 使用本地BGE-M3（推荐）
EMBEDDING_MODE=local

# 使用DeepInfra API
EMBEDDING_MODE=deepinfra

# 使用OpenAI API
EMBEDDING_MODE=openai
```

### Q2: 如何切换向量数据库？

**A**: 修改 `.env` 文件中的数据库配置:

```bash
# 使用Pinecone（当前）
PINECONE_VECTOR_DATABASE_API_KEY=your_key

# 使用Milvus
MILVUS_MODE=lite

# 使用Qdrant
QDRANT_MODE=cloud
```

### Q3: GPU不可用怎么办？

**A**: BGE-M3会自动fallback到CPU模式，性能会降低但仍可使用。

### Q4: 数据迁移中断怎么办？

**A**: 迁移脚本支持断点续传，重新运行即可继续。

### Q5: 如何优化Embedding性能？

**A**: 
- 使用GPU加速（自动）
- 调整 `batch_size`（16GB GPU推荐800）
- 调整 `max_workers`（推荐20）

### Q6: 代理连接失败？

**A**: 
- 检查Clash是否运行：`ps aux | grep clash`
- 检查代理配置：`echo $http_proxy`
- 参考：`GLOBAL_PROXY_SETUP_COMPLETE.md`

---

## 📞 联系方式和支持

### 关键资源

- **项目仓库**: [Git仓库URL]
- **问题追踪**: [Issue Tracker URL]
- **文档目录**: `docs/`

### 获取帮助

1. 查看文档：`docs/` 目录
2. 查看问题报告：`MIGRATION_STATUS_REPORT.md`
3. 查看性能报告：`BGE_M3_PERFORMANCE_VERIFIED.md`
4. 提交Issue：描述问题和复现步骤

---

## 📝 更新日志

### 2025-11-05
- ✅ 完成BGE-M3本地Embedding集成
- ✅ 完成Pinecone数据迁移（部分）
- ✅ 完成性能优化（300+ emb/s）
- ✅ 完成分块策略优化（4000/800配置）

### 2025-11-04
- ✅ 完成LangGraph工作流
- ✅ 完成数据加载和分块模块

---

**文档维护**: 请及时更新此文档，确保信息准确。

**最后更新**: 2025-11-05

