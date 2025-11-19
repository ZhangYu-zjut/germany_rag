# OpenAI Embedding 使用说明

## 🎯 快速开始

### 1️⃣ 填写API Key

编辑 `.env` 文件，在第7行填写您的OpenAI API Key：

```bash
# OpenAI官方API配置（用于Embedding）
OPENAI_EMBEDDING_API_KEY=sk-proj-在这里填写您的API_Key  # ⬅️ 在这里填写
OPENAI_EMBEDDING_BASE_URL=https://api.openai.com/v1
```

**获取API Key**: https://platform.openai.com/api-keys

---

### 2️⃣ 运行测试

在PowerShell中执行：

```powershell
# 方法一：使用快速测试脚本（推荐）
.\quick_test_openai.ps1

# 方法二：手动设置环境变量并测试
$env:OPENAI_EMBEDDING_API_KEY="sk-proj-xxxxx"
python test_openai_embedding.py
```

---

### 3️⃣ 查看测试结果

✅ **成功示例**：
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
✅ 向量前5维: [0.0123, -0.0456, 0.0789, -0.0234, 0.0567]

[3] 测试批量Embedding...
✅ 批量embedding成功: 3个文本 -> 3个向量

================================================================================
  ✅ 所有测试通过！OpenAI Embedding工作正常
================================================================================
```

❌ **失败示例**：
```
❌ 错误: 未设置OPENAI_EMBEDDING_API_KEY

请在 .env 文件中设置:
  OPENAI_EMBEDDING_API_KEY=sk-xxx...
```

---

### 4️⃣ 构建索引

测试成功后，运行：

```powershell
python build_index.py
```

这将：
- ✅ 加载德国议会演讲数据
- ✅ 文本分块处理
- ✅ 使用OpenAI API生成embeddings（1536维向量）
- ✅ 存储到Milvus向量数据库

---

## 📋 完整配置检查清单

- [ ] 已在 `.env` 文件中填写 `OPENAI_EMBEDDING_API_KEY`
- [ ] `EMBEDDING_MODE=openai` 已设置
- [ ] 运行 `python test_openai_embedding.py` 测试通过
- [ ] 删除旧的 `milvus_data/` 目录（如果存在）
- [ ] 运行 `python build_index.py` 构建索引

---

## 🔑 获取OpenAI API Key

### 步骤：

1. **访问**: https://platform.openai.com/api-keys
2. **登录**: 使用您的OpenAI账号
3. **创建Key**: 点击 "Create new secret key"
4. **复制Key**: 格式为 `sk-proj-xxxxxxxxxx`
5. **粘贴**: 到 `.env` 文件的 `OPENAI_EMBEDDING_API_KEY=`

### 注意：
- 首次使用需要充值（最低$5）
- 访问: https://platform.openai.com/account/billing

---

## 💰 成本估算

| 数据量 | Token数 | 成本 |
|--------|---------|------|
| 100条演讲 | ~50K | $0.001 |
| 1,000条演讲 | ~500K | $0.01 |
| 10,000条演讲 | ~5M | $0.10 |
| 100,000条演讲 | ~50M | $1.00 |

**结论**: 非常便宜！处理整个项目数据也就$1左右。

---

## 🛠️ 故障排除

### 问题1: API Key错误

**错误信息**:
```
AuthenticationError: Invalid API Key
```

**解决方案**:
- ✅ 检查API Key是否正确复制（注意首尾空格）
- ✅ 确认Key格式为 `sk-proj-xxx` 或 `sk-xxx`
- ✅ 访问 https://platform.openai.com/api-keys 确认Key有效

---

### 问题2: 余额不足

**错误信息**:
```
RateLimitError: You exceeded your current quota
```

**解决方案**:
- ✅ 访问 https://platform.openai.com/account/billing
- ✅ 添加支付方式并充值（最低$5）

---

### 问题3: 网络连接失败

**错误信息**:
```
Connection timeout
Network error
```

**解决方案**:

**如果在中国大陆，需要配置代理**:

```powershell
# 在PowerShell中设置代理
$env:HTTP_PROXY="http://127.0.0.1:7890"
$env:HTTPS_PROXY="http://127.0.0.1:7890"

# 然后运行测试
python test_openai_embedding.py
```

---

### 问题4: 环境变量未生效

**现象**: 设置了环境变量但仍提示未找到

**解决方案**:

```powershell
# 确保在同一PowerShell窗口中设置并运行
$env:OPENAI_EMBEDDING_API_KEY="sk-proj-xxxxx"
python test_openai_embedding.py  # 立即在同一窗口运行
```

或者直接在 `.env` 文件中配置（推荐）。

---

## 📚 相关文档

- [`docs/OpenAI_Embedding配置指南.md`](docs/OpenAI_Embedding配置指南.md) - 详细配置说明
- [`docs/改用OpenAI_Embedding总结.md`](docs/改用OpenAI_Embedding总结.md) - 修改总结
- [OpenAI官方文档](https://platform.openai.com/docs/guides/embeddings)

---

## ✅ 当前配置状态

运行以下命令检查配置：

```powershell
python -c "from src.config import settings; print(f'Embedding模式: {settings.embedding_mode}'); print(f'模型: {settings.openai_embedding_model}'); print(f'维度: {settings.embedding_dimension}')"
```

**预期输出**:
```
Embedding模式: openai
模型: text-embedding-3-small
维度: 1536
```

---

## 🎉 准备就绪！

完成以上步骤后，您就可以：
1. ✅ 构建向量索引
2. ✅ 运行智能问答系统
3. ✅ 开始使用LangGraph工作流

**下一步**: 运行 `python build_index.py` 开始构建索引！
