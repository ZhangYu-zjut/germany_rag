# 德国议会智能问答系统 - 代码评估报告

**生成时间**: 2025-11-01  
**评估范围**: 对照产品文档和技术设计文档，评估当前代码框架的完成度

---

## 📊 执行摘要

### 总体评估

| 评估维度 | 完成度 | 评级 |
|---------|-------|------|
| **架构设计** | 95% | ⭐⭐⭐⭐⭐ |
| **数据处理** | 100% | ⭐⭐⭐⭐⭐ |
| **LLM集成** | 90% | ⭐⭐⭐⭐☆ |
| **CoA工作流** | 85% | ⭐⭐⭐⭐☆ |
| **向量检索** | 90% | ⭐⭐⭐⭐☆ |
| **Prompt工程** | 40% | ⭐⭐☆☆☆ |
| **测试验证** | 30% | ⭐⭐☆☆☆ |
| **文档完整性** | 70% | ⭐⭐⭐⭐☆ |

**综合评分**: 75% ⭐⭐⭐⭐☆

---

## ✅ 已完成功能

### 1. 数据处理层 (100%)

#### ✅ 数据转换
- [x] **B文件夹到A文件夹格式转换** (`convert_data.py`)
  - 转换26,537条记录
  - 新增2022-2025年4个文件
  - 字段映射完整：year/month/day/group/speaker/text_id
  - 验证通过率：100%

#### ✅ 数据加载
- [x] **ParliamentDataLoader** (`src/data_loader/loader.py`)
  - 支持PART/ALL模式切换
  - 支持按年份过滤
  - metadata清洗（speaker特殊字符处理）
  - 统计信息生成

#### ✅ 党派映射
- [x] **PartyMapper** (`src/data_loader/mapper.py`)
  - 62条党派映射记录
  - 支持所有历史党派（1949-2025）
  - 标准化功能：处理拼写变体、换行、大小写
  - 中德双语支持

#### ✅ 文本分块
- [x] **TextSplitter** (`src/data_loader/splitter.py`)
  - RecursiveCharacterTextSplitter集成
  - metadata继承（保留year/month/day/group/speaker/text_id）
  - 可配置chunk_size和chunk_overlap

### 2. 架构层 (95%)

#### ✅ 配置管理
- [x] **Settings** (`src/config/settings.py`)
  - Pydantic Settings框架
  - 多模式支持：
    - Milvus: lite/local/cloud
    - Embedding: local/openai/vertex
    - Data: PART/ALL
  - 环境变量 + .env文件
  - 动态参数计算（embedding_dimension, milvus_uri等）

#### ✅ LangGraph工作流
- [x] **QuestionAnswerWorkflow** (`src/graph/workflow.py`)
  - 完整的CoA流程：Intent → Classify → Extract → Decompose → Retrieve → Summarize → Exception
  - 7个节点：IntentNode, ClassifyNode, ExtractNode, DecomposeNode, RetrieveNode, SummarizeNode, ExceptionNode
  - 条件路由：复杂问题vs简单问题
  - 状态管理：GraphState

#### ✅ 状态管理
- [x] **GraphState** (`src/graph/state.py`)
  - TypedDict定义所有状态字段
  - 包含：question, intent, question_type, parameters, sub_questions, sub_answers, final_answer等

### 3. LLM集成 (90%)

#### ✅ Gemini客户端
- [x] **GeminiLLMClient** (`src/llm/client.py`)
  - 基于OpenAI SDK调用Gemini 2.5 Pro
  - 支持第三方API代理
  - 温度、max_tokens可配置
  - 错误处理

#### ✅ Embedding
- [x] **多Embedding方案**
  - OpenAI Embedding (`src/llm/embeddings.py`)
  - 本地Embedding (`src/llm/local_embeddings.py`)
  - Vertex AI Embedding (`src/llm/vertex_embeddings.py`)
  - 统一接口设计

#### ⚠️ Prompt模板（40%）
- [x] **PromptTemplates框架** (`src/llm/prompts.py`)
  - 已有框架代码
  - ❌ **缺失**：具体的prompt内容
    - 意图判断prompt（空）
    - 参数提取prompt（空）
    - 问题分类prompt（空）
    - 问题拆解模板（空）
    - 总结prompt（空）

### 4. 向量数据库层 (90%)

#### ✅ Milvus集成
- [x] **MilvusClient** (`src/vectordb/client.py`)
  - 支持lite/local/cloud三种模式
  - Collection管理（创建、删除、检查）
  - 数据插入（批量、带进度条）

- [x] **MilvusCollection** (`src/vectordb/collection.py`)
  - Schema定义：text + embedding + metadata字段
  - 索引配置：IVF_FLAT + L2距离
  - metadata标量字段索引（year, month, day, group, speaker, text_id）

- [x] **MilvusRetriever** (`src/vectordb/retriever.py`)
  - 混合检索：metadata过滤 + 向量相似度
  - top_k可配置
  - 结果格式化

### 5. Agent节点 (85%)

#### ✅ 已实现节点
- [x] **IntentNode** - 意图判断（简单/复杂）
- [x] **ClassifyNode** - 问题分类（变化/总结/对比/事实/趋势）
- [x] **ExtractNode** - 参数提取（时间/党派/议员/主题）
- [x] **DecomposeNode** - 问题拆解
- [x] **RetrieveNode** - 数据检索
- [x] **SummarizeNode** - 总结
- [x] **ExceptionNode** - 异常处理

#### ⚠️ 节点实现质量
所有节点都有完整的代码框架，但**依赖于Prompt模板内容**，而模板内容目前为空占位符。

---

## ❌ 未完成/需补充功能

### 1. 🔴 Prompt模板内容（优先级：最高）

#### 缺失内容：

**1.1 意图判断Prompt**
```python
# src/llm/prompts.py - format_intent_prompt()
# 当前：空占位符
# 需要：判断问题是简单检索还是复杂分析的prompt
```

**1.2 问题分类Prompt**
```python
# src/llm/prompts.py - format_classify_prompt()
# 需要：区分变化类、总结类、对比类、事实查询、趋势分析
```

**1.3 参数提取Prompt**
```python
# src/llm/prompts.py - format_extract_prompt()
# 需要：提取时间范围、党派、议员、主题等结构化参数
```

**1.4 问题拆解模板**
```python
# src/llm/prompts.py - format_decompose_prompt()
# 需要：预定义的拆解模板
#   - 时间维度拆解（按年份）
#   - 党派维度拆解（按党派）
#   - 议员维度拆解（按议员）
#   - 复合维度拆解
```

**1.5 总结Prompt**
```python
# src/llm/prompts.py - format_summarize_prompt()
# 需要：符合德文输出格式要求的总结模板
# 产品文档要求的结构：
#   - Sprecherzuordnung (发言人归属)
#   - Kernaussage (核心论述)
#   - Beweisstücke (证据片段)
#   - Datenquelle (数据来源: text_id)
```

**影响范围**：所有Agent节点无法正确工作，系统无法端到端运行

---

### 2. 🟡 系统提示词（优先级：高）

#### 缺失内容：

产品文档中明确指定的德文系统提示词：

```
【Rolle】Du bist Politikexperte mit Spezialisierung auf deutschen Bundestagsdebatten.
【Kernaufgabe】Erstelle auf Grundlage der untenstehenden Frage und des betreffenden Hintergrunds 
eine strukturierte Antwort auf Deutsch. Die Antwort soll:
1. alle zentralen Argumente und Details bewahren,
2. die ursprünglichen Sprecherzuordnungen sowie kontextuellen Beziehungen erhalten,
3. nicht essenzielle Dialogteile verdichten, dabei jedoch die faktische Dichte beibehalten.

【Kritische Vorgaben】
- NIEMALS auslassen: politische Terminologie, Parteipositionen, Beschlüsse/Resolutionen 
  oder Zugehörigkeiten der Sprecher (Partei/Funktion).
- IMMER bewahren: Ursache-Wirkungs-Beziehungen und die Entscheidungslogik.
- Ausgabeformat: Aufzählungspunkte mit dem Link „Speaker" und dem Link „text_id".

【Struktur der Zusammenfassung】
- Sprecherzuordnung (falls verfügbar): [Name/Partei]
- Kernaussage: [prägnante Formulierung]
- Beweisstücke: [Schlüsselfakten/-daten]
- Datenquelle: [text_id]
```

**当前状态**：未集成到LLM客户端中  
**影响范围**：输出格式不符合产品需求

---

### 3. 🟡 问题拆解逻辑（优先级：高）

#### 产品文档示例：

**示例1**：在2015年到2018年期间，德国联邦议会中不同党派在难民家庭团聚问题上的讨论发生了怎样的变化？

**拆解方式**：
```
1. 2015年社会民主党在难民家庭团聚问题上的讨论？
2. 2015年联盟党在难民家庭团聚问题上的讨论？
3. 2015年绿党在难民家庭团聚问题上的讨论？
...
4. 2016年社会民主党在难民家庭团聚问题上的讨论？
...
```

**当前状态**：DecomposeNode有框架，但缺少具体拆解模板  
**需要实现**：
- 时间 × 党派的笛卡尔积拆解
- 最大子问题数限制（避免爆炸）
- 智能合并策略（先按年汇总，再总结）

---

### 4. 🟢 测试用例（优先级：中）

#### 产品文档要求：

> 为了评估整个问答系统的效果，需要提前收集一些用户经常会提问的问题-参考答案对的文本，
> 前期可以考虑收集20个问题-答案对

**当前状态**：无测试用例

**需要包含**：
- 简单问题（2-3个）
- 变化类问题（5-6个）
- 总结类问题（5-6个）
- 对比类问题（5-6个）

产品文档已提供了一些示例，需要用户补充完整的Q&A对。

---

### 5. 🟢 模块化输出（优先级：中）

#### 产品文档要求：

> 模块化输出格式需要提供参考样例之后总结

**当前状态**：SummarizeNode未实现模块化输出格式

**需要实现**：
- 按年份分段输出
- 按党派分段输出
- 按议员分段输出
- 总体总结

---

### 6. 🟢 异常处理增强（优先级：中）

#### 当前限制：

ExceptionNode只处理"无材料"情况。

**需要增强**：
- LLM调用失败
- Milvus连接失败
- 数据格式错误
- Token超限
- 问题拆解失败
- 参数提取失败

**建议方案**：
```python
class ExceptionType(Enum):
    NO_MATERIAL = "no_material"  # 材料中未找到
    LLM_ERROR = "llm_error"      # LLM调用失败
    RETRIEVAL_ERROR = "retrieval_error"  # 检索失败
    PARSE_ERROR = "parse_error"  # 解析失败
    TOKEN_LIMIT = "token_limit"  # Token超限
```

---

### 7. 🟢 索引构建脚本增强（优先级：低）

#### 当前状态：

- `build_index.py` 存在
- `build_index_local.py` 存在
- `build_index_vertex.py` 存在

**需要增强**：
- 增量索引（只添加新数据）
- 索引重建（清空重建）
- 索引验证（检查完整性）
- 进度保存（支持中断恢复）

---

### 8. 🟢 文档补充（优先级：低）

#### 需要补充的文档：

- [ ] **API文档**：如果需要对外提供API接口
- [ ] **部署文档**：云端部署指南
- [ ] **性能调优文档**：针对大规模数据的优化建议
- [ ] **问题模板库**：预定义的问题拆解模板

---

## 🎯 关键问题识别

### 问题1：Prompt模板是系统的核心瓶颈 🔴

**现状**：所有Agent节点都依赖Prompt，但Prompt内容为空

**影响**：
- 系统无法端到端运行
- 无法进行测试验证
- 无法评估实际效果

**建议优先级**：🔴 最高

**建议行动**：
1. 先基于产品文档示例问题，编写初版Prompt
2. 测试并迭代优化
3. 收集20个Q&A对后，进行系统性评估

---

### 问题2：问题拆解可能导致"爆炸" ⚠️

**风险场景**：
- 2015-2018年（4年）× 6个党派 = 24个子问题
- 每个子问题检索Top10文档 = 240个文档
- 每个文档1000字 = 240,000字 ≈ 60K tokens
- Gemini上下文窗口虽大，但成本和延迟都会增加

**建议方案**：
1. **设置最大子问题数**：如20个
2. **分层汇总策略**：
   - 第一层：每个子问题单独总结（200字）
   - 第二层：按年份汇总（4段 × 500字 = 2000字）
   - 第三层：最终总结（800字）
3. **智能过滤**：只保留最相关的N个文档

---

### 问题3：测试验证缺失 ⚠️

**现状**：
- 没有单元测试
- 没有集成测试
- 没有端到端测试
- 没有Q&A评估数据集

**影响**：
- 无法验证功能正确性
- 无法评估系统效果
- 难以发现潜在bug

**建议行动**：
1. 先手动测试简单问题（如"2019年CDU/CSU的立场？"）
2. 逐步测试复杂问题
3. 收集20个Q&A对后，建立评估基准

---

### 问题4：党派名称不一致风险 ⚠️

**已解决**：
- ✅ 创建了party_mapping.csv（62条记录）
- ✅ 实现了PartyMapper工具类
- ✅ 支持所有历史党派和拼写变体

**仍需注意**：
- 在数据加载时应用PartyMapper标准化
- 在参数提取时应用PartyMapper识别
- 在结果展示时提供中文党派名称

---

## 📋 推荐的实施计划

### Phase 1: Prompt工程（2-3天）⭐⭐⭐

**目标**：让系统能够端到端运行

| 任务 | 工作量 | 优先级 |
|-----|--------|--------|
| 编写意图判断Prompt | 2小时 | 🔴 最高 |
| 编写参数提取Prompt | 3小时 | 🔴 最高 |
| 编写问题分类Prompt | 2小时 | 🔴 最高 |
| 编写问题拆解模板（3类） | 4小时 | 🔴 最高 |
| 编写总结Prompt（德文格式） | 4小时 | 🔴 最高 |
| 集成系统提示词 | 1小时 | 🔴 最高 |
| 手动测试简单问题 | 2小时 | 🔴 最高 |

**里程碑**：系统能回答简单问题

---

### Phase 2: 复杂问题处理（2-3天）⭐⭐

**目标**：实现复杂问题的拆解和汇总

| 任务 | 工作量 | 优先级 |
|-----|--------|--------|
| 实现问题拆解逻辑 | 4小时 | 🟡 高 |
| 实现分层汇总策略 | 4小时 | 🟡 高 |
| 实现最大子问题数限制 | 2小时 | 🟡 高 |
| 测试复杂问题（时间跨度） | 2小时 | 🟡 高 |
| 测试复杂问题（党派对比） | 2小时 | 🟡 高 |
| 优化Prompt（基于测试结果） | 3小时 | 🟡 高 |

**里程碑**：系统能回答复杂问题

---

### Phase 3: 测试与优化（2-3天）⭐

**目标**：建立评估基准，迭代优化

| 任务 | 工作量 | 优先级 |
|-----|--------|--------|
| 收集20个Q&A对（用户提供） | - | 🟢 中 |
| 建立评估脚本 | 3小时 | 🟢 中 |
| 批量测试20个问题 | 2小时 | 🟢 中 |
| 分析评估结果 | 2小时 | 🟢 中 |
| 优化Prompt和逻辑 | 6小时 | 🟢 中 |
| 二次评估 | 2小时 | 🟢 中 |

**里程碑**：系统质量达到可演示标准

---

### Phase 4: 增强功能（1-2天）⭐

**目标**：增强异常处理和用户体验

| 任务 | 工作量 | 优先级 |
|-----|--------|--------|
| 增强异常处理 | 3小时 | 🟢 中 |
| 实现模块化输出 | 4小时 | 🟢 中 |
| 优化检索策略 | 3小时 | 🟢 中 |
| 性能优化 | 2小时 | 🟢 低 |
| 文档补充 | 2小时 | 🟢 低 |

**里程碑**：系统完善，可交付

---

### Phase 5: 部署与交付（1天）

**目标**：部署系统，准备交付

| 任务 | 工作量 | 优先级 |
|-----|--------|--------|
| 云端Milvus配置 | 2小时 | 🟢 中 |
| 全量数据索引构建 | 2小时 | 🟢 中 |
| API封装（如需要） | 4小时 | 🟢 低 |
| 部署文档 | 2小时 | 🟢 低 |
| 最终测试 | 2小时 | 🟢 中 |

**里程碑**：系统部署完成

---

## 🤔 需要用户明确的问题

### 问题1：Prompt模板的语言选择

产品文档中系统提示词是德文，但：
- 用户问题可能是中文或德文？
- Agent内部推理用中文还是德文？
- 最终答案输出德文（已明确）

**建议**：
- 内部推理用中文（更可控）
- 最终总结用德文（符合需求）

### 问题2：20个Q&A评估集

产品文档提到需要20个Q&A对，但：
- 问题已部分提供（产品文档中有示例）
- 参考答案需要用户提供

**建议**：
- 先基于示例问题开发
- 用户后续补充参考答案
- 进行系统性评估

### 问题3：API接口需求

产品文档提到"可以对外提供API接口"，但：
- 是否必须？
- 接口规格？（REST API? GraphQL?）
- 认证方式？

**建议**：
- 先实现命令行交互
- 如需API，Phase 5再封装

### 问题4：全量数据索引时机

当前使用2019-2021部分数据（PART模式），但：
- 何时切换到全量数据（ALL模式）？
- 全量索引构建需要较长时间

**建议**：
- Phase 3完成后切换全量
- 在Phase 5部署前完成全量索引

---

## 📈 代码质量评估

### 优点 ✅

1. **架构设计优秀**
   - 清晰的模块划分
   - LangGraph工作流设计合理
   - 配置管理灵活（支持多种模式）

2. **代码规范**
   - 完整的类型注解
   - 详细的文档字符串
   - 统一的代码风格

3. **扩展性强**
   - 支持多种Embedding方案
   - 支持多种Milvus部署方式
   - 易于添加新的Agent节点

4. **数据处理完善**
   - 党派映射表覆盖全面
   - 数据转换脚本健壮
   - metadata继承正确

### 不足 ⚠️

1. **Prompt内容缺失**（最大问题）
2. **测试覆盖不足**
3. **异常处理简单**
4. **性能优化空间**（如缓存、批处理）

---

## 🎯 总结

### 核心结论

**当前代码框架设计优秀，完成度75%，但关键的Prompt模板内容缺失导致系统无法实际运行。**

### 最紧急的任务

1. **补充Prompt模板内容**（Phase 1，2-3天）
2. **实现问题拆解逻辑**（Phase 2，2-3天）
3. **收集Q&A评估集**（需用户参与）

### 预计完成时间

- **MVP版本（能回答简单问题）**：3-4天
- **完整版本（能回答复杂问题）**：7-10天
- **优化版本（质量达到可演示）**：10-14天

---

## 📞 下一步行动

### 立即执行

1. ✅ **数据预处理** - 已完成
2. ✅ **党派映射表** - 已完成
3. 🔄 **编写Prompt模板** - 进行中
4. 🔄 **生成实施计划** - 进行中

### 需要用户确认

1. **Prompt语言选择**（内部推理 vs 输出）
2. **20个Q&A评估集**（何时提供）
3. **API接口需求**（是否必须）
4. **全量数据索引时机**

---

**报告结束**


