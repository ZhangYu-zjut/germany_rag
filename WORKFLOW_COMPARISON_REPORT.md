# 完整Workflow vs 简化脚本对比报告

## 测试配置

- **测试时间**: 2025-11-06 18:06:43
- **数据范围**: 2015年德国议会数据
- **Workflow**: LangGraph CoA (Chain of Agents)
- **ReRank**: Cohere rerank-v3.5
- **Embedding**: BGE-M3 (local, 1024-dim)
- **Vector DB**: Pinecone (german-bge index)

## 测试结果对比

### Q1: 总结类

**问题**: 请总结2015年德国议会关于难民政策的主要讨论内容

**状态**: ❌ 失败

**错误**: 'NoneType' object is not iterable

---

### Q2: 对比类

**问题**: CDU/CSU和SPD在2015年对难民政策的立场有什么不同？

**状态**: ❌ 失败

**错误**: 'NoneType' object is not iterable

---

### Q3: 观点类

**问题**: 2015年德国议会议员对欧盟一体化的主要观点是什么？

**状态**: ❌ 失败

**错误**: 'NoneType' object is not iterable

---

### Q4: 事实查询

**问题**: 2015年德国议会有哪些重要法案被讨论？

**状态**: ❌ 失败

**错误**: 'NoneType' object is not iterable

---

## 总体对比

### 完整Workflow优势

1. **多阶段处理**: 意图分析 → 分类 → 参数提取 → 分解 → 检索 → ReRank → 总结
2. **ReRank优化**: Cohere API重新排序文档，提升相关性
3. **子问题分解**: 复杂问题拆分为多个子问题，检索更精准
4. **参数提取**: 自动提取年份、党派、发言人等过滤条件

### 简化脚本特点

1. **直接检索**: 问题 → Embedding → Pinecone查询 → LLM生成
2. **无ReRank**: 直接使用向量相似度排序
3. **固定top_k**: 检索固定数量文档（10个）
4. **简单快速**: 适合简单问题，耗时更短

### 性能对比

| 指标 | 完整Workflow | 简化脚本 |
|------|-------------|--------|
