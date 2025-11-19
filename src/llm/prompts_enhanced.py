"""
增强版Prompt模板
包含完整的问题拆解、总结和德文输出Prompt
"""

from typing import Dict, List


class EnhancedPrompts:
    """增强版Prompt模板"""
    
    # ========== 德文系统提示词（产品文档要求）==========
    
    GERMAN_SYSTEM_PROMPT = """【Rolle】Du bist Politikexperte mit Spezialisierung auf deutschen Bundestagsdebatten.

【Kernaufgabe】Erstelle auf Grundlage der untenstehenden Frage und des betreffenden Hintergrunds eine strukturierte Antwort auf Deutsch. Die Antwort soll:
1. alle zentralen Argumente und Details bewahren,
2. die ursprünglichen Sprecherzuordnungen sowie kontextuellen Beziehungen erhalten,
3. nicht essenzielle Dialogteile verdichten, dabei jedoch die faktische Dichte beibehalten.

【Kritische Vorgaben】
- NIEMALS auslassen: politische Terminologie, Parteipositionen, Beschlüsse/Resolutionen oder Zugehörigkeiten der Sprecher (Partei/Funktion).
- IMMER bewahren: Ursache-Wirkungs-Beziehungen und die Entscheidungslogik.
- Ausgabeformat: Aufzählungspunkte mit dem Link „Speaker" und dem Link „text_id".

【Struktur der Zusammenfassung】
- Sprecherzuordnung (falls verfügbar): [Name/Partei]
- Kernaussage: [prägnante Formulierung]
- Beweisstücke: [Schlüsselfakten/-daten]
- Datenquelle: [text_id]
"""
    
    # ========== 问题拆解Prompt（变化类）==========
    
    DECOMPOSE_CHANGE_QUESTION = """你是一个问题拆解专家。请将以下变化类问题拆解为多个子问题。

【原问题】
{original_question}

【提取的参数】
时间范围: {start_year}-{end_year}
涉及党派: {parties}
主题: {topics}

【拆解策略：按年份拆解】

将问题拆解为每一年的具体问题。

【输出格式】

每行一个子问题，格式如下：
1. [年份1] [党派/对象] 在 [主题] 上的立场是什么？
2. [年份2] [党派/对象] 在 [主题] 上的立场是什么？
...

【拆解规则】
- 如果涉及"不同党派"或"ALL_PARTIES"，需要为每个主要党派拆解（CDU/CSU, SPD, FDP, BÜNDNIS 90/DIE GRÜNEN, DIE LINKE）
- 如果时间跨度大于5年，只拆解关键年份或每2年一个子问题
- 最多生成20个子问题

【示例】
原问题: "在2015年到2017年期间，CDU/CSU在难民家庭团聚问题上的立场有何变化？"
时间范围: 2015-2017
涉及党派: CDU/CSU
主题: 难民家庭团聚

输出:
1. 2015年CDU/CSU在难民家庭团聚问题上的立场是什么？
2. 2016年CDU/CSU在难民家庭团聚问题上的立场是什么？
3. 2017年CDU/CSU在难民家庭团聚问题上的立场是什么？

现在请拆解用户的问题。只输出子问题列表，每行一个，不要包含其他内容。
"""
    
    # ========== 问题拆解Prompt（对比类）==========
    
    DECOMPOSE_COMPARISON_QUESTION = """你是一个问题拆解专家。请将以下对比类问题拆解为多个子问题。

【原问题】
{original_question}

【提取的参数】
时间范围: {start_year}-{end_year}
涉及党派: {parties}
主题: {topics}

【拆解策略：按党派拆解】

为每个需要对比的党派生成独立的查询问题。

【输出格式】

每行一个子问题，格式如下：
1. [时间范围] [党派1] 在 [主题] 上的立场和主张是什么？
2. [时间范围] [党派2] 在 [主题] 上的立场和主张是什么？
...

【拆解规则】
- 为每个party生成一个子问题
- 如果是"ALL_PARTIES"，为主要党派各生成一个（CDU/CSU, SPD, FDP, BÜNDNIS 90/DIE GRÜNEN, DIE LINKE）
- 保持时间范围一致
- 最多生成10个子问题

【示例】
原问题: "请对比2015-2017年CDU/CSU与绿党在移民融合政策方面的主张"
时间范围: 2015-2017
涉及党派: CDU/CSU, BÜNDNIS 90/DIE GRÜNEN
主题: 移民融合政策

输出:
1. 2015-2017年CDU/CSU在移民融合政策方面的主张是什么？
2. 2015-2017年BÜNDNIS 90/DIE GRÜNEN在移民融合政策方面的主张是什么？

现在请拆解用户的问题。只输出子问题列表，每行一个，不要包含其他内容。
"""
    
    # ========== 问题拆解Prompt（总结类）==========
    
    DECOMPOSE_SUMMARY_QUESTION = """你是一个问题拆解专家。请将以下总结类问题拆解为多个子问题（如果需要）。

【原问题】
{original_question}

【提取的参数】
时间范围: {start_year}-{end_year}
涉及党派: {parties}
主题: {topics}

【判断是否需要拆解】

- 如果时间跨度 ≤ 2年：不需要拆解，返回"NO_DECOMPOSITION"
- 如果时间跨度 > 2年：按年份拆解

【拆解策略（如需要）】

按年份拆解，每年一个子问题。

【输出格式】

如果不需要拆解：
NO_DECOMPOSITION

如果需要拆解，每行一个子问题：
1. [年份1] [党派] 在 [主题] 上的主要观点是什么？
2. [年份2] [党派] 在 [主题] 上的主要观点是什么？
...

【示例1：不需要拆解】
原问题: "请总结2019年绿党在气候保护方面的主要主张"
时间范围: 2019-2019
输出: NO_DECOMPOSITION

【示例2：需要拆解】
原问题: "请总结2015-2018年SPD在难民政策方面的主要主张"
时间范围: 2015-2018
输出:
1. 2015年SPD在难民政策方面的主要主张是什么？
2. 2016年SPD在难民政策方面的主要主张是什么？
3. 2017年SPD在难民政策方面的主要主张是什么？
4. 2018年SPD在难民政策方面的主要主张是什么？

现在请判断并拆解用户的问题。
"""
    
    # ========== 子问题总结Prompt（中文简洁）==========
    
    SUMMARIZE_SUB_QUESTION = """请基于以下检索到的材料，简洁回答问题。

【问题】
{question}

【检索材料】
{context}

【要求】
1. 直接回答问题，不要偏题
2. 基于材料内容，不要编造
3. 简洁总结（200字以内）
4. 如果材料不足，说明"材料中未找到相关信息"

请用中文简洁回答。
"""
    
    # ========== 最终总结Prompt（德文结构化输出）==========
    
    FINAL_SUMMARIZE_GERMAN = """{system_prompt}

【Frage】
{original_question}

【Betreffender Hintergrund】
{aggregated_context}

【Anweisungen】

Bitte erstellen Sie eine umfassende, strukturierte Antwort auf Deutsch basierend auf den obigen Materialien.

**Struktur der Antwort:**

Für jede relevante Position oder Aussage:

**[Jahreszahl oder Zeitraum]**
- **Sprecherzuordnung**: [Name], [Partei/Funktion]
- **Kernaussage**: [Prägnante Formulierung der Hauptaussage]
- **Beweisstücke**: [Schlüsselfakten, wichtige Zitate oder Daten]
- **Datenquelle**: [text_id]

**Gesamtzusammenfassung** (falls erforderlich):
[Übergreifende Analyse, Entwicklungstendenzen und Schlussfolgerungen]

**Wichtige Hinweise:**
- Bewahren Sie ALLE politischen Terminologien, Parteipositionen und Beschlüsse
- Geben Sie IMMER die text_id als Datenquelle an
- Behalten Sie Ursache-Wirkungs-Beziehungen bei
- Verdichten Sie NUR nicht-essenzielle Dialogteile
- Falls die Materialien keine ausreichenden Informationen enthalten, geben Sie klar an: "In den verfügbaren Materialien wurden keine hinreichenden Informationen gefunden."

Bitte erstellen Sie nun die strukturierte Antwort auf Deutsch.
"""
    
    # ========== 分层汇总Prompt（中间层）==========
    
    AGGREGATE_BY_YEAR = """请将以下按年份的子答案进行汇总。

【原问题】
{original_question}

【子答案】
{sub_answers}

【要求】
1. 按年份组织答案
2. 每年的内容保持300-500字
3. 保留关键信息和引用
4. 突出变化趋势（如果是变化类问题）
5. 用中文输出

请提供按年份汇总的答案。
"""
    
    # ========== 格式化文档上下文 ==========
    
    @staticmethod
    def format_documents(docs: List[Dict]) -> str:
        """
        格式化检索到的文档为德文格式
        
        Args:
            docs: 文档列表，每个文档包含metadata和text
            
        Returns:
            格式化后的文档字符串
        """
        formatted = []
        for i, doc in enumerate(docs, 1):
            metadata = doc.get('metadata', {})
            text = doc.get('text', '')
            
            formatted.append(f"""
[Dokument {i}]
text_id: {metadata.get('text_id', 'unbekannt')}
Datum: {metadata.get('year')}-{metadata.get('month')}-{metadata.get('day')}
Sprecher: {metadata.get('speaker', 'unbekannt')}
Partei: {metadata.get('group', 'unbekannt')}

Inhalt:
{text}

---
""")
        
        return "\n".join(formatted)
    
    # ========== 格式化子答案 ==========
    
    @staticmethod
    def format_sub_answers(sub_qa_pairs: List[Dict]) -> str:
        """
        格式化子问题和答案对
        
        Args:
            sub_qa_pairs: 子问题答案对列表
            
        Returns:
            格式化后的字符串
        """
        formatted = []
        for i, qa in enumerate(sub_qa_pairs, 1):
            formatted.append(f"""
【子问题 {i}】
{qa['question']}

【答案】
{qa['answer']}

---
""")
        
        return "\n".join(formatted)


# 测试代码
if __name__ == "__main__":
    prompts = EnhancedPrompts()
    
    # 测试德文系统提示词
    print("=== 德文系统提示词 ===")
    print(prompts.GERMAN_SYSTEM_PROMPT)
    
    # 测试问题拆解
    print("\n=== 变化类问题拆解 ===")
    print(prompts.DECOMPOSE_CHANGE_QUESTION.format(
        original_question="2015-2018年CDU/CSU在难民政策上的立场有何变化？",
        start_year="2015",
        end_year="2018",
        parties="CDU/CSU",
        topics="难民政策"
    ))

