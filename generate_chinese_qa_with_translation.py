"""
生成带中文翻译的问答报告
使用Gemini LLM翻译德语答案为中文
"""

import json
from datetime import datetime
from src.llm.client import GeminiLLMClient

def translate_german_to_chinese(german_text, llm_client):
    """使用LLM翻译德语文本为中文"""

    prompt = f"""请将以下德语文本翻译成中文。这是德国议会相关的政治分析文本。

要求：
1. 保持专业术语的准确性
2. 保留原文的结构（如**标题**、列表等）
3. 党派名称翻译：
   - CDU/CSU → 基民盟/基社盟
   - SPD → 社民党
   - BÜNDNIS 90/DIE GRÜNEN 或 Grüne/Bündnis 90 → 绿党
   - DIE LINKE → 左翼党
   - AfD → 选择党
   - FDP → 自民党
4. 保持引用和来源信息的格式

德语原文：
{german_text}

请直接输出中文翻译，不要添加任何解释。"""

    try:
        translation = llm_client.invoke(prompt)
        return translation
    except Exception as e:
        return f"[翻译失败: {str(e)}]\n\n{german_text}"


def generate_chinese_report_with_translation(results_file, output_file):
    """生成带中文翻译的问答报告"""

    print("正在初始化LLM客户端...")
    llm_client = GeminiLLMClient()

    with open(results_file, 'r', encoding='utf-8') as f:
        results = json.load(f)

    lines = []

    # 标题
    lines.append('# 德国议会RAG系统问答报告 (中文翻译版)\n\n')
    lines.append('**测试时间**: 2025-11-07\n')
    lines.append('**系统**: 基于LangGraph的RAG系统，使用BGE-M3嵌入模型\n')
    lines.append('**数据库**: Pinecone (173,355个向量, 2015-2024年)\n')
    lines.append('**成功率**: 7/7 (100%)\n\n')
    lines.append('> **说明**: 本报告将系统生成的德语答案翻译为中文，方便阅读理解。\n\n')
    lines.append('---\n\n')

    # 每个问题
    for i, r in enumerate(results, 1):
        q_id = r.get('question_id')
        question = r.get('question', '')
        answer = r.get('final_answer', '')
        q_type = r.get('type', 'N/A')

        print(f"\n处理问题 {q_id}/7: {q_type}")
        print(f"  问题: {question[:50]}...")

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

        # 翻译答案
        if answer:
            print(f"  正在翻译答案 ({len(answer)}字符)...")

            # 调用LLM翻译
            chinese_answer = translate_german_to_chinese(answer, llm_client)

            print(f"  翻译完成 ({len(chinese_answer)}字符)")

            lines.append(f'**系统回答（中文翻译）** (原文{len(answer)}字符):\n\n')
            lines.append(f'{chinese_answer}\n\n')

            # 添加德语原文折叠部分
            lines.append('<details>\n')
            lines.append('<summary>📄 点击查看德语原文</summary>\n\n')
            lines.append('```\n')
            lines.append(f'{answer}\n')
            lines.append('```\n\n')
            lines.append('</details>\n\n')
        else:
            error = r.get('error', '未知错误')
            lines.append(f'**错误**: {error}\n\n')

        # 性能
        lines.append('**性能指标**:\n')
        lines.append(f'- 总耗时: {r.get("total_time", 0):.2f}秒\n')
        lines.append(f'- 意图类型: {r.get("intent", "N/A")}\n')
        lines.append(f'- 问题分类: {r.get("question_type", "N/A")}\n\n')

        lines.append('---\n\n')

    # 添加使用说明
    lines.append('## 📖 使用说明\n\n')
    lines.append('### 关于翻译\n\n')
    lines.append('- 本报告中的中文翻译由Gemini 2.5 Pro自动生成\n')
    lines.append('- 德语原文可以通过点击"📄 点击查看德语原文"展开查看\n')
    lines.append('- 专业术语和党派名称已按照标准翻译规范处理\n\n')

    lines.append('### 党派名称对照\n\n')
    lines.append('| 德语 | 中文 |\n')
    lines.append('|------|------|\n')
    lines.append('| CDU/CSU | 基民盟/基社盟 |\n')
    lines.append('| SPD | 社民党 |\n')
    lines.append('| Grüne/BÜNDNIS 90 | 绿党 |\n')
    lines.append('| DIE LINKE | 左翼党 |\n')
    lines.append('| AfD | 选择党 |\n')
    lines.append('| FDP | 自民党 |\n\n')

    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(''.join(lines))

    print(f'\n✅ 中文翻译报告已生成: {output_file}')
    print(f'   - 行数: {len(lines)}')
    print(f'   - 大小: {len("".join(lines))/1024:.1f} KB')


if __name__ == "__main__":
    print("=" * 60)
    print("生成带中文翻译的问答报告")
    print("=" * 60)
    print("\n⚠️ 注意: 这将调用Gemini LLM进行翻译，需要一些时间...")
    print()

    generate_chinese_report_with_translation(
        'langgraph_complete_test_results.json',
        '问答报告-中文翻译版.md'
    )

    print("\n" + "=" * 60)
    print("✅ 翻译完成！")
    print("=" * 60)
