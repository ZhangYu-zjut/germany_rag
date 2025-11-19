# BGE-M3 本地模型使用指南

## 概述

本项目现在支持使用本地 BGE-M3 模型进行 embedding，完全免费，无需 API Key，并且支持 GPU 加速。

## 功能特点

- ✅ **完全免费**：无需 API Key，无需云服务费用
- ✅ **离线可用**：模型下载后完全离线运行
- ✅ **GPU 加速**：自动检测并使用 GPU（如 4060Ti）进行加速
- ✅ **高性能**：BGE-M3 模型提供 1024 维向量，性能优异
- ✅ **多语言支持**：支持中文、德语等多种语言
- ✅ **灵活切换**：可以轻松切换到云服务 API 模式

## 安装依赖

首先安装必要的依赖库：

```bash
pip install FlagEmbedding>=1.2.0 torch>=2.0.0
```

或者直接安装项目依赖：

```bash
pip install -r requirements.txt
```

## 配置方式

### 方式1：环境变量（推荐）

在 `.env` 文件中设置：

```bash
# 设置为 local 模式
EMBEDDING_MODE=local

# 指定模型（可选，默认为 BAAI/bge-m3）
LOCAL_EMBEDDING_MODEL=BAAI/bge-m3
```

### 方式2：代码中指定

```python
from src.llm import GeminiEmbeddingClient

# 使用本地 BGE-M3 模型
client = GeminiEmbeddingClient(embedding_mode="local")
```

## 模型选择

### BGE-M3 模型（推荐）

- **模型名称**: `BAAI/bge-m3`
- **向量维度**: 1024
- **特点**: 性能最佳，多语言支持优秀
- **首次下载**: 约 2GB，自动从 Hugging Face 下载

### 其他支持的模型

- `paraphrase-multilingual-MiniLM-L12-v2`: 384维，sentence-transformers 模型
- `distiluse-base-multilingual-cased-v2`: 512维，sentence-transformers 模型

## GPU 加速

如果您的系统有 GPU（如 4060Ti），系统会自动检测并使用 GPU 加速：

1. **自动检测**：代码会自动检测是否有可用的 GPU
2. **GPU 加速**：使用 GPU 时，会自动启用半精度（FP16）加速
3. **批次优化**：GPU 模式下可以使用更大的批次大小（如 64 或 128）

### 手动指定设备

```python
from src.llm.local_embeddings import LocalEmbeddingClient

# 强制使用 GPU
client = LocalEmbeddingClient(model_name="BAAI/bge-m3", device="cuda:0")

# 强制使用 CPU
client = LocalEmbeddingClient(model_name="BAAI/bge-m3", device="cpu")
```

## 使用示例

### 基本使用

```python
from src.llm import GeminiEmbeddingClient

# 初始化（从环境变量读取配置）
client = GeminiEmbeddingClient()

# 单文本 embedding
text = "德国联邦议院是德国的最高立法机构。"
vector = client.embed_text(text)
print(f"向量维度: {len(vector)}")  # 1024

# 批量 embedding
texts = ["文本1", "文本2", "文本3"]
vectors = client.embed_batch(texts, batch_size=64)
```

### 在测试文件中使用

`test_end_to_end_real.py` 会自动根据 `EMBEDDING_MODE` 环境变量切换模式：

```bash
# 使用本地 BGE-M3 模型
export EMBEDDING_MODE=local
python tests/test_end_to_end_real.py

# 使用云服务 API（DeepInfra）
export EMBEDDING_MODE=deepinfra
python tests/test_end_to_end_real.py
```

## 模式切换

### 切换到本地模式

在 `.env` 文件中设置：
```bash
EMBEDDING_MODE=local
LOCAL_EMBEDDING_MODEL=BAAI/bge-m3
```

### 切换到云服务模式

在 `.env` 文件中设置：
```bash
EMBEDDING_MODE=deepinfra
# 或
EMBEDDING_MODE=openai
```

## 性能对比

| 模式 | 速度 | 费用 | 离线 | GPU加速 |
|------|------|------|------|---------|
| 本地 BGE-M3 | 快（GPU） | 免费 | ✅ | ✅ |
| DeepInfra API | 快 | 付费 | ❌ | ❌ |
| OpenAI API | 中等 | 付费 | ❌ | ❌ |

## 常见问题

### Q: 首次运行时模型下载很慢？

A: BGE-M3 模型约 2GB，首次下载需要一些时间。下载完成后会缓存在本地，后续使用无需重新下载。

### Q: 如何检查 GPU 是否可用？

A: 运行以下代码：

```python
import torch
print(f"CUDA 可用: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU 设备: {torch.cuda.get_device_name(0)}")
```

### Q: 内存不足怎么办？

A: 
1. 减小批次大小（batch_size）
2. 使用 CPU 模式（设置 `device="cpu"`）
3. 使用更小的模型（如 `paraphrase-multilingual-MiniLM-L12-v2`）

### Q: 如何查看模型下载位置？

A: 模型默认下载到 `~/.cache/huggingface/` 目录。

## 技术细节

- **库**: 使用 `FlagEmbedding` 库加载 BGE-M3 模型
- **框架**: 基于 PyTorch，支持 GPU 加速
- **向量维度**: BGE-M3 固定为 1024 维
- **精度**: GPU 模式下使用 FP16 半精度加速

## 参考资料

- [FlagEmbedding GitHub](https://github.com/FlagOpen/FlagEmbedding)
- [BGE-M3 模型页面](https://huggingface.co/BAAI/bge-m3)
- [BGE-M3 论文](https://arxiv.org/abs/2402.03216)

