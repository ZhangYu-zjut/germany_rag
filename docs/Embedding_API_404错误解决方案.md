# Embedding API 404 错误解决方案

## 🔍 **问题分析**

### **错误信息**
```
Error code: 404 - {'error': {'message': 'Invalid URL (POST /v1/embeddings)', 'type': 'invalid_request_error', 'param': '', 'code': ''}}
```

### **问题原因**

您使用的第三方 API 代理 (`https://api.evolink.ai/v1`) 可能：

1. ❌ **不支持 `/v1/embeddings` 端点**
2. ❌ **Embedding API 路径与聊天 API 不同**
3. ❌ **需要不同的 API Key 或端点配置**

---

## ✅ **解决方案**

### **方案一：使用 OpenAI 的 Embedding 模型（推荐）**

如果您的 API 提供商不支持 Gemini Embedding，可以改用 OpenAI 的 Embedding 模型。

#### **1. 修改 `.env` 配置**

```bash
# Embedding配置
GEMINI_EMBEDDING_MODEL=text-embedding-3-small  # 改用OpenAI模型
EMBEDDING_DIMENSION=1536
# 使用相同的base_url（如果支持）
```

**OpenAI Embedding 模型选项**：
- `text-embedding-3-small` - 1536维，性价比高 ⭐ **推荐**
- `text-embedding-3-large` - 3072维，效果更好但成本高
- `text-embedding-ada-002` - 1536维，旧版本

#### **2. 无需修改代码**

代码已经兼容 OpenAI Embedding API。

---

### **方案二：联系 API 提供商确认端点**

联系 `api.evolink.ai` 的客服，询问：

1. **是否支持 Embedding API？**
2. **Embedding API 的端点是什么？**
   - 可能是 `/v1/embeddings`
   - 也可能是 `/embeddings`
   - 或者其他自定义路径

3. **需要的模型名称是什么？**
   - `text-embedding-004`
   - `gemini-embedding-001`
   - 或其他名称

如果他们提供了不同的端点，在 `.env` 中配置：

```bash
# 专用 Embedding 端点
EMBEDDING_BASE_URL=https://api.evolink.ai/embeddings
```

---

### **方案三：使用本地 Embedding 模型（完全免费）**

如果不想依赖 API，可以使用本地 Embedding 模型。

#### **1. 安装 sentence-transformers**

```bash
pip install sentence-transformers
```

#### **2. 创建本地 Embedding 客户端**

创建 `src/llm/local_embeddings.py`:

```python
"""本地 Embedding 客户端"""

from sentence_transformers import SentenceTransformer
from typing import List
from src.utils import logger


class LocalEmbeddingClient:
    """
    本地 Embedding 客户端
    使用 sentence-transformers
    """
    
    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        """
        初始化本地 Embedding 模型
        
        Args:
            model_name: 模型名称
                - paraphrase-multilingual-MiniLM-L12-v2: 支持中文/德语，384维
                - distiluse-base-multilingual-cased-v2: 支持多语言，512维
        """
        logger.info(f"加载本地 Embedding 模型: {model_name}")
        self.model = SentenceTransformer(model_name)
        logger.success("✅ 本地模型加载成功")
    
    def embed_query(self, text: str) -> List[float]:
        """单文本 embedding"""
        return self.model.encode(text).tolist()
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """批量 embedding"""
        embeddings = self.model.encode(texts)
        return [emb.tolist() for emb in embeddings]
    
    def embed_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """批量处理"""
        return self.embed_documents(texts)
    
    def embed_chunks(
        self,
        chunks: List[dict],
        text_key: str = 'text',
        batch_size: int = 100
    ) -> List[dict]:
        """Chunks embedding"""
        texts = [chunk[text_key] for chunk in chunks]
        vectors = self.embed_batch(texts, batch_size)
        
        embedded_chunks = []
        for chunk, vector in zip(chunks, vectors):
            embedded_chunk = chunk.copy()
            embedded_chunk['vector'] = vector
            embedded_chunks.append(embedded_chunk)
        
        return embedded_chunks
```

#### **3. 在 `build_index.py` 中使用**

```python
# 修改这一行
# from src.llm import GeminiEmbeddingClient
from src.llm.local_embeddings import LocalEmbeddingClient

# 初始化本地 Embedding
# embedding_client = GeminiEmbeddingClient()
embedding_client = LocalEmbeddingClient()
```

**优点**：
- ✅ 完全免费
- ✅ 无需 API Key
- ✅ 离线可用
- ✅ 支持中文和德语

**缺点**：
- ⚠️ 向量维度可能不同（384或512维，而不是1536维）
- ⚠️ 首次运行需要下载模型（约200MB）
- ⚠️ 需要一定的本地计算资源

---

## 🔧 **快速修复步骤**

### **推荐：方案一（使用 OpenAI Embedding）**

```bash
# 1. 修改 .env
# 将这一行：
GEMINI_EMBEDDING_MODEL=text-embedding-004

# 改为：
GEMINI_EMBEDDING_MODEL=text-embedding-3-small

# 2. 重新运行
python build_index.py
```

如果还是 404 错误，说明您的 API 提供商不支持 Embedding API。

---

### **备选：方案三（本地模型）**

```bash
# 1. 安装依赖
pip install sentence-transformers

# 2. 创建 local_embeddings.py
# （复制上面的代码）

# 3. 修改 build_index.py
# 将 GeminiEmbeddingClient 改为 LocalEmbeddingClient

# 4. 运行
python build_index.py
```

---

## 📞 **联系 API 提供商**

发邮件给 `api.evolink.ai` 的支持团队：

```
主题：关于 Embedding API 支持的咨询

您好，

我正在使用贵平台的 API 服务（https://api.evolink.ai/v1），
遇到以下问题：

1. 使用 POST /v1/embeddings 时返回 404 错误
2. 我想使用 Gemini 的 text-embedding-004 模型

请问：
1. 贵平台是否支持 Embedding API？
2. 如果支持，正确的端点是什么？
3. 支持哪些 Embedding 模型？

我的 API Key: sk-BC2E... (前4位)

谢谢！
```

---

## 🧪 **测试 API 端点**

创建 `test_embedding_api.py`:

```python
"""测试不同的 Embedding API 端点"""

import requests
import json

# 配置
API_KEY = "sk-BC2EBzybRMyVyMJNaK8nvZWUe6Jv4CMCFI3Wd6Yq3QJjQfWm"
BASE_URL = "https://api.evolink.ai"

# 测试不同端点
endpoints = [
    "/v1/embeddings",           # OpenAI 标准端点
    "/embeddings",              # 可能的简化端点
    "/v1/models/embeddings",    # 可能的变体
]

# 测试不同模型
models = [
    "text-embedding-3-small",   # OpenAI 最新
    "text-embedding-ada-002",   # OpenAI 旧版
    "text-embedding-004",       # Gemini
]

def test_endpoint(endpoint, model):
    """测试单个端点"""
    url = f"{BASE_URL}{endpoint}"
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model,
        "input": "测试文本 test text"
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ 成功: {endpoint} + {model}")
            result = response.json()
            if 'data' in result:
                embedding = result['data'][0]['embedding']
                print(f"   向量维度: {len(embedding)}")
            return True
        else:
            print(f"❌ 失败: {endpoint} + {model}")
            print(f"   状态码: {response.status_code}")
            print(f"   响应: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ 错误: {endpoint} + {model}")
        print(f"   异常: {str(e)}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("测试 Embedding API 端点")
    print("="*60)
    
    for endpoint in endpoints:
        for model in models:
            print(f"\n测试: {endpoint} + {model}")
            test_endpoint(endpoint, model)
            print("-"*60)
```

运行测试：
```bash
python test_embedding_api.py
```

这会帮您找到正确的端点和模型组合。

---

## 💡 **建议配置**

### **如果 API 提供商支持 OpenAI Embedding**

```bash
# .env
GEMINI_EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536
# 不需要 EMBEDDING_BASE_URL
```

### **如果需要不同的端点**

```bash
# .env
GEMINI_EMBEDDING_MODEL=text-embedding-004
EMBEDDING_DIMENSION=1536
EMBEDDING_BASE_URL=https://api.evolink.ai/embeddings  # 从客服获取
```

### **如果使用本地模型**

```bash
# .env（可以保持不变，但不会使用）
# 在代码中直接使用 LocalEmbeddingClient
```

---

## 📊 **Embedding 模型对比**

| 模型 | 维度 | 语言支持 | 成本 | 推荐度 |
|------|------|---------|------|--------|
| text-embedding-3-small | 1536 | 多语言 | 低 | ⭐⭐⭐⭐⭐ |
| text-embedding-ada-002 | 1536 | 多语言 | 中 | ⭐⭐⭐⭐ |
| paraphrase-multilingual-MiniLM-L12-v2 | 384 | 多语言 | 免费 | ⭐⭐⭐⭐ (本地) |
| distiluse-base-multilingual-cased-v2 | 512 | 多语言 | 免费 | ⭐⭐⭐ (本地) |

---

## ✅ **总结**

### **最快解决方案**

1. **修改 `.env`** 改用 OpenAI 模型：
   ```bash
   GEMINI_EMBEDDING_MODEL=text-embedding-3-small
   ```

2. **重新运行**：
   ```bash
   python build_index.py
   ```

### **如果还是失败**

使用本地 Embedding 模型（完全免费，无需 API）：
```bash
pip install sentence-transformers
# 然后修改 build_index.py 使用 LocalEmbeddingClient
```

---

**最后更新**: 2025-10-31
