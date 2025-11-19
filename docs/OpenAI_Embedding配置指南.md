# OpenAI官方Embedding配置指南

## 概述

本项目已配置为使用OpenAI官方的 `text-embedding-3-small` 模型进行文本向量化。

## 配置步骤

### 1. 获取OpenAI API Key

访问 [OpenAI API Keys](https://platform.openai.com/api-keys) 获取您的API Key。

### 2. 配置环境变量

**方法一：在 `.env` 文件中配置（推荐）**

编辑项目根目录的 `.env` 文件，添加：

```bash
# OpenAI官方API配置（用于Embedding）
OPENAI_EMBEDDING_API_KEY=sk-proj-xxxxxxxxxxxxx  # 替换为您的真实API Key
OPENAI_EMBEDDING_BASE_URL=https://api.openai.com/v1
```

**方法二：设置系统环境变量**

在PowerShell中：
```powershell
$env:OPENAI_EMBEDDING_API_KEY="sk-proj-xxxxxxxxxxxxx"
```

在CMD中：
```cmd
set OPENAI_EMBEDDING_API_KEY=sk-proj-xxxxxxxxxxxxx
```

### 3. 配置Embedding模式

确保 `.env` 文件中设置为使用OpenAI：

```bash
# 选择Embedding方式：local / openai / vertex
EMBEDDING_MODE=openai  # 使用OpenAI官方API
```

## 模型信息

- **模型名称**: `text-embedding-3-small`
- **向量维度**: 1536
- **官方文档**: https://platform.openai.com/docs/guides/embeddings
- **价格**: $0.02 / 1M tokens（非常便宜）

## 测试连接

运行测试脚本验证配置：

```powershell
python test_openai_embedding.py
```

成功输出示例：
```
================================================================================
  OpenAI官方 Embedding 测试
================================================================================

[0] 检查配置...
✅ API Key: sk-proj-xxxxxxxxxx...
✅ API URL: https://api.openai.com/v1
✅ 模型: text-embedding-3-small
✅ 维度: 1536

[1] 初始化Embedding客户端...
✅ 使用OpenAI官方API
✅ 模型: text-embedding-3-small
✅ 向量维度: 1536

[2] 测试单文本Embedding...
✅ 文本: 德国联邦议院是德国的最高立法机构。
✅ 向量维度: 1536
✅ 向量前5维: [0.123, -0.456, 0.789, ...]

[3] 测试批量Embedding...
✅ 批量embedding成功: 3个文本 -> 3个向量

================================================================================
  ✅ 所有测试通过！OpenAI Embedding工作正常
================================================================================
```

## 构建索引

测试成功后，运行构建脚本：

```powershell
python build_index.py
```

该脚本会：
1. 加载德国议会演讲数据
2. 文本分块
3. 使用OpenAI API生成embeddings
4. 存储到Milvus向量数据库

## 常见问题

### Q1: API Key错误
**错误信息**: `AuthenticationError: Invalid API Key`

**解决方案**:
- 检查API Key是否正确复制（注意首尾空格）
- 确认API Key未过期
- 访问 https://platform.openai.com/api-keys 重新生成

### Q2: 余额不足
**错误信息**: `RateLimitError: You exceeded your current quota`

**解决方案**:
- 访问 https://platform.openai.com/account/billing 充值
- OpenAI要求至少充值 $5

### Q3: 网络连接问题
**错误信息**: `Connection timeout` 或 `Network error`

**解决方案**:
- 检查网络连接
- 如在中国大陆，可能需要配置代理
- 设置环境变量:
  ```powershell
  $env:HTTP_PROXY="http://your-proxy:port"
  $env:HTTPS_PROXY="http://your-proxy:port"
  ```

### Q4: 速率限制
**错误信息**: `RateLimitError: Rate limit exceeded`

**解决方案**:
- OpenAI有每分钟请求数限制
- 在 `build_index.py` 中调整 `batch_size` 参数
- 添加延时: `time.sleep(1)`

## 成本估算

以处理1000条演讲为例：
- 平均每条演讲: ~500 tokens
- 总tokens: 500,000
- 成本: $0.02 × 0.5 = **$0.01 USD**

非常经济实惠！

## 对比其他方案

| 方案 | 优点 | 缺点 | 成本 |
|------|------|------|------|
| **OpenAI官方** | ✅ 稳定可靠<br>✅ 向量质量高<br>✅ 1536维 | ❌ 需要付费<br>❌ 需要网络 | $0.02/1M tokens |
| 本地模型 | ✅ 完全免费<br>✅ 离线可用 | ❌ 384维<br>❌ 质量略低 | 免费 |
| Vertex AI | ✅ Google官方<br>✅ 768维 | ❌ 配置复杂<br>❌ 需要GCP账号 | 按用量计费 |

## 配置文件参考

完整的 `.env` 配置：

```bash
# ========== LLM配置 ==========
# 第三方代理API（用于聊天）
OPENAI_API_KEY=sk-BC2EBzybRMyVyMJNaK8nvZWUe6Jv4CMCFI3Wd6Yq3QJjQfWm
THIRD_PARTY_BASE_URL=https://api.evolink.ai/v1
THIRD_PARTY_MODEL_NAME=gemini-2.5-pro

# OpenAI官方API（用于Embedding）
OPENAI_EMBEDDING_API_KEY=sk-proj-xxxxxxxxxxxxx  # 填写您的API Key
OPENAI_EMBEDDING_BASE_URL=https://api.openai.com/v1

# ========== Embedding配置 ==========
EMBEDDING_MODE=openai  # 使用OpenAI官方API

# OpenAI Embedding配置
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMENSION=1536
```

## 技术支持

如有问题，请检查：
1. OpenAI官方文档: https://platform.openai.com/docs
2. API状态页: https://status.openai.com
3. 项目日志输出
