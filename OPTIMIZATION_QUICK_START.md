# 性能优化快速上手指南

## 已实施的优化 (2025-11-10)

### ✅ 优化1: 并行化Retrieve (预计加速8-10倍)

**修改文件**:
1. `src/vectordb/pinecone_retriever.py` - 新增`search_multi_year_parallel()`
2. `src/graph/nodes/retrieve_pinecone.py:245` - 调用并行版本

**关键代码**:
```python
# 并行查询所有年份
with ThreadPoolExecutor(max_workers=20) as executor:
    futures = [executor.submit(query_single_year, year) for year in years]
    results = [f.result() for f in futures]
```

---

### ✅ 优化2: 分层模型选择 (预计节省4-5分钟)

**修改文件**:
- `src/graph/workflow.py:66-76` - 创建Flash客户端并传给节点

**关键代码**:
```python
flash_client = GeminiLLMClient(model="gemini-2.5-flash")
self.intent_node = IntentNode(llm_client=flash_client)
self.classify_node = ClassifyNode(llm_client=flash_client)
self.extract_node = ExtractNode(llm_client=flash_client)
```

---

## 测试验证

### 快速测试 (2个问题, ~5分钟)
```bash
source venv/bin/activate
python test_optimization.py
```

### 完整测试 (7个问题, ~15-20分钟)
```bash
source venv/bin/activate
python test_langgraph_complete.py
```

---

## 预期效果

| 问题 | 优化前 | 优化后 | 加速比 |
|------|--------|--------|--------|
| Q1 (10年) | 1145秒 | 80-120秒 | 9.5-14x |
| Q4 (4年) | 416秒 | 35-50秒 | 8-12x |
| 7题总计 | 39分钟 | 3.8-5.3分钟 | 7.5-10.5x |

---

## 回滚方法 (如果需要)

### 回滚并行化
```python
# src/graph/nodes/retrieve_pinecone.py:245
# 改回串行版本
results = self.retriever.search_multi_year(...)  # 去掉_parallel
```

### 回滚模型选择
```python
# src/graph/workflow.py:74-76
# 不传llm_client,使用默认Pro模型
self.intent_node = IntentNode()
self.classify_node = ClassifyNode()
self.extract_node = ExtractNode()
```

---

## 故障排查

### 问题1: 并行查询失败
**症状**: `PineconeRetriever] ✗ XXXX年检索失败`
**原因**: Pinecone限流或网络问题
**解决**: 降低并发数
```python
# src/vectordb/pinecone_retriever.py:280
max_workers = min(len(years), 10)  # 从20降到10
```

### 问题2: Flash模型准确率低
**症状**: Extract阶段参数提取错误
**解决**: 该节点切回Pro模型
```python
# src/graph/workflow.py:76
self.extract_node = ExtractNode()  # 不传flash_client
```

### 问题3: 答案质量下降
**检查点**:
1. 是否包含Quellen格式?
2. 年份分布是否正确?
3. 答案长度是否合理?

**对比工具**:
```bash
# 对比优化前后的答案
diff 11-07测试结果/test_AFTER_QUELLEN_FIX.log new_test.log
```

---

## 监控指标

### 性能指标
- ✅ 总耗时 <300秒 (7题)
- ✅ Q1耗时 <120秒
- ✅ Retrieve节点 <20%总耗时

### 质量指标
- ✅ 所有答案包含`**Quellen**`
- ✅ 年份分布符合预期
- ✅ 答案长度 >3000字符

---

## 详细文档

- 完整实施报告: `OPTIMIZATION_IMPLEMENTATION.md`
- 性能分析: `11-07测试结果/PERFORMANCE_ANALYSIS_REPORT.md`
- Q1 vs Q5分析: `11-07测试结果/Q1_Q5_PERFORMANCE_MYSTERY_SOLVED.md`
