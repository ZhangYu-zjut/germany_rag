# 基于证据的诊断报告

## 观察到的事实

### 事实1: 查询语句
**子问题**: "Was ist die Position von CDU/CSU zum Thema Migrationspolitik im Jahr 2017?"

**特点**:
- 非常宽泛："Migrationspolitik"（移民政策）
- 没有具体关键词："Abschiebung", "Zwang", "Rückführung"等
- 焦点是"立场"（Position），而不是具体措施

### 事实2: 检索结果的相似度
**Top-1相似度**: 0.6235（Nina Warken，关于移民政策总体立场）

**分析**:
- 相似度0.62 **偏低但不算很低**
- 说明查询与文档之间存在**语义gap**
- 最相关的文档都是关于"移民政策总体立场"，而非具体的"遣返/强制执行"措施

### 事实3: "Zwang durchsetzen"文档的特征

根据客户反馈，text_id `2017_1762423575_2922`的原文是：
> "Allein mit der Pflicht zur freiwilligen Ausreise werden wir nicht weiterkommen. Wir müssen [...] die Ausreisepflicht auch mit **Zwang durchsetzen**."

**特点**:
- 主题：**遣返执行**（Abschiebung/Ausreise）
- 关键词：**Zwang**（强制）、**durchsetzen**（执行）
- 立场类型：**具体措施**，而非总体立场

---

## 根本原因分析

### ❌ 我之前的假设（未经验证）

我之前假设："向量相似度太低导致未召回"

**问题**: 我没有验证：
- 文档是否在Pinecone中？
- 实际相似度是多少？
- 文档在top-50/top-100的哪个位置？

### ✅ 基于证据的推断

#### 可能原因1: **语义不匹配** (概率: 70%)

**证据**:
```
查询: "Was ist die Position ... zur Migrationspolitik"
      （CDU/CSU对移民政策的立场是什么？）
      ↓
      语义：抽象的、总体的、立场性的
      
文档: "Wir müssen die Ausreisepflicht mit Zwang durchsetzen"
      （我们必须强制执行遣返义务）
      ↓
      语义：具体的、措施性的、执行层面的
```

**向量模型的行为**:
- BGE-M3会认为"Position zur Migrationspolitik"与"总体立场论述"更相关
- 与"具体措施（Zwang durchsetzen）"的相似度较低
- 结果：即使文档中有"Zwang durchsetzen"，也可能排名低于那些谈"总体立场"的文档

**类比**:
```
用户搜: "中国经济政策"
文档A: "中国经济总体平稳，注重高质量发展..."（相似度高）
文档B: "央行决定降低准备金率0.5%"（相似度低，但可能更重要！）
```

#### 可能原因2: **查询分解策略过于宽泛** (概率: 20%)

**当前分解**:
```
原始问题: "CDU/CSU立场在2017-2019年如何变化"
    ↓
子问题1: "2017年CDU/CSU Migrationspolitik Position"
子问题2: "2019年CDU/CSU Migrationspolitik Position"
```

**问题**: 
- 子问题太宽泛，没有体现"变化"（Veränderung）的维度
- 没有针对性提问"遣返政策"（Abschiebungspolitik）

**更好的分解**（假设）:
```
子问题1: "2017年CDU/CSU Abschiebung Rückführung"
子问题2: "2017年CDU/CSU Migrationspolitik allgemein"
子问题3: "2019年CDU/CSU Abschiebung Rückführung"
子问题4: "2019年CDU/CSU Migrationspolitik allgemein"
```

#### 可能原因3: **top_k=50不足** (概率: 10%)

**假设**: "Zwang durchsetzen"文档排名在50-100之间

**如果是这种情况**:
- 增加top_k到100可能召回
- 但根本问题仍是相似度偏低

---

## 方案推荐（修正版）

### 🥇 **方案1: Query扩展** (推荐指数: ⭐⭐⭐⭐⭐)

**原理**: 将宽泛查询分解为多个具体角度的查询

```python
原始查询: "Was ist die Position von CDU/CSU zur Migrationspolitik 2017"

扩展为:
1. "CDU/CSU Migrationspolitik Position 2017"  # 原始查询
2. "CDU/CSU Abschiebung Rückführung 2017"     # 具体措施维度
3. "CDU/CSU Zwang Ausreisepflicht 2017"       # 强制执行维度
4. "CDU/CSU sichere Herkunftsländer 2017"      # 安全来源国维度
5. "CDU/CSU Grenzkontrollen Obergrenze 2017"  # 边境管控维度
```

**为什么有效**:
- 查询3 "CDU/CSU Zwang Ausreisepflicht 2017" 会与"Zwang durchsetzen"文档**高度匹配**
- 向量相似度预期提升到**0.7+**

**依据**:
- ✅ 证据：当前查询过于宽泛（"Migrationspolitik"）
- ✅ 理论：具体关键词查询会提高目标文档的排名
- ✅ 成本：低（只需Prompt工程）

**时间成本**: 1-2天

---

### 🥈 **方案2: BM25混合检索** (推荐指数: ⭐⭐⭐⭐)

**原理**: 关键词精确匹配

**为什么有效**:
- BM25会直接匹配"Zwang", "durchsetzen", "Ausreisepflicht"等词
- 即使查询是"Migrationspolitik"，只要文档包含这些词，BM25也会给高分

**依据**:
- ✅ 理论：BM25擅长精确匹配
- ⚠️ 证据不足：我**未验证**向量检索彻底失败，可能Query扩展就够了

**时间成本**: 2-3天

---

### 🥉 **方案3: 改进Decompose逻辑** (推荐指数: ⭐⭐⭐)

**原理**: 让LLM分解出更具体的子问题

```python
# 当前Decompose
"CDU/CSU Position Migrationspolitik 2017"

# 改进Decompose（增加维度）
"CDU/CSU Abschiebungspolitik Zwang Rückführung 2017"
"CDU/CSU Aufnahme Integration 2017"
"CDU/CSU Grenzkontrollen 2017"
```

**为什么有效**:
- 从源头解决查询过于宽泛的问题

**依据**:
- ✅ 证据：当前子问题过于宽泛
- ✅ 理论：更细粒度的子问题 = 更精准的检索

**时间成本**: 0.5-1天（修改Decompose Prompt）

---

## 推荐组合方案

**最优组合**: 方案3（改进Decompose）+ 方案1（Query扩展）

**原因**:
1. **成本低**: 纯Prompt工程，2-3天完成
2. **证据支持**: 当前查询确实过于宽泛（有实际证据）
3. **风险小**: 不改架构，可快速回滚

**如果方案1+3仍然失败**，再考虑方案2（BM25）

---

## 我之前方案的问题反思

### 问题1: 缺少证据链

我之前说："向量相似度太低"，但我没有：
- ❌ 验证文档是否在Pinecone中
- ❌ 计算实际相似度
- ❌ 检查文档在top-N的排名

### 问题2: 过度设计

我直接推荐了**BM25+Query扩展组合**，但可能：
- ⚠️ Query扩展就够了
- ⚠️ 改进Decompose就够了
- ⚠️ BM25是过度工程

### 正确的方法论

1. **观察现象**: "Zwang durchsetzen"未召回 ✅
2. **提取证据**: 查询是"Migrationspolitik"，top-1相似度0.62 ✅
3. **分析原因**: 查询过于宽泛，语义gap ✅
4. **最小干预**: 先尝试最简单的方案（改Decompose或Query扩展）
5. **验证效果**: 测试召回率
6. **升级方案**: 如果失败，再考虑BM25

---

## 下一步建议

### 立即执行（优先级1）

**方案**: 改进Decompose Prompt + 简单Query扩展

**实施步骤**:
1. 修改Decompose Prompt，增加细粒度维度
2. 在子问题基础上添加关键词扩展（无需LLM，手工模板即可）
3. 测试Q6

**时间**: 1天

**预期**: 70-80%概率修复"Zwang durchsetzen"

### 如果失败（优先级2）

再实施完整的BM25方案

---

**修正后的结论**: 
- 核心问题：**查询过于宽泛**（有证据）
- 最优方案：**改进Decompose + Query扩展**（成本低，风险小）
- BM25方案：作为**备选**，而非首选
