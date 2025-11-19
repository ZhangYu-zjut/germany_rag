#!/usr/bin/env python3
"""
生成完整的引用文本报告（--full_ref模式）

功能：
1. 从state中提取完整的检索链路数据
2. 生成带有原始文本、分数的Markdown报告
3. 生成JSON格式的原始数据
4. 生成分析报告（召回率、ReRank效果）
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any


class FullRefReportGenerator:
    """完整引用报告生成器"""

    def __init__(self, output_dir: str = "outputs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_report(self, final_state: Dict, question_id: str = "Q1"):
        """
        生成完整报告

        Args:
            final_state: LangGraph最终状态
            question_id: 问题ID（用于文件命名）
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_dir = self.output_dir / f"{question_id}_{timestamp}"
        report_dir.mkdir(parents=True, exist_ok=True)

        print(f"[FullRefReport] 生成报告到: {report_dir}")

        # 1. 生成完整的Markdown报告
        self._generate_markdown_report(final_state, report_dir, question_id)

        # 2. 生成原始JSON数据
        self._generate_raw_json(final_state, report_dir, question_id)

        # 3. 生成简化版JSON（只保留metadata和分数）
        self._generate_summary_json(final_state, report_dir, question_id)

        # 4. 生成分析报告
        analysis_dir = report_dir / "analysis"
        analysis_dir.mkdir(exist_ok=True)
        self._generate_retrieval_analysis(final_state, analysis_dir)
        self._generate_rerank_analysis(final_state, analysis_dir)
        self._generate_citation_mapping(final_state, analysis_dir)

        print(f"[FullRefReport] ✅ 报告生成完成！")
        print(f"[FullRefReport] 📁 报告目录: {report_dir}")

        return report_dir

    def _generate_markdown_report(self, state: Dict, report_dir: Path, qid: str):
        """生成人类可读的Markdown完整报告"""

        md_content = []

        # 标题
        md_content.append(f"# {qid} 完整检索链路报告\n")
        md_content.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        md_content.append("---\n")

        # 原始问题
        md_content.append("## 原始问题\n")
        md_content.append(f"{state.get('question', 'N/A')}\n")

        # 提取的参数
        md_content.append("## 提取的参数\n")
        parameters = state.get('parameters', {})
        md_content.append(f"```json\n{json.dumps(parameters, ensure_ascii=False, indent=2)}\n```\n")

        # 子问题列表
        sub_questions = state.get('sub_questions', [])
        if sub_questions:
            md_content.append(f"## 子问题列表 ({len(sub_questions)}个)\n")
            for i, sq in enumerate(sub_questions, 1):
                if isinstance(sq, dict):
                    q_text = sq.get('question', sq)
                    target_year = sq.get('target_year')
                    strategy = sq.get('retrieval_strategy')
                    md_content.append(f"{i}. **{q_text}**\n")
                    if target_year:
                        md_content.append(f"   - 目标年份: `{target_year}`\n")
                    if strategy:
                        md_content.append(f"   - 检索策略: `{strategy}`\n")
                else:
                    md_content.append(f"{i}. {sq}\n")
            md_content.append("\n")

        # 检索和ReRank结果
        md_content.append("## 检索和ReRank详情\n")

        retrieval_results = state.get('retrieval_results', [])
        reranked_results = state.get('reranked_results', [])

        for i, (retrieve_item, rerank_item) in enumerate(zip(retrieval_results, reranked_results), 1):
            question = retrieve_item.get('question', f'子问题{i}')

            md_content.append(f"### 子问题 {i}: {question}\n")

            # Retrieve阶段
            retrieve_chunks = retrieve_item.get('chunks', [])
            year_dist = retrieve_item.get('year_distribution', {})
            method = retrieve_item.get('retrieval_method', 'N/A')

            md_content.append(f"#### 📥 Retrieve阶段\n")
            md_content.append(f"- **检索方法**: `{method}`\n")
            md_content.append(f"- **检索文档数**: {len(retrieve_chunks)}\n")
            md_content.append(f"- **年份分布**: {year_dist}\n")

            if retrieve_chunks:
                md_content.append(f"\n**检索到的文档 (Top 10)**:\n")
                for j, chunk in enumerate(retrieve_chunks[:10], 1):
                    score = chunk.get('score', 0.0)
                    metadata = chunk.get('metadata', {})
                    year = metadata.get('year', 'N/A')
                    speaker = metadata.get('speaker', 'N/A')
                    party = metadata.get('party', 'N/A')
                    date = metadata.get('date', 'N/A')

                    md_content.append(f"\n{j}. **{speaker} ({party}), {date}** | 相似度: `{score:.4f}`\n")

                    # 显示完整文本内容
                    text = chunk.get('text', '')
                    md_content.append(f"   > {text}\n")

            md_content.append("\n")

            # ReRank阶段
            rerank_chunks = rerank_item.get('chunks', [])
            original_count = rerank_item.get('original_count', len(retrieve_chunks))

            md_content.append(f"#### 🎯 ReRank阶段\n")
            md_content.append(f"- **输入文档数**: {original_count}\n")
            md_content.append(f"- **保留文档数**: {len(rerank_chunks)}\n")
            md_content.append(f"- **精简比例**: {len(rerank_chunks)/original_count*100:.1f}%\n")

            if rerank_chunks:
                md_content.append(f"\n**ReRank后的Top 10文档**:\n")
                for j, chunk in enumerate(rerank_chunks[:10], 1):
                    retrieval_score = chunk.get('score', chunk.get('retrieval_score', 0.0))
                    rerank_score = chunk.get('rerank_score', 0.0)
                    metadata = chunk.get('metadata', {})
                    speaker = metadata.get('speaker', 'N/A')
                    party = metadata.get('party', 'N/A')
                    date = metadata.get('date', 'N/A')

                    md_content.append(
                        f"\n{j}. **{speaker} ({party}), {date}** | "
                        f"检索: `{retrieval_score:.4f}` → ReRank: `{rerank_score:.4f}`\n"
                    )

                    # 完整文本（用于验证引用）
                    text = chunk.get('text', '')
                    md_content.append(f"\n<details>\n<summary>点击查看完整文本</summary>\n\n{text}\n\n</details>\n")

            md_content.append("\n---\n")

        # 最终答案
        md_content.append("## 最终答案\n")
        final_answer = state.get('final_answer', 'N/A')
        md_content.append(f"{final_answer}\n")

        # Quellen引用
        md_content.append("## Quellen引用映射\n")
        md_content.append("以下是答案中引用的Quellen与实际文本块的对应关系：\n\n")

        # 从答案中提取Quellen
        quellen = self._extract_quellen_from_answer(final_answer)
        md_content.append(f"**共找到 {len(quellen)} 个引用**\n\n")

        for i, q in enumerate(quellen, 1):
            md_content.append(f"{i}. `{q['citation']}`\n")

            # 尝试匹配到reranked_results中的chunk
            matched_chunks = self._match_citation_to_chunks(q, reranked_results)

            if matched_chunks:
                md_content.append(f"   **匹配到 {len(matched_chunks)} 个文本块**:\n")
                for j, chunk in enumerate(matched_chunks, 1):
                    text = chunk.get('text', '')
                    # 显示完整文本内容
                    md_content.append(f"   {j}) {text}\n\n")
            else:
                md_content.append(f"   ⚠️ **未找到匹配的文本块**\n")

            md_content.append("\n")

        # 写入文件
        md_file = report_dir / f"{qid}_full_report.md"
        md_file.write_text("".join(md_content), encoding='utf-8')
        print(f"[FullRefReport] ✅ Markdown报告已生成: {md_file}")

    def _generate_raw_json(self, state: Dict, report_dir: Path, qid: str):
        """生成完整原始JSON数据"""

        raw_data = {
            "question": state.get('question'),
            "parameters": state.get('parameters'),
            "sub_questions": state.get('sub_questions'),
            "retrieval_results": state.get('retrieval_results'),
            "reranked_results": state.get('reranked_results'),
            "final_answer": state.get('final_answer'),
            "overall_year_distribution": state.get('overall_year_distribution'),
            "intent": state.get('intent'),
            "question_type": state.get('question_type'),
        }

        json_file = report_dir / f"{qid}_raw_data.json"
        json_file.write_text(
            json.dumps(raw_data, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        print(f"[FullRefReport] ✅ 原始JSON已生成: {json_file}")

    def _generate_summary_json(self, state: Dict, report_dir: Path, qid: str):
        """生成简化版JSON（只保留metadata和分数）"""

        summary_data = {
            "question": state.get('question'),
            "parameters": state.get('parameters'),
            "sub_questions_summary": [],
            "overall_stats": {
                "total_retrieved": 0,
                "total_reranked": 0,
                "year_distribution": state.get('overall_year_distribution', {})
            }
        }

        retrieval_results = state.get('retrieval_results', [])
        reranked_results = state.get('reranked_results', [])

        for retrieve_item, rerank_item in zip(retrieval_results, reranked_results):
            question = retrieve_item.get('question')

            # 统计
            retrieve_count = len(retrieve_item.get('chunks', []))
            rerank_count = len(rerank_item.get('chunks', []))

            summary_data['overall_stats']['total_retrieved'] += retrieve_count
            summary_data['overall_stats']['total_reranked'] += rerank_count

            # 简化的子问题数据（只保留metadata和分数）
            sub_summary = {
                "question": question,
                "retrieval_method": retrieve_item.get('retrieval_method'),
                "year_distribution": retrieve_item.get('year_distribution'),
                "retrieve_count": retrieve_count,
                "rerank_count": rerank_count,
                "chunks_metadata": []
            }

            # 只保留metadata和分数
            for chunk in rerank_item.get('chunks', []):
                chunk_meta = {
                    "metadata": chunk.get('metadata'),
                    "retrieval_score": chunk.get('score', chunk.get('retrieval_score')),
                    "rerank_score": chunk.get('rerank_score'),
                    "text_length": len(chunk.get('text', ''))
                }
                sub_summary['chunks_metadata'].append(chunk_meta)

            summary_data['sub_questions_summary'].append(sub_summary)

        json_file = report_dir / f"{qid}_summary.json"
        json_file.write_text(
            json.dumps(summary_data, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        print(f"[FullRefReport] ✅ 简化JSON已生成: {json_file}")

    def _generate_retrieval_analysis(self, state: Dict, analysis_dir: Path):
        """生成检索质量分析报告"""

        md_content = []
        md_content.append("# 检索质量分析\n\n")

        retrieval_results = state.get('retrieval_results', [])

        # 统计信息
        total_retrieved = sum(len(r.get('chunks', [])) for r in retrieval_results)
        avg_per_question = total_retrieved / len(retrieval_results) if retrieval_results else 0

        md_content.append("## 整体统计\n")
        md_content.append(f"- 子问题数: {len(retrieval_results)}\n")
        md_content.append(f"- 总检索文档数: {total_retrieved}\n")
        md_content.append(f"- 平均每题文档数: {avg_per_question:.1f}\n\n")

        # 年份分布
        md_content.append("## 年份分布\n")
        year_dist = state.get('overall_year_distribution', {})
        for year, count in sorted(year_dist.items()):
            md_content.append(f"- {year}: {count} 个文档\n")

        md_content.append("\n")

        # 相似度分布
        md_content.append("## 相似度分数分布\n")
        all_scores = []
        for r in retrieval_results:
            for chunk in r.get('chunks', []):
                score = chunk.get('score', 0.0)
                all_scores.append(score)

        if all_scores:
            md_content.append(f"- 最高分: {max(all_scores):.4f}\n")
            md_content.append(f"- 最低分: {min(all_scores):.4f}\n")
            md_content.append(f"- 平均分: {sum(all_scores)/len(all_scores):.4f}\n")

            # 分数区间分布
            bins = [0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.0]
            md_content.append("\n**分数区间分布**:\n")
            for i in range(len(bins) - 1):
                count = sum(1 for s in all_scores if bins[i] >= s > bins[i+1])
                percentage = count / len(all_scores) * 100
                md_content.append(f"- {bins[i]:.1f} ~ {bins[i+1]:.1f}: {count} ({percentage:.1f}%)\n")

        # 写入文件
        md_file = analysis_dir / "retrieval_analysis.md"
        md_file.write_text("".join(md_content), encoding='utf-8')
        print(f"[FullRefReport] ✅ 检索分析已生成: {md_file}")

    def _generate_rerank_analysis(self, state: Dict, analysis_dir: Path):
        """生成ReRank效果分析报告"""

        md_content = []
        md_content.append("# ReRank效果分析\n\n")

        reranked_results = state.get('reranked_results', [])

        # 统计信息
        total_before = sum(r.get('original_count', 0) for r in reranked_results)
        total_after = sum(len(r.get('chunks', [])) for r in reranked_results)

        md_content.append("## 整体统计\n")
        md_content.append(f"- ReRank前文档数: {total_before}\n")
        md_content.append(f"- ReRank后文档数: {total_after}\n")
        md_content.append(f"- 精简比例: {total_after/total_before*100:.1f}%\n\n")

        # ReRank分数分布
        md_content.append("## ReRank分数分布\n")
        all_rerank_scores = []
        for r in reranked_results:
            for chunk in r.get('chunks', []):
                score = chunk.get('rerank_score', 0.0)
                if score > 0:
                    all_rerank_scores.append(score)

        if all_rerank_scores:
            md_content.append(f"- 最高分: {max(all_rerank_scores):.4f}\n")
            md_content.append(f"- 最低分: {min(all_rerank_scores):.4f}\n")
            md_content.append(f"- 平均分: {sum(all_rerank_scores)/len(all_rerank_scores):.4f}\n\n")

        # 排名变化分析
        md_content.append("## 排名变化分析\n")
        md_content.append("TODO: 分析检索排名vs ReRank排名的变化\n\n")

        # 写入文件
        md_file = analysis_dir / "rerank_analysis.md"
        md_file.write_text("".join(md_content), encoding='utf-8')
        print(f"[FullRefReport] ✅ ReRank分析已生成: {md_file}")

    def _generate_citation_mapping(self, state: Dict, analysis_dir: Path):
        """生成Quellen引用映射表"""

        md_content = []
        md_content.append("# Quellen引用映射表\n\n")

        final_answer = state.get('final_answer', '')
        quellen = self._extract_quellen_from_answer(final_answer)
        reranked_results = state.get('reranked_results', [])

        md_content.append(f"## 引用统计\n")
        md_content.append(f"- 总引用数: {len(quellen)}\n\n")

        md_content.append("## 引用详情\n\n")

        for i, q in enumerate(quellen, 1):
            citation = q['citation']
            speaker = q.get('speaker', 'N/A')
            date = q.get('date', 'N/A')

            md_content.append(f"### {i}. {citation}\n")
            md_content.append(f"- 发言人: {speaker}\n")
            md_content.append(f"- 日期: {date}\n")

            # 匹配到的chunks
            matched_chunks = self._match_citation_to_chunks(q, reranked_results)
            md_content.append(f"- 匹配文本块数: {len(matched_chunks)}\n\n")

            if matched_chunks:
                md_content.append("**匹配的文本块**:\n\n")
                for j, chunk in enumerate(matched_chunks, 1):
                    metadata = chunk.get('metadata', {})
                    text = chunk.get('text', '')

                    md_content.append(f"#### 匹配 {j}\n")
                    md_content.append(f"- 年份: {metadata.get('year', 'N/A')}\n")
                    md_content.append(f"- 党派: {metadata.get('party', 'N/A')}\n")
                    md_content.append(f"- 会议: {metadata.get('session', 'N/A')}\n")
                    md_content.append(f"- ReRank分数: {chunk.get('rerank_score', 0.0):.4f}\n\n")
                    md_content.append(f"**文本内容**:\n\n{text}\n\n")
                    md_content.append("---\n\n")
            else:
                md_content.append("⚠️ **未找到匹配的文本块**\n\n")

        # 写入文件
        md_file = analysis_dir / "citation_mapping.md"
        md_file.write_text("".join(md_content), encoding='utf-8')
        print(f"[FullRefReport] ✅ 引用映射已生成: {md_file}")

    def _extract_quellen_from_answer(self, answer: str) -> List[Dict]:
        """
        从答案中提取Quellen引用（鲁棒方案，支持多种格式和fallback）

        支持的格式：
        1. "*   Name (Party), Date"
        2. "- Material X: Name (Party), Date"
        3. "- Name (Party), Date"
        4. "*   Redner: Name (Party), Date" (嵌套格式，允许缩进)
        5. "- Material X: Redner: Name (Party), Date" (混合格式)
        6. "*   Material X: Name (Party), Date" (星号 + Material)

        Fallback机制：
        1. 优先匹配 **Quellen** section
        2. 如果没有标题，在答案结尾匹配
        """
        quellen = []

        # 尝试1: 定位到Quellen section
        # 修复：使用贪婪匹配到答案结尾，而不是遇到\n\n就停止
        quellen_match = re.search(r'\*\*Quellen\*\*(.*)', answer, re.DOTALL)

        if quellen_match:
            quellen_text = quellen_match.group(1)
        else:
            # Fallback 1: 如果没有**Quellen**标题，尝试在答案结尾提取
            # 取答案最后2000字符（通常引用在结尾）
            quellen_text = answer[-2000:]

        # 支持6种引用格式，按优先级从高到低尝试匹配
        # 注意：Speaker名字可能包含括号，如"Thomas Strobl (Heilbronn)"
        # 因此需要从右往左匹配：日期 -> 最后一个括号(Party) -> Speaker

        # Pattern 6: "*   Material X: Name (Party), Date" (星号 + Material，需要最高优先级)
        pattern6 = r'^\*\s+Material\s+\d+:\s+(.+)\s+\(([^)]+)\),\s*(\d{4}-\d{2}-\d{2})$'
        matches6 = re.findall(pattern6, quellen_text, re.MULTILINE)

        # Pattern 5: "- Material X: Redner: Name (Party), Date" (横线 + Material + Redner)
        pattern5 = r'^-\s+Material\s+\d+:\s+Redner:\s+(.+)\s+\(([^)]+)\),\s*(\d{4}-\d{2}-\d{2})$'
        matches5 = re.findall(pattern5, quellen_text, re.MULTILINE)

        # Pattern 4: "    *   Redner: Name (Party), Date" (嵌套格式，带缩进和Redner前缀)
        pattern4 = r'^\s*\*\s+Redner:\s+(.+)\s+\(([^)]+)\),\s*(\d{4}-\d{2}-\d{2})$'
        matches4 = re.findall(pattern4, quellen_text, re.MULTILINE)

        # Pattern 2: "- Material X: Name (Party), Date" (横线 + Material)
        pattern2 = r'^-\s+Material\s+\d+:\s+(.+)\s+\(([^)]+)\),\s*(\d{4}-\d{2}-\d{2})$'
        matches2 = re.findall(pattern2, quellen_text, re.MULTILINE)

        # Pattern 3: "- Name (Party), Date" (纯横线，没有Material前缀)
        pattern3 = r'^-\s+(.+)\s+\(([^)]+)\),\s*(\d{4}-\d{2}-\d{2})$'
        matches3 = re.findall(pattern3, quellen_text, re.MULTILINE)

        # Pattern 1: "*   Name (Party), Date" (纯星号，没有Material/Redner前缀)
        pattern1 = r'^\*\s+(.+)\s+\(([^)]+)\),\s*(\d{4}-\d{2}-\d{2})$'
        matches1 = re.findall(pattern1, quellen_text, re.MULTILINE)

        # 合并所有匹配结果（优先级: Pattern6 > Pattern5 > Pattern4 > Pattern2 > Pattern3 > Pattern1）
        # 优先选择最特殊的格式，避免误匹配
        all_matches = matches6 if matches6 else (matches5 if matches5 else (matches4 if matches4 else (matches2 if matches2 else (matches3 if matches3 else matches1))))

        for match in all_matches:
            speaker = match[0].strip()
            party = match[1].strip()
            date = match[2].strip()

            quellen.append({
                "citation": f"{speaker} ({party}), {date}",
                "speaker": speaker,
                "party": party,
                "date": date
            })

        return quellen

    def _normalize_date(self, date_str: str) -> str:
        """标准化日期格式为 YYYY-MM-DD (补零)"""
        if not date_str:
            return date_str

        try:
            from datetime import datetime
            # 尝试解析多种格式
            for fmt in ['%Y-%m-%d', '%Y-%m-%d']:
                try:
                    dt = datetime.strptime(date_str.strip(), fmt)
                    return dt.strftime('%Y-%m-%d')  # 统一为补零格式
                except ValueError:
                    continue

            # 如果无法解析，尝试手动补零
            parts = date_str.strip().split('-')
            if len(parts) == 3:
                year, month, day = parts
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

            return date_str
        except Exception:
            return date_str

    def _match_citation_to_chunks(self, citation: Dict, reranked_results: List) -> List[Dict]:
        """将引用匹配到具体的文本块"""
        matched_chunks = []

        citation_speaker = citation.get('speaker', '').strip().lower()
        citation_date = self._normalize_date(citation.get('date', ''))

        # 在所有reranked_results中查找匹配
        for result in reranked_results:
            for chunk in result.get('chunks', []):
                metadata = chunk.get('metadata', {})

                chunk_speaker = metadata.get('speaker', '').strip().lower()
                chunk_date = self._normalize_date(metadata.get('date', ''))

                # 匹配: speaker名字包含 + 日期标准化后相等
                if citation_speaker in chunk_speaker and citation_date == chunk_date:
                    matched_chunks.append(chunk)

        return matched_chunks


def main():
    """主函数：从test_langgraph_complete.py的结果生成报告"""
    import sys

    if len(sys.argv) < 2:
        print("用法: python generate_full_ref_report.py <final_state.json>")
        print("或者: 在test_langgraph_complete.py中调用generate_report()")
        return

    # 读取final_state
    json_file = sys.argv[1]
    with open(json_file, 'r', encoding='utf-8') as f:
        final_state = json.load(f)

    # 生成报告
    generator = FullRefReportGenerator(output_dir="outputs")
    report_dir = generator.generate_report(final_state, question_id="Q1")

    print(f"\n✅ 报告生成完成！")
    print(f"📁 报告目录: {report_dir}")
    print(f"\n请查看:")
    print(f"  - Q1_full_report.md: 完整的人类可读报告")
    print(f"  - Q1_raw_data.json: 原始数据")
    print(f"  - Q1_summary.json: 简化版数据")
    print(f"  - analysis/: 分析报告")


if __name__ == "__main__":
    main()
