# API配置更新说明

**日期**: 2025-11-01  
**问题**: GeminiLLMClient需要支持第三方OpenAI兼容API

---

## ✅ 已完成的修改

### 1. 修复了`src/llm/client.py` ✅

**主要变更**:
- ✅ `invoke()` 方法：改为直接接收字符串参数（而不是消息列表）
- ✅ `invoke_with_messages()` 方法：新增，用于多轮对话
- ✅ `stream_invoke()` 方法：改为直接接收字符串参数
- ✅ 支持第三方API配置（已经在原代码中）

**API调用方式**:
```python
from src.llm.client import GeminiLLMClient

client = GeminiLLMClient()

# 方式1: 简单调用（字符串）
response = client.invoke("你的问题")

# 方式2: 带系统提示词
response = client.invoke(
    prompt="你的问题",
    system_prompt="你是一个专家..."
)

# 方式3: 多轮对话
messages = [
    {'role': 'user', 'content': '第一个问题'},
    {'role': 'assistant', 'content': '回答'},
    {'role': 'user', 'content': '第二个问题'}
]
response = client.invoke_with_messages(messages)
```

### 2. 配置文件已支持 ✅

**`src/config/settings.py` 已配置**:
- ✅ `OPENAI_API_KEY`: 第三方API密钥
- ✅ `THIRD_PARTY_BASE_URL`: 默认 `https://api.evolink.ai/v1`
- ✅ `THIRD_PARTY_MODEL_NAME`: 默认 `gemini-2.5-pro`

### 3. 创建了测试脚本 ✅

- ✅ `tests/test_api_connection.py`: 快速验证API连接
- ✅ `tests/test_real_llm.py`: 完整的LLM功能测试

---

## 🚀 如何使用

### 步骤1: 配置环境变量

在`.env`文件中添加：

```ini
# 第三方API配置
OPENAI_API_KEY=your_api_key_here
THIRD_PARTY_BASE_URL=https://api.evolink.ai/v1
THIRD_PARTY_MODEL_NAME=gemini-2.5-pro
```

### 步骤2: 激活虚拟环境

```bash
cd /Users/zhangyu/project/germany_latest/tj_germany
source venv/bin/activate
```

### 步骤3: 快速测试API连接

```bash
python tests/test_api_connection.py
```

**预期输出**:
```
==========================================================
第三方API连接测试
==========================================================

【步骤1: 检查环境变量】
✅ 配置加载成功
   - API Base URL: https://api.evolink.ai/v1
   - 模型名称: gemini-2.5-pro
   - API Key: 已配置

【步骤2: 初始化LLM客户端】
✅ LLM客户端初始化成功

【步骤3: 测试API连接】
🔄 发送测试请求...
✅ API调用成功！

回复内容:
   我是一个大型语言模型...

==========================================================
✅ 所有测试通过！第三方API连接正常！
==========================================================
```

### 步骤4: 运行完整LLM测试

```bash
python tests/test_real_llm.py
```

这将测试：
- ✅ 意图判断准确性（4个用例）
- ✅ 问题分类准确性（5个用例）
- ✅ 参数提取准确性（2个用例）

---

## 📋 .env文件示例

```ini
# ========== 第三方API配置 ==========
# 必填项
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx

# 可选项（有默认值）
THIRD_PARTY_BASE_URL=https://api.evolink.ai/v1
THIRD_PARTY_MODEL_NAME=gemini-2.5-pro

# ========== Milvus配置 ==========
MILVUS_MODE=lite

# ========== Embedding配置 ==========
EMBEDDING_MODE=openai
OPENAI_EMBEDDING_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx

# ========== 数据配置 ==========
DATA_MODE=PART
PART_DATA_YEARS=2019,2020,2021
```

---

## ⚠️ 故障排查

### 问题1: API Key错误

**错误信息**:
```
❌ API调用失败: Invalid API key
```

**解决方案**:
1. 检查`.env`文件中的`OPENAI_API_KEY`
2. 确认API Key有效且有额度
3. 重新加载环境：`source venv/bin/activate`

### 问题2: 网络连接问题

**错误信息**:
```
❌ API调用失败: Connection timeout
```

**解决方案**:
1. 检查网络连接
2. 确认API端点可访问：`curl https://api.evolink.ai/v1`
3. 检查防火墙设置

### 问题3: 模型名称错误

**错误信息**:
```
❌ API调用失败: Model not found
```

**解决方案**:
1. 确认模型名称正确：`THIRD_PARTY_MODEL_NAME=gemini-2.5-pro`
2. 查看第三方API支持的模型列表
3. 更新`.env`文件中的模型名称

---

## 🔧 代码迁移指南

如果您的现有代码使用了旧版本的`invoke`方法（传消息列表），需要修改：

### 修改前 ❌
```python
messages = [{'role': 'user', 'content': '问题'}]
response = client.invoke(messages, system_prompt="...")
```

### 修改后 ✅

**选项1: 使用新的字符串API**
```python
response = client.invoke("问题", system_prompt="...")
```

**选项2: 使用多轮对话API**
```python
messages = [{'role': 'user', 'content': '问题'}]
response = client.invoke_with_messages(messages, system_prompt="...")
```

---

## 📊 测试结果示例

运行`test_real_llm.py`后，您应该看到：

```
🚀 真实LLM测试 - 意图识别和问题分类验证
================================================================================

🔍 检查LLM连接...
✅ LLM连接成功

【测试1: 意图判断准确性】
--- 测试用例 1 ---
问题: 2019年德国议会讨论了哪些主要议题？
预期意图: simple
🔄 调用LLM进行意图判断...
✅ LLM返回成功
判断结果: simple
验证: ✅ PASS

...

📊 最终测试报告
================================================================================
INTENT: 通过率: 3/4 (75.0%)
CLASSIFY: 通过率: 4/5 (80.0%)
EXTRACT: 通过率: 2/2 (100.0%)

总体通过率: 9/11 (81.8%)

🎉 测试结果良好！Prompt效果符合预期。
```

---

## ✅ 验证清单

在运行完整测试前，请确认：

- [ ] `.env`文件存在且配置了`OPENAI_API_KEY`
- [ ] 虚拟环境已激活：`source venv/bin/activate`
- [ ] API连接测试通过：`python tests/test_api_connection.py`
- [ ] 网络连接正常
- [ ] API额度充足

---

## 📝 相关文件

| 文件 | 说明 |
|------|------|
| `src/llm/client.py` | LLM客户端（已更新） |
| `src/config/settings.py` | 配置管理（已支持第三方API） |
| `tests/test_api_connection.py` | API连接快速测试 |
| `tests/test_real_llm.py` | 完整LLM功能测试 |
| `.env` | 环境变量配置文件 |

---

**更新完成！** ✅

现在您可以使用第三方API进行测试了：

```bash
source venv/bin/activate
python tests/test_api_connection.py
python tests/test_real_llm.py
```

