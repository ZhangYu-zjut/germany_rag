# 德国议会智能问答系统 - 实施落地计划

**制定时间**: 2025-11-01  
**计划周期**: 10-14天  
**当前状态**: 数据预处理完成，进入核心功能开发阶段

---

## 📊 项目总览

### 当前进度

```
数据预处理 ████████████████████ 100% ✅
架构搭建   ████████████████████ 95%  ✅
Prompt工程 ████░░░░░░░░░░░░░░░░ 20%  🔄
测试验证   ██░░░░░░░░░░░░░░░░░░ 10%  🔄
系统优化   ░░░░░░░░░░░░░░░░░░░░ 0%   ⏳
部署交付   ░░░░░░░░░░░░░░░░░░░░ 0%   ⏳
```

### 里程碑计划

| 里程碑 | 预计完成时间 | 状态 |
|-------|------------|------|
| M1: 数据预处理完成 | Day 1 | ✅ 已完成 |
| M2: 简单问题可回答 | Day 4 | 🔄 进行中 |
| M3: 复杂问题可回答 | Day 7 | ⏳ 待开始 |
| M4: 系统可演示 | Day 10 | ⏳ 待开始 |
| M5: 系统可交付 | Day 14 | ⏳ 待开始 |

---

## 📅 详细实施计划

### Phase 1: Prompt工程与简单问题处理 (Day 2-4)

**目标**: 让系统能够回答简单查询问题

#### Day 2: 核心Prompt开发

| 时间 | 任务 | 产出 | 负责人 |
|-----|------|------|--------|
| 上午 | 编写意图判断Prompt | `format_intent_prompt()`完整实现 | 开发 |
| 上午 | 编写参数提取Prompt | `format_extract_prompt()`完整实现 | 开发 |
| 下午 | 编写问题分类Prompt | `format_classify_prompt()`完整实现 | 开发 |
| 下午 | 测试Prompt效果 | 测试报告 | 开发 |

**详细任务说明**：

**任务1.1：意图判断Prompt** (2小时)

```python
# src/llm/prompts.py - format_intent_prompt()

def format_intent_prompt(self, question: str) -> str:
    """
    格式化意图判断prompt
    
    目标：判断问题是简单检索还是复杂分析
    
    简单问题特征：
    - 单一时间点
    - 单一党派或议员
    - 事实查询
    
    复杂问题特征：
    - 时间跨度（多年）
    - 多个党派对比
    - 趋势变化分析
    - 政策演变分析
    """
    return f"""
你是一个问题复杂度分析专家。请判断以下问题的复杂程度。

问题：{question}

分析维度：
1. 时间维度：是否涉及多个年份或时间跨度？
2. 对象维度：是否涉及多个党派或议员的对比？
3. 分析深度：是简单的事实查询还是需要分析、对比、总结？

请按以下格式回答：
【复杂度】：简单/复杂
【原因】：（说明判断依据）
【维度分析】：
  - 时间：单一/多个
  - 对象：单一/多个  
  - 类型：事实查询/变化分析/对比分析/总结类

只需输出分析结果，不要额外解释。
"""
```

**任务1.2：参数提取Prompt** (3小时)

```python
# src/llm/prompts.py - format_extract_prompt()

def format_extract_prompt(self, question: str) -> str:
    """
    格式化参数提取prompt
    
    需要提取的参数：
    - 时间范围：year_start, year_end, month, day
    - 党派：parties (可能多个)
    - 议员：speakers (可能多个)
    - 主题：topics
    """
    return f"""
你是一个信息提取专家。请从以下问题中提取结构化参数。

问题：{question}

请提取以下信息（如果存在）：

1. **时间范围**
   - 起始年份：YYYY
   - 结束年份：YYYY
   - 月份：MM（如果指定）
   - 日期：DD（如果指定）

2. **党派**（德语原名）
   - 可能的党派：CDU/CSU, SPD, FDP, BÜNDNIS 90/DIE GRÜNEN, DIE LINKE, AfD, 等
   - 如果问题提到"所有党派"或"不同党派"，标记为：ALL_PARTIES

3. **议员姓名**（德语原名）
   - 如"Angela Merkel", "Olaf Scholz"等

4. **主题关键词**（德语）
   - 如"Flüchtlingspolitik"（难民政策）, "Klimaschutz"（气候保护）等

请以JSON格式输出：
{{
  "time": {{
    "year_start": "YYYY",
    "year_end": "YYYY",
    "month": "MM",
    "day": "DD"
  }},
  "parties": ["党派1", "党派2"],
  "speakers": ["议员1", "议员2"],
  "topics": ["主题1", "主题2"]
}}

如果某个字段无法提取，设为null。
"""
```

**任务1.3：问题分类Prompt** (2小时)

```python
# src/llm/prompts.py - format_classify_prompt()

def format_classify_prompt(self, question: str) -> str:
    """
    格式化问题分类prompt
    
    分类类型：
    - 变化类：分析某个政策/立场在时间上的变化
    - 总结类：总结某个党派/议员在某个主题上的观点
    - 对比类：对比不同党派/议员的立场差异
    - 事实查询：查询具体事实（时间/地点/内容）
    - 趋势分析：分析某个议题的发展趋势
    """
    return f"""
你是一个问题分类专家。请对以下问题进行分类。

问题：{question}

分类类型：
1. **变化类**：分析某个政策/立场随时间的变化
   - 示例："2015-2018年CDU对难民政策的立场有何变化？"
   
2. **总结类**：总结某个党派/议员的观点
   - 示例："请总结2019年绿党在气候保护方面的主要主张"
   
3. **对比类**：对比不同党派/议员的立场差异
   - 示例："请对比CDU和SPD在2020年对数字化政策的看法"
   
4. **事实查询**：查询具体事实
   - 示例："2019年3月15日Merkel在议会上说了什么？"
   
5. **趋势分析**：分析议题发展趋势
   - 示例："2010-2020年议会对核能的态度有何演变？"

请输出分类结果：
【类型】：变化类/总结类/对比类/事实查询/趋势分析
【理由】：（简要说明）
"""
```

#### Day 3: 问题拆解与总结Prompt

| 时间 | 任务 | 产出 | 负责人 |
|-----|------|------|--------|
| 上午 | 编写问题拆解模板 | 3类问题拆解模板 | 开发 |
| 下午 | 编写总结Prompt（德文） | `format_summarize_prompt()`完整实现 | 开发 |
| 下午 | 集成系统提示词 | LLM客户端集成 | 开发 |

**任务1.4：问题拆解模板** (4小时)

```python
# src/llm/prompts.py - format_decompose_prompt()

def format_decompose_prompt(
    self, 
    question: str, 
    question_type: str, 
    parameters: dict
) -> str:
    """
    格式化问题拆解prompt
    
    根据问题类型和参数，生成拆解策略
    """
    
    if question_type == "变化类":
        return self._decompose_change_question(question, parameters)
    elif question_type == "对比类":
        return self._decompose_comparison_question(question, parameters)
    elif question_type == "总结类":
        return self._decompose_summary_question(question, parameters)
    else:
        # 事实查询和趋势分析不需要拆解
        return ""

def _decompose_change_question(self, question: str, params: dict) -> str:
    """
    拆解变化类问题
    
    策略：按时间维度拆解
    """
    year_start = params.get('time', {}).get('year_start')
    year_end = params.get('time', {}).get('year_end')
    parties = params.get('parties', [])
    topics = params.get('topics', [])
    
    return f"""
请将以下复杂问题拆解为多个简单子问题。

原问题：{question}

拆解策略：按年份拆解

时间范围：{year_start} - {year_end}
涉及党派：{', '.join(parties) if parties else '所有主要党派'}
主题：{', '.join(topics)}

请为每一年生成一个子问题，格式为：
1. {year_start}年[党派]在[主题]上的立场是什么？
2. {int(year_start)+1}年[党派]在[主题]上的立场是什么？
...

如果涉及多个党派，则进一步拆解为：
1.1 {year_start}年CDU/CSU在[主题]上的立场？
1.2 {year_start}年SPD在[主题]上的立场？
...

最多生成20个子问题。
"""

def _decompose_comparison_question(self, question: str, params: dict) -> str:
    """
    拆解对比类问题
    
    策略：按党派维度拆解
    """
    parties = params.get('parties', [])
    year_start = params.get('time', {}).get('year_start')
    year_end = params.get('time', {}).get('year_end')
    topics = params.get('topics', [])
    
    return f"""
请将以下对比问题拆解为多个独立的查询子问题。

原问题：{question}

拆解策略：按党派拆解

涉及党派：{', '.join(parties)}
时间范围：{year_start} - {year_end}
主题：{', '.join(topics)}

请为每个党派生成一个子问题，格式为：
1. {year_start}-{year_end}年CDU/CSU在[主题]的立场和主张是什么？
2. {year_start}-{year_end}年SPD在[主题]的立场和主张是什么？
...
"""

def _decompose_summary_question(self, question: str, params: dict) -> str:
    """
    拆解总结类问题
    
    策略：如果时间跨度大，按年份拆解；否则直接检索
    """
    year_start = params.get('time', {}).get('year_start')
    year_end = params.get('time', {}).get('year_end')
    
    if year_start and year_end and int(year_end) - int(year_start) > 2:
        # 时间跨度大，拆解
        return f"""
请将以下总结问题拆解为按年份的子问题。

原问题：{question}

拆解策略：按年份拆解

请为每一年生成一个子问题，然后汇总。
"""
    else:
        # 时间跨度小，不需要拆解
        return ""
```

**任务1.5：总结Prompt（德文格式）** (4小时)

```python
# src/llm/prompts.py - format_summarize_prompt()

def format_summarize_prompt(
    self, 
    question: str, 
    retrieved_docs: List[Dict],
    is_sub_question: bool = False
) -> str:
    """
    格式化总结prompt
    
    按照产品文档要求的德文输出格式
    """
    
    # 构建文档上下文
    context = self._format_documents(retrieved_docs)
    
    if is_sub_question:
        # 子问题的简洁总结
        return f"""
Frage: {question}

Betreffender Hintergrund:
{context}

Bitte erstellen Sie eine prägnante Zusammenfassung (max. 200 Wörter) basierend 
auf den obigen Materialien. Falls die Materialien keine relevanten Informationen 
enthalten, antworten Sie: "Keine relevanten Informationen gefunden."
"""
    else:
        # 最终答案的结构化输出
        system_prompt = self._get_system_prompt()
        
        return f"""
{system_prompt}

Frage: {question}

Betreffender Hintergrund:
{context}

Bitte erstellen Sie eine strukturierte Antwort nach folgendem Format:

**Für jede relevante Position/Aussage:**

- **Sprecherzuordnung**: [Name], [Partei/Funktion]
- **Kernaussage**: [Prägnante Formulierung der Hauptaussage]
- **Beweisstücke**: [Schlüsselfakten, Zitate oder Daten]
- **Datenquelle**: [text_id]

**Gesamtzusammenfassung** (falls erforderlich):
[Übergreifende Analyse und Schlussfolgerungen]

Wichtig:
- Bewahren Sie ALLE politischen Terminologien und Parteipositionen
- Geben Sie IMMER die text_id als Datenquelle an
- Verdichten Sie NUR nicht-essenzielle Dialogteile
- Behalten Sie Ursache-Wirkungs-Beziehungen bei
"""

def _get_system_prompt(self) -> str:
    """返回产品文档中指定的德文系统提示词"""
    return """
【Rolle】Du bist Politikexperte mit Spezialisierung auf deutschen Bundestagsdebatten.

【Kernaufgabe】Erstelle auf Grundlage der untenstehenden Frage und des betreffenden 
Hintergrunds eine strukturierte Antwort auf Deutsch. Die Antwort soll:
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
"""

def _format_documents(self, docs: List[Dict]) -> str:
    """格式化检索到的文档"""
    formatted = []
    for i, doc in enumerate(docs, 1):
        metadata = doc.get('metadata', {})
        text = doc.get('text', '')
        
        formatted.append(f"""
[Dokument {i}]
text_id: {metadata.get('text_id', 'unknown')}
Datum: {metadata.get('year')}-{metadata.get('month')}-{metadata.get('day')}
Sprecher: {metadata.get('speaker', 'unbekannt')}
Partei: {metadata.get('group', 'unbekannt')}

Inhalt:
{text}
---
""")
    
    return "\n".join(formatted)
```

#### Day 4: 集成测试与调试

| 时间 | 任务 | 产出 | 负责人 |
|-----|------|------|--------|
| 上午 | 集成所有Prompt到节点 | 所有Agent节点可运行 | 开发 |
| 上午 | 测试简单问题1 | "2019年CDU/CSU的立场？" | 开发 |
| 下午 | 测试简单问题2-3 | 测试报告 | 开发 |
| 下午 | 调试和优化Prompt | 优化后的Prompt | 开发 |

**测试用例**：

```python
# 简单问题测试集
simple_questions = [
    "2019年德国联邦议院讨论了哪些主要议题？",
    "2020年3月15日Merkel说了什么？",
    "2021年绿党在气候保护方面的主要立场是什么？"
]
```

**预期输出**：
- 系统能够正确识别为简单问题
- 能够提取参数（年份、党派等）
- 能够检索到相关文档
- 能够生成德文格式的结构化答案

---

### Phase 2: 复杂问题处理 (Day 5-7)

**目标**: 实现复杂问题的拆解、检索和汇总

#### Day 5: 问题拆解实现

| 时间 | 任务 | 产出 | 负责人 |
|-----|------|------|--------|
| 上午 | 实现问题拆解逻辑 | DecomposeNode完整实现 | 开发 |
| 上午 | 实现最大子问题数限制 | 防止拆解爆炸 | 开发 |
| 下午 | 测试问题拆解 | 拆解结果验证 | 开发 |
| 下午 | 优化拆解策略 | 优化后的拆解逻辑 | 开发 |

**关键代码**：

```python
# src/graph/nodes/decompose.py

class DecomposeNode:
    MAX_SUB_QUESTIONS = 20  # 最大子问题数
    
    def __call__(self, state: GraphState) -> GraphState:
        question = state["question"]
        question_type = state["question_type"]
        parameters = state["parameters"]
        
        # 调用LLM拆解问题
        prompt = self.prompts.format_decompose_prompt(
            question, question_type, parameters
        )
        
        response = self.llm.invoke(prompt)
        sub_questions = self._parse_sub_questions(response)
        
        # 限制子问题数量
        if len(sub_questions) > self.MAX_SUB_QUESTIONS:
            logger.warning(
                f"拆解出{len(sub_questions)}个子问题，超过限制，"
                f"截取前{self.MAX_SUB_QUESTIONS}个"
            )
            sub_questions = sub_questions[:self.MAX_SUB_QUESTIONS]
        
        return update_state(
            state,
            sub_questions=sub_questions,
            current_node="decompose",
            next_node="retrieve"
        )
```

#### Day 6: 分层汇总实现

| 时间 | 任务 | 产出 | 负责人 |
|-----|------|------|--------|
| 上午 | 实现子问题批量检索 | RetrieveNode支持多问题 | 开发 |
| 上午 | 实现分层汇总策略 | 三层汇总逻辑 | 开发 |
| 下午 | 测试分层汇总 | 汇总结果验证 | 开发 |
| 下午 | 优化Token控制 | 避免超限 | 开发 |

**分层汇总策略**：

```
Layer 1: 子问题独立回答
├─ 2015年CDU/CSU立场？ → 200字总结
├─ 2016年CDU/CSU立场？ → 200字总结
├─ 2017年CDU/CSU立场？ → 200字总结
└─ 2018年CDU/CSU立场？ → 200字总结

Layer 2: 按年份汇总
├─ 2015年情况汇总 → 500字
├─ 2016年情况汇总 → 500字
├─ 2017年情况汇总 → 500字
└─ 2018年情况汇总 → 500字

Layer 3: 最终总结
└─ 2015-2018年变化趋势 → 800字（德文结构化输出）
```

#### Day 7: 复杂问题测试

| 时间 | 任务 | 产出 | 负责人 |
|-----|------|------|--------|
| 上午 | 测试变化类问题 | "2015-2018年难民政策变化" | 开发 |
| 上午 | 测试对比类问题 | "CDU vs SPD在2019年立场对比" | 开发 |
| 下午 | 测试总结类问题 | "2020年绿党气候保护主张总结" | 开发 |
| 下午 | 调试和优化 | 优化后的系统 | 开发 |

**测试用例**：

```python
# 复杂问题测试集
complex_questions = [
    # 变化类
    "在2015年到2018年期间，德国联邦议会中不同党派在难民家庭团聚问题上的讨论发生了怎样的变化？",
    
    # 对比类
    "请对比2015-2017年联盟党与绿党在移民融合政策方面的主张",
    
    # 总结类
    "请总结2019年德国绿党议员在气候保护方面的主要发言内容"
]
```

---

### Phase 3: 测试与优化 (Day 8-10)

**目标**: 建立评估基准，迭代优化系统质量

#### Day 8: 评估框架建立

| 时间 | 任务 | 产出 | 负责人 |
|-----|------|------|--------|
| 上午 | 编写评估脚本 | `evaluate.py` | 开发 |
| 上午 | 整理测试问题集 | 基于产品文档的15个问题 | 用户+开发 |
| 下午 | 批量测试 | 15个问题的回答结果 | 开发 |
| 下午 | 结果分析 | 问题分类和优先级 | 开发 |

**评估脚本框架**：

```python
# evaluate.py

class SystemEvaluator:
    """
    系统评估器
    
    功能：
    1. 批量测试问题集
    2. 记录每个问题的处理时间、Token消耗
    3. 生成评估报告
    """
    
    def __init__(self, workflow: QuestionAnswerWorkflow):
        self.workflow = workflow
        self.results = []
    
    def evaluate_questions(
        self, 
        questions: List[str],
        reference_answers: Optional[List[str]] = None
    ):
        """批量评估问题"""
        for i, question in enumerate(questions, 1):
            print(f"\n{'='*60}")
            print(f"测试 {i}/{len(questions)}: {question}")
            print(f"{'='*60}")
            
            start_time = time.time()
            
            try:
                result = self.workflow.run(question, verbose=False)
                elapsed_time = time.time() - start_time
                
                self.results.append({
                    'question': question,
                    'success': True,
                    'answer': result.get('final_answer'),
                    'elapsed_time': elapsed_time,
                    'sub_questions_count': len(result.get('sub_questions', [])),
                    'error': None
                })
                
                print(f"✅ 完成 (耗时: {elapsed_time:.2f}秒)")
                
            except Exception as e:
                elapsed_time = time.time() - start_time
                
                self.results.append({
                    'question': question,
                    'success': False,
                    'answer': None,
                    'elapsed_time': elapsed_time,
                    'sub_questions_count': 0,
                    'error': str(e)
                })
                
                print(f"❌ 失败: {str(e)}")
        
        self.generate_report()
    
    def generate_report(self):
        """生成评估报告"""
        total = len(self.results)
        success = sum(1 for r in self.results if r['success'])
        avg_time = sum(r['elapsed_time'] for r in self.results) / total
        
        print(f"\n{'='*60}")
        print("评估报告")
        print(f"{'='*60}")
        print(f"总问题数: {total}")
        print(f"成功数: {success}")
        print(f"成功率: {success/total*100:.1f}%")
        print(f"平均耗时: {avg_time:.2f}秒")
        
        # 失败案例
        failed = [r for r in self.results if not r['success']]
        if failed:
            print(f"\n失败案例:")
            for r in failed:
                print(f"  - {r['question'][:50]}...")
                print(f"    错误: {r['error']}")
```

#### Day 9: 迭代优化

| 时间 | 任务 | 产出 | 负责人 |
|-----|------|------|--------|
| 上午 | 分析失败案例 | 失败原因分析报告 | 开发 |
| 上午 | 优化Prompt | 针对性Prompt改进 | 开发 |
| 下午 | 优化检索策略 | 改进metadata过滤逻辑 | 开发 |
| 下午 | 优化异常处理 | 更友好的错误提示 | 开发 |

**常见问题及优化方案**：

| 问题 | 可能原因 | 优化方案 |
|------|---------|---------|
| 参数提取失败 | Prompt不够明确 | 优化示例，增加约束 |
| 检索结果为空 | metadata过滤太严格 | 放宽过滤条件 |
| 总结不符合格式 | Prompt约束不足 | 增强格式要求 |
| Token超限 | 子问题太多 | 降低MAX_SUB_QUESTIONS |
| 回答不准确 | 检索top_k太小 | 增加top_k值 |

#### Day 10: 二次评估与演示准备

| 时间 | 任务 | 产出 | 负责人 |
|-----|------|------|--------|
| 上午 | 二次批量测试 | 优化后的测试结果 | 开发 |
| 上午 | 准备演示案例 | 5个精选问题及答案 | 开发 |
| 下午 | 准备演示文档 | PPT或演示脚本 | 开发 |
| 下午 | 系统演示排练 | 流程熟悉 | 开发 |

**演示案例选择标准**：
1. 覆盖简单和复杂问题
2. 展示系统核心能力
3. 回答质量高、格式规范
4. 具有代表性和说服力

---

### Phase 4: 增强功能 (Day 11-12)

**目标**: 完善系统功能，提升用户体验

#### Day 11: 功能增强

| 时间 | 任务 | 产出 | 负责人 |
|-----|------|------|--------|
| 上午 | 增强异常处理 | 完善的异常分类和提示 | 开发 |
| 上午 | 实现模块化输出 | 按年份/党派分段输出 | 开发 |
| 下午 | 优化检索性能 | 缓存、批处理优化 | 开发 |
| 下午 | 完善日志系统 | 详细的调试日志 | 开发 |

**异常处理增强**：

```python
# src/graph/nodes/exception.py

class ExceptionType(Enum):
    NO_MATERIAL = "no_material"          # 材料中未找到
    LLM_ERROR = "llm_error"              # LLM调用失败
    RETRIEVAL_ERROR = "retrieval_error"  # 检索失败
    PARSE_ERROR = "parse_error"          # 解析失败
    TOKEN_LIMIT = "token_limit"          # Token超限
    TIMEOUT = "timeout"                  # 超时

class ExceptionNode:
    def __call__(self, state: GraphState) -> GraphState:
        error = state.get("error", "")
        error_type = self._classify_error(error)
        
        user_message = self._generate_user_message(error_type, error)
        
        return update_state(
            state,
            final_answer=user_message,
            error_type=error_type.value,
            current_node="exception"
        )
    
    def _generate_user_message(
        self, 
        error_type: ExceptionType, 
        error: str
    ) -> str:
        """生成用户友好的错误信息（德文）"""
        messages = {
            ExceptionType.NO_MATERIAL: 
                "Entschuldigung, in den verfügbaren Materialien wurden keine "
                "relevanten Informationen zu Ihrer Frage gefunden. "
                "Bitte formulieren Sie Ihre Frage anders oder erweitern Sie "
                "den Zeitraum bzw. die Thematik.",
            
            ExceptionType.LLM_ERROR:
                "Es ist ein technischer Fehler aufgetreten. "
                "Bitte versuchen Sie es erneut.",
            
            ExceptionType.RETRIEVAL_ERROR:
                "Die Datenbankabfrage ist fehlgeschlagen. "
                "Bitte überprüfen Sie Ihre Anfrage.",
            
            # ... 其他错误类型
        }
        
        return messages.get(error_type, f"Ein Fehler ist aufgetreten: {error}")
```

#### Day 12: 文档与测试

| 时间 | 任务 | 产出 | 负责人 |
|-----|------|------|--------|
| 上午 | 编写使用文档 | `USAGE.md` | 开发 |
| 上午 | 编写API文档（可选） | `API.md` | 开发 |
| 下午 | 全面测试 | 测试报告 | 开发 |
| 下午 | 修复发现的bug | bug列表和修复记录 | 开发 |

---

### Phase 5: 部署与交付 (Day 13-14)

**目标**: 部署系统到云端，准备交付

#### Day 13: 云端部署

| 时间 | 任务 | 产出 | 负责人 |
|-----|------|------|--------|
| 上午 | 配置云端Milvus | 云端Milvus可用 | 开发 |
| 上午 | 全量数据索引构建 | 全部数据（1949-2025）索引 | 开发 |
| 下午 | 环境配置 | 生产环境配置文件 | 开发 |
| 下午 | 部署测试 | 云端系统可用 | 开发 |

**全量数据索引**：

```bash
# 切换到ALL模式
export DATA_MODE=ALL
export MILVUS_MODE=cloud

# 构建全量索引
python build_index.py

# 预计耗时：2-3小时
# 预计索引大小：根据数据量和embedding维度
```

#### Day 14: 最终交付

| 时间 | 任务 | 产出 | 负责人 |
|-----|------|------|--------|
| 上午 | 系统最终测试 | 测试通过确认 | 开发 |
| 上午 | 准备交付文档 | 完整交付包 | 开发 |
| 下午 | 知识转移 | 培训材料、操作手册 | 开发 |
| 下午 | 正式交付 | 交付确认 | 用户+开发 |

**交付清单**：

- [ ] 完整源代码
- [ ] 环境配置文件（.env.example）
- [ ] 依赖列表（requirements.txt）
- [ ] 使用文档（USAGE.md）
- [ ] 部署文档（DEPLOYMENT.md）
- [ ] 测试报告
- [ ] 党派映射表（party_mapping.csv）
- [ ] 已构建的向量索引（可选，可现场构建）
- [ ] 演示视频/录屏（可选）

---

## 🎯 关键成功因素

### 1. Prompt质量是核心

所有功能都依赖于高质量的Prompt。建议：
- 先用中文编写逻辑清晰的Prompt
- 针对德文输出单独优化
- 充分测试，快速迭代

### 2. 分层汇总避免Token超限

复杂问题必须采用分层汇总策略：
- 子问题简洁回答（200字）
- 中间层适度汇总（500字）
- 最终层结构化输出（800字）

### 3. 测试驱动开发

- 每完成一个功能立即测试
- 维护测试用例库
- 记录失败案例，针对性优化

### 4. 用户参与很重要

需要用户参与的环节：
- **Day 8**：提供20个Q&A评估集
- **Day 10**：参加系统演示，提供反馈
- **Day 14**：最终验收

---

## 📊 资源需求

### 人力资源

| 角色 | 工作量 | 关键技能 |
|------|-------|---------|
| Python开发工程师 | 全职14天 | Python, LangChain, RAG |
| 测试工程师 | 3天 | 测试设计、bug跟踪 |
| 产品经理/用户 | 关键节点参与 | 需求确认、验收 |

### 技术资源

| 资源 | 用途 | 成本估算 |
|------|------|---------|
| Gemini API | LLM调用 | ~$50-100（测试+开发） |
| OpenAI Embedding API | 向量化 | ~$20-50 |
| Milvus Cloud | 向量数据库 | 按需（或本地免费） |
| 计算资源 | 索引构建 | 本地或云端 |

---

## ⚠️ 风险与应对

### 风险1：Prompt效果不理想

**概率**: 中等  
**影响**: 高  
**应对**:
- 留出充足的Prompt迭代时间
- 准备Plan B（简化输出格式）
- 必要时咨询LLM专家

### 风险2：LLM API不稳定

**概率**: 低-中等  
**影响**: 高  
**应对**:
- 实现重试机制（已有）
- 准备备用API
- 设置合理的超时时间

### 风险3：向量检索召回率低

**概率**: 中等  
**影响**: 高  
**应对**:
- 调整检索参数（top_k, threshold）
- 优化metadata过滤策略
- 考虑使用更好的Embedding模型

### 风险4：性能不达标

**概率**: 低  
**影响**: 中等  
**应对**:
- 实现缓存机制
- 异步处理
- 批量操作优化

### 风险5：用户需求变更

**概率**: 中等  
**影响**: 中等  
**应对**:
- 保持架构灵活性
- 模块化设计
- 定期与用户沟通

---

## 📞 沟通与汇报

### 日常沟通

- **每日站会**（可选）：15分钟，同步进度和问题
- **关键节点汇报**：Phase完成时向用户汇报

### 里程碑汇报

| 里程碑 | 汇报时间 | 汇报内容 |
|-------|---------|---------|
| M2: 简单问题可回答 | Day 4 | 演示简单问题回答，收集反馈 |
| M3: 复杂问题可回答 | Day 7 | 演示复杂问题处理，评估质量 |
| M4: 系统可演示 | Day 10 | 正式演示，收集最终修改意见 |
| M5: 系统可交付 | Day 14 | 交付验收 |

---

## ✅ 检查清单

### Phase 1完成标准

- [ ] 所有Prompt模板已编写
- [ ] 系统提示词已集成
- [ ] 能够回答至少3个简单问题
- [ ] 输出格式符合德文要求

### Phase 2完成标准

- [ ] 问题拆解逻辑实现
- [ ] 分层汇总策略实现
- [ ] 能够回答至少3个复杂问题
- [ ] Token控制有效

### Phase 3完成标准

- [ ] 评估脚本可用
- [ ] 至少15个问题测试完成
- [ ] 成功率 ≥ 80%
- [ ] 平均响应时间 ≤ 30秒（简单问题）
- [ ] 平均响应时间 ≤ 90秒（复杂问题）

### Phase 4完成标准

- [ ] 异常处理完善
- [ ] 模块化输出实现
- [ ] 文档完整
- [ ] 无严重bug

### Phase 5完成标准

- [ ] 云端部署成功
- [ ] 全量数据索引完成
- [ ] 用户验收通过
- [ ] 交付文档齐全

---

## 🎉 结语

这是一个技术上具有挑战性但非常有意义的项目。关键成功因素是：

1. **Prompt工程质量**
2. **分层汇总策略**
3. **充分测试迭代**
4. **用户及时反馈**

让我们按照这个计划，一步一步完成这个优秀的智能问答系统！

---

**计划制定者**: AI Assistant  
**最后更新**: 2025-11-01  
**版本**: v1.0

