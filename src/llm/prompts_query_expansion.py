"""
Query扩展相关Prompt模板
用于LLM驱动的多角度查询生成
"""

QUERY_EXPANSION_PROMPT = """你是德国议会语料检索专家。给定一个查询问题，你需要生成5-7个不同角度的德语检索查询，以最大化召回率。

## 原始问题
{original_question}

## 子问题
{sub_question}

## 参数信息
- 年份: {year}
- 党派: {group}
- 主题: {topic}

## 生成规则

1. **语义多样性**：每个查询应覆盖不同的语义角度
   - 具体政策名称（如"Asylpaket I", "Sicherer Herkunftsstaat"）
   - 抽象理念（如"Humanitäre Verantwortung", "Ordnung und Kontrolle"）
   - 具体行动（如"Abschiebung durchsetzen", "Integration fördern"）

2. **关键词组合**：使用不同的关键词组合
   - 同义词替换（Flüchtlinge ↔ Asylsuchende）
   - 上下位词（Migrationspolitik → Abschiebung, Integration）
   - 相关术语（Rückführung, Ausreisepflicht, Zwang）

3. **元数据融合**：每个查询必须包含年份和党派信息
   - 格式：[党派] [主题关键词] [年份]
   - 示例：CDU/CSU Flüchtlingspolitik 2015

4. **长度控制**：每个查询30-60个字符

5. **覆盖范围**：
   - Query 1: 直接主题（最相关的核心关键词）
   - Query 2: 具体政策（政策名称+法案）
   - Query 3: 抽象理念（价值观+原则）
   - Query 4: 具体行动（动词+措施）
   - Query 5: 同义表达（换个说法）
   - Query 6-7: 补充角度（相关议题、对比视角）

## 输出格式

请以JSON格式输出，确保严格遵守以下格式：

```json
{{
  "expanded_queries": [
    "CDU/CSU Flüchtlingspolitik sichere Herkunftsländer 2015",
    "CDU Asylpaket Balkanstaaten Rückführung 2015",
    "CDU/CSU humanitäre Verantwortung Kontrolle Ordnung 2015",
    "CDU Abschiebung konsequent durchsetzen Ausreisepflicht 2015",
    "CDU/CSU Asylsuchende Integration Rückführung 2015",
    "CDU Migrationspolitik Grenzsicherung Dublin-Verfahren 2015",
    "CDU/CSU Flüchtlingskrise Maßnahmen Steuerung 2015"
  ]
}}
```

## 示例（难民政策）

**输入**：
- 原始问题：请总结2015年CDU/CSU在难民政策上的立场
- 子问题：CDU/CSU在2015年关于难民政策的主要观点是什么？
- 年份：2015
- 党派：CDU/CSU
- 主题：难民政策

**输出**：
```json
{{
  "expanded_queries": [
    "CDU/CSU Flüchtlingspolitik sichere Herkunftsländer 2015",
    "CDU Asylpaket I Balkanstaaten Abschiebung 2015",
    "CDU/CSU humanitäre Verantwortung Asylrecht 2015",
    "CDU Rückführung konsequent durchsetzen 2015",
    "CDU/CSU Flüchtlinge Integration Steuerung 2015",
    "CDU Migrationspolitik Grenzsicherung Dublin 2015",
    "CDU/CSU Asylverfahren beschleunigen Erstaufnahme 2015"
  ]
}}
```

## 注意事项

1. **必须包含年份和党派**：每个查询都要有年份和党派信息
2. **德语专业术语**：使用准确的德语政治术语
3. **避免重复**：7个查询应该是不同的，不要简单重复
4. **保持相关性**：所有查询都必须与原始问题高度相关
5. **JSON格式严格**：输出必须是有效的JSON，不要有多余的文字

现在，请根据上述规则生成扩展查询。
"""


QUERY_EXPANSION_FALLBACK_PROMPT = """检测到扩展查询生成失败。请根据以下信息，生成一个简化版本的扩展查询（3个查询）。

## 原始问题
{original_question}

## 子问题
{sub_question}

## 简化规则
1. Query 1: [党派] [主题核心词] [年份]
2. Query 2: [党派] [主题同义词] [年份]
3. Query 3: [党派] [主题具体措施] [年份]

## 输出格式（JSON）
```json
{{
  "expanded_queries": [
    "...",
    "...",
    "..."
  ]
}}
```
"""


# 主题关键词映射（辅助生成）
TOPIC_KEYWORD_MAP = {
    # 难民/移民政策
    "难民": ["Flüchtlinge", "Asylsuchende", "Schutzsuchende", "Geflüchtete"],
    "移民": ["Migration", "Einwanderung", "Zuwanderung"],
    "遣返": ["Abschiebung", "Rückführung", "Ausreise", "Rückkehr"],
    "融合": ["Integration", "Inklusion", "Teilhabe", "Eingliederung"],
    "庇护": ["Asyl", "Schutz", "Asylrecht", "Asylverfahren"],

    # 经济政策
    "数字化": ["Digitalisierung", "Digital", "Technologie", "Innovation"],
    "气候": ["Klima", "Klimaschutz", "Umwelt", "Energie"],
    "经济": ["Wirtschaft", "Konjunktur", "Wachstum", "Beschäftigung"],

    # 社会政策
    "教育": ["Bildung", "Schule", "Ausbildung", "Studium"],
    "健康": ["Gesundheit", "Pflege", "Medizin", "Krankenversicherung"],
    "养老": ["Rente", "Altersvorsorge", "Pensionen", "Alterssicherung"],

    # 外交政策
    "欧盟": ["EU", "Europa", "Europäische Union", "Integration"],
    "防务": ["Verteidigung", "Sicherheit", "Bundeswehr", "NATO"],
}


def build_query_expansion_prompt(original_question: str, sub_question: str,
                                 year: str = "", group: str = "", topic: str = "") -> str:
    """
    构建Query扩展Prompt

    Args:
        original_question: 原始用户问题
        sub_question: 子问题
        year: 年份
        group: 党派
        topic: 主题

    Returns:
        完整的Prompt字符串
    """
    return QUERY_EXPANSION_PROMPT.format(
        original_question=original_question,
        sub_question=sub_question,
        year=year or "未指定",
        group=group or "未指定",
        topic=topic or "未指定"
    )
