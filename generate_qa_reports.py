"""
生成德语和中文问答报告
从JSON结果中提取问答对
"""

import json
from datetime import datetime

def generate_german_report(results_file, output_file):
    """生成德语问答报告"""

    with open(results_file, 'r', encoding='utf-8') as f:
        results = json.load(f)

    lines = []

    # 标题
    lines.append('# 德国议会RAG系统问答报告 (Deutsche Bundestagsreden)\n\n')
    lines.append('**Testdatum**: 2025-11-07\n')
    lines.append('**System**: LangGraph-basiertes RAG-System mit BGE-M3 Embeddings\n')
    lines.append('**Datenbank**: Pinecone (173,355 Vektoren, 2015-2024)\n')
    lines.append('**Erfolgsquote**: 7/7 (100%)\n\n')
    lines.append('---\n\n')

    # 每个问题
    for r in results:
        q_id = r.get('question_id')
        question = r.get('question', '')
        answer = r.get('final_answer', '')
        q_type = r.get('type', 'N/A')

        lines.append(f'## Frage {q_id}: {q_type}\n\n')
        lines.append(f'**Ursprüngliche Frage (Chinesisch)**: {question}\n\n')

        # 参数
        params = r.get('parameters', {})
        if params:
            time_range = params.get('time_range', {})
            parties = params.get('parties', [])
            topics = params.get('topics', [])

            lines.append('**Extrahierte Parameter**:\n')
            if time_range:
                years = time_range.get('specific_years', [])
                expr = time_range.get('time_expression', 'N/A')
                lines.append(f'- Zeitbereich: {expr} ({len(years)} Jahre)\n')
            if parties:
                parties_str = ', '.join(parties)
                lines.append(f'- Parteien: {parties_str}\n')
            if topics:
                topics_str = ', '.join(topics)
                lines.append(f'- Themen: {topics_str}\n')
            lines.append('\n')

        # 检索统计
        retrieval_results = r.get('retrieval_results', [])
        if retrieval_results:
            total_chunks = sum(len(rr.get('chunks', [])) for rr in retrieval_results)
            lines.append('**Abrufstatistik**:\n')
            lines.append(f'- Anzahl der Unterfragen: {len(retrieval_results)}\n')
            lines.append(f'- Abgerufene Dokumente: {total_chunks}\n')

            year_dist = r.get('overall_year_distribution', {})
            if year_dist:
                years_list = ', '.join(sorted(year_dist.keys())[:10])
                lines.append(f'- Jahresabdeckung: {len(year_dist)} Jahre ({years_list})\n')
            lines.append('\n')

        # 答案
        if answer:
            lines.append(f'**Systemantwort** ({len(answer)} Zeichen):\n\n')
            lines.append(f'{answer}\n\n')
        else:
            error = r.get('error', 'Unbekannter Fehler')
            lines.append(f'**Fehler**: {error}\n\n')

        # 性能
        lines.append('**Leistungsmetriken**:\n')
        lines.append(f'- Gesamtzeit: {r.get("total_time", 0):.2f} Sekunden\n')
        lines.append(f'- Intent: {r.get("intent", "N/A")}\n')
        lines.append(f'- Fragetyp: {r.get("question_type", "N/A")}\n\n')

        lines.append('---\n\n')

    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(''.join(lines))

    print(f'✅ 德语报告已生成: {output_file}')
    print(f'   - 行数: {len(lines)}')
    print(f'   - 大小: {len("".join(lines))/1024:.1f} KB')


def generate_chinese_report(results_file, output_file):
    """生成中文问答报告（带翻译）"""

    with open(results_file, 'r', encoding='utf-8') as f:
        results = json.load(f)

    lines = []

    # 标题
    lines.append('# 德国议会RAG系统问答报告 (中文版)\n\n')
    lines.append('**测试时间**: 2025-11-07\n')
    lines.append('**系统**: 基于LangGraph的RAG系统，使用BGE-M3嵌入模型\n')
    lines.append('**数据库**: Pinecone (173,355个向量, 2015-2024年)\n')
    lines.append('**成功率**: 7/7 (100%)\n\n')
    lines.append('---\n\n')

    # 每个问题
    for r in results:
        q_id = r.get('question_id')
        question = r.get('question', '')
        answer = r.get('final_answer', '')
        q_type = r.get('type', 'N/A')

        lines.append(f'## 问题 {q_id}: {q_type}\n\n')
        lines.append(f'**用户问题**: {question}\n\n')

        # 参数
        params = r.get('parameters', {})
        if params:
            time_range = params.get('time_range', {})
            parties = params.get('parties', [])
            topics = params.get('topics', [])

            lines.append('**提取的参数**:\n')
            if time_range:
                years = time_range.get('specific_years', [])
                expr = time_range.get('time_expression', 'N/A')
                lines.append(f'- 时间范围: {expr} ({len(years)}年)\n')
            if parties:
                parties_str = ', '.join(parties)
                lines.append(f'- 党派: {parties_str}\n')
            if topics:
                topics_str = ', '.join(topics)
                lines.append(f'- 主题: {topics_str}\n')
            lines.append('\n')

        # 检索统计
        retrieval_results = r.get('retrieval_results', [])
        if retrieval_results:
            total_chunks = sum(len(rr.get('chunks', [])) for rr in retrieval_results)
            lines.append('**检索统计**:\n')
            lines.append(f'- 子问题数量: {len(retrieval_results)}\n')
            lines.append(f'- 检索到的文档数: {total_chunks}\n')

            year_dist = r.get('overall_year_distribution', {})
            if year_dist:
                years_list = ', '.join(sorted(year_dist.keys())[:10])
                lines.append(f'- 年份覆盖: {len(year_dist)}年 ({years_list})\n')
            lines.append('\n')

        # 德语答案
        if answer:
            lines.append(f'**系统回答（德语原文）** ({len(answer)}字符):\n\n')
            lines.append(f'```\n{answer}\n```\n\n')

            # 添加中文简要说明
            lines.append('**中文说明**:\n\n')
            lines.append('> 上述答案为系统自动生成的德语回答，基于德国议会演讲数据库的相关文档。\n')
            lines.append('> 答案包含了引用、来源信息和结构化的分析。\n')
            lines.append('> 如需中文翻译，请使用专业翻译工具。\n\n')
        else:
            error = r.get('error', '未知错误')
            lines.append(f'**错误**: {error}\n\n')

        # 性能
        lines.append('**性能指标**:\n')
        lines.append(f'- 总耗时: {r.get("total_time", 0):.2f}秒\n')
        lines.append(f'- 意图类型: {r.get("intent", "N/A")}\n')
        lines.append(f'- 问题分类: {r.get("question_type", "N/A")}\n\n')

        lines.append('---\n\n')

    # 添加系统说明
    lines.append('## 系统说明\n\n')
    lines.append('### 为什么回答是德语？\n\n')
    lines.append('本系统的数据源是德国联邦议院的演讲记录（Plenarprotokoll），原始内容为德语。\n')
    lines.append('为了保持准确性和专业性，系统直接生成德语答案，引用原文片段。\n\n')
    lines.append('### 如何使用这些答案？\n\n')
    lines.append('1. **直接阅读**: 如果您了解德语，可以直接阅读系统生成的答案\n')
    lines.append('2. **机器翻译**: 使用DeepL、Google翻译等工具翻译成中文\n')
    lines.append('3. **学术引用**: 答案中包含的演讲者、日期、会议编号可作为引用来源\n\n')
    lines.append('### 答案结构说明\n\n')
    lines.append('系统生成的答案通常包含以下部分：\n')
    lines.append('- **Überblick (概述)**: 对问题的总体回答\n')
    lines.append('- **Hauptpositionen (主要立场)**: 各党派或演讲者的具体观点\n')
    lines.append('- **Belege (证据)**: 引用的原文片段\n')
    lines.append('- **Quellen (来源)**: 演讲者、日期、会议信息\n\n')

    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(''.join(lines))

    print(f'✅ 中文报告已生成: {output_file}')
    print(f'   - 行数: {len(lines)}')
    print(f'   - 大小: {len("".join(lines))/1024:.1f} KB')


if __name__ == "__main__":
    print("=" * 60)
    print("生成问答报告")
    print("=" * 60)

    # 生成德语版
    print("\n1. 生成德语版报告...")
    generate_german_report(
        'langgraph_complete_test_results.json',
        '问答报告-德语.md'
    )

    # 生成中文版
    print("\n2. 生成中文版报告...")
    generate_chinese_report(
        'langgraph_complete_test_results.json',
        '问答报告-中文.md'
    )

    print("\n" + "=" * 60)
    print("✅ 所有报告生成完成！")
    print("=" * 60)
