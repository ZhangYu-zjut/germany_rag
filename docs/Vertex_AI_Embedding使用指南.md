# Vertex AI Embedding 使用指南

## 🎯 **概述**

使用 Google Cloud Vertex AI 的 `text-embedding-004` 模型进行文本向量化。这是 **Google 官方的 Gemini Embedding 模型**，效果优秀且稳定。

---

## 📋 **完整步骤**

### **第 1 步：安装依赖**

```bash
pip install -r requirements.txt
```

这会安装：
- `google-cloud-aiplatform>=1.38.0` - Vertex AI SDK
- 其他必要依赖

---

### **第 2 步：设置环境变量**

您需要设置 `GOOGLE_APPLICATION_CREDENTIALS` 环境变量，指向您的 JSON 凭证文件。

#### **Windows PowerShell** (推荐)

```powershell
# 设置环境变量（当前会话有效）
$env:GOOGLE_APPLICATION_CREDENTIALS="f:\vscode_project\tj_germany\heroic-cedar-476803-e1-fe50591663ce.json"

# 验证设置
echo $env:GOOGLE_APPLICATION_CREDENTIALS
```

#### **Windows CMD**

```cmd
# 设置环境变量
set GOOGLE_APPLICATION_CREDENTIALS=f:\vscode_project\tj_germany\heroic-cedar-476803-e1-fe50591663ce.json

# 验证设置
echo %GOOGLE_APPLICATION_CREDENTIALS%
```

#### **Linux/Mac**

```bash
# 设置环境变量
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/heroic-cedar-476803-e1-fe50591663ce.json"

# 验证设置
echo $GOOGLE_APPLICATION_CREDENTIALS
```

---

### **第 3 步：测试连接**

```bash
python test_vertex_embedding.py
```

**预期输出**：
```
================================================================================
测试 Vertex AI Embedding
================================================================================

[1/4] 检查环境变量...
✅ 找到环境变量: f:\vscode_project\tj_germany\heroic-cedar-476803-e1-fe50591663ce.json

[2/4] 检查凭证文件...
✅ 凭证文件存在

[3/4] 测试导入...
✅ vertexai 包导入成功

[4/4] 测试 API 调用...
  初始化客户端...
✅ Vertex AI Embedding 初始化成功！
📊 模型: text-embedding-004, 向量维度: 768

  测试单个文本...
✅ API 调用成功!
  - 文本: 你好，世界！
  - 向量维度: 768
  - 向量前5维: [0.123, -0.456, ...]

  测试批量处理...
✅ 批量处理成功!
  - 处理文本数: 3
  - 生成向量数: 3

================================================================================
✅ 所有测试通过！
================================================================================
```

---

### **第 4 步：构建索引**

```bash
python build_index_vertex.py
```

**流程**：
1. 检查环境变量
2. 加载演讲数据
3. 文本分块
4. 使用 Vertex AI 生成向量
5. 存储到 Milvus

**预计时间**：
- 2019-2021 数据（~2.1万条）: 约 10-15 分钟
- 全量数据：根据数据量而定

---

### **第 5 步：运行问答系统**

```bash
python main.py
```

---

## 🔑 **关键配置**

### **`.env` 文件**

```bash
# Embedding 配置
GEMINI_EMBEDDING_MODEL=text-embedding-004
EMBEDDING_DIMENSION=768  # text-embedding-004 的维度

# Vertex AI 配置
VERTEX_PROJECT_ID=heroic-cedar-476803-e1
VERTEX_LOCATION=us-central1
```

### **凭证文件信息**

- **文件名**: `heroic-cedar-476803-e1-fe50591663ce.json`
- **项目 ID**: `heroic-cedar-476803-e1`
- **服务账号**: `germany-rag@heroic-cedar-476803-e1.iam.gserviceaccount.com`
- **区域**: `us-central1`

---

## 📊 **Vertex AI text-embedding-004 特性**

| 特性 | 说明 |
|------|------|
| **模型名称** | text-embedding-004 |
| **向量维度** | 768 |
| **支持语言** | 100+ 语言（包括中文、德语） |
| **最大输入** | 2048 tokens |
| **速率限制** | 1000 requests/min |
| **批量限制** | 建议 5-10 条/批 |
| **成本** | 按使用量计费 |

---

## 💡 **代码使用示例**

### **基本使用**

```python
from src.llm.vertex_embeddings import VertexAIEmbeddingClient

# 初始化客户端
client = VertexAIEmbeddingClient()

# 单文本 embedding
text = "德国联邦议院是德国的最高立法机构。"
vector = client.embed_query(text)
print(f"向量维度: {len(vector)}")  # 768

# 批量 embedding
texts = [
    "社民党是德国历史最悠久的政党之一。",
    "基民盟在德国政治中扮演重要角色。",
    "绿党关注环境和气候问题。"
]
vectors = client.embed_batch(texts, batch_size=3)
print(f"生成 {len(vectors)} 个向量")
```

### **处理 Chunks**

```python
# Chunks 格式
chunks = [
    {
        'text': '演讲内容...',
        'metadata': {'speaker': 'Merkel', 'year': '2019'}
    },
    # ... 更多 chunks
]

# 批量 embedding
embedded_chunks = client.embed_chunks(chunks, batch_size=5)

# 每个 chunk 现在都有 vector 字段
for chunk in embedded_chunks:
    print(f"向量维度: {len(chunk['vector'])}")  # 768
```

---

## 🔧 **故障排查**

### **问题 1: 环境变量未设置**

**错误**：
```
❌ 错误: 未设置 GOOGLE_APPLICATION_CREDENTIALS 环境变量
```

**解决**：
```powershell
# PowerShell
$env:GOOGLE_APPLICATION_CREDENTIALS="f:\vscode_project\tj_germany\heroic-cedar-476803-e1-fe50591663ce.json"
```

---

### **问题 2: 凭证文件找不到**

**错误**：
```
❌ 凭证文件不存在: xxx
```

**解决**：
1. 确认文件路径正确
2. 使用**绝对路径**
3. 注意路径中的反斜杠 `\`

---

### **问题 3: API 未启用**

**错误**：
```
google.api_core.exceptions.PermissionDenied: 403 Vertex AI API has not been used in project xxx
```

**解决**：
1. 访问：https://console.cloud.google.com/apis/library/aiplatform.googleapis.com
2. 选择项目 `heroic-cedar-476803-e1`
3. 点击"启用"按钮

---

### **问题 4: 权限不足**

**错误**：
```
google.api_core.exceptions.PermissionDenied: 403 The caller does not have permission
```

**解决**：
服务账号需要以下权限：
- `Vertex AI User` 或
- `AI Platform Developer`

在 Google Cloud Console 中为服务账号 `germany-rag@heroic-cedar-476803-e1.iam.gserviceaccount.com` 添加权限。

---

### **问题 5: 速率限制**

**错误**：
```
google.api_core.exceptions.ResourceExhausted: 429 Quota exceeded
```

**解决**：
1. 减小 `batch_size`（建议 3-5）
2. 添加延迟（代码中已自动处理）
3. 检查配额限制

---

## 📈 **性能优化**

### **批次大小建议**

```python
# 小数据量（< 1000 条）
client.embed_chunks(chunks, batch_size=10)

# 中等数据量（1000-10000 条）
client.embed_chunks(chunks, batch_size=5)

# 大数据量（> 10000 条）
client.embed_chunks(chunks, batch_size=3)
```

### **并发处理**

如果需要加速，可以使用异步 API（需要修改代码）：

```python
# TODO: 实现异步版本
# from vertexai.language_models import TextEmbeddingModelAsync
```

---

## 🆚 **与其他 Embedding 方案对比**

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **Vertex AI** ⭐⭐⭐⭐⭐ | - 官方模型<br>- 稳定性高<br>- 效果好<br>- 支持多语言 | - 需要 GCP 账号<br>- 有成本 | 生产环境 |
| **OpenAI Embedding** ⭐⭐⭐⭐ | - 简单易用<br>- API 稳定 | - 需要 API Key<br>- 可能被墙 | 国际项目 |
| **本地模型** ⭐⭐⭐ | - 完全免费<br>- 离线可用 | - 效果略差<br>- 维度不同 | 开发测试 |

---

## 💰 **成本估算**

**Vertex AI Embedding 价格** (2024年):
- $0.000025 / 1000 characters

**我们的项目**:
- 数据量: ~2.1万条演讲
- 平均长度: ~500 字符/条
- 总字符数: ~10.5M 字符
- **预计成本**: ~$0.26 USD

非常便宜！ 💰

---

## ✅ **总结**

### **推荐流程**

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 设置环境变量（PowerShell）
$env:GOOGLE_APPLICATION_CREDENTIALS="f:\vscode_project\tj_germany\heroic-cedar-476803-e1-fe50591663ce.json"

# 3. 测试连接
python test_vertex_embedding.py

# 4. 构建索引
python build_index_vertex.py

# 5. 运行系统
python main.py
```

### **优点**

- ✅ 使用官方 Gemini Embedding
- ✅ 效果优秀，支持多语言
- ✅ 稳定可靠
- ✅ 成本很低
- ✅ 无需第三方代理

---

**最后更新**: 2025-10-31
