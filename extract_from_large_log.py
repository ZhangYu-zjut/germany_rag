#!/usr/bin/env python3
"""
从大型日志文件中分段提取7个问题的完整Q&A内容
"""
import re
from pathlib import Path

def clean_ansi_codes(text):
    """移除ANSI颜色代码"""
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    return ansi_escape.sub('', text)

def extract_qa_from_large_log(log_file):
    """逐行读取大型日志文件，提取7个问题的Q&A"""

    qa_pairs = []

    current_question_num = None
    current_question_desc = None
    current_question_text = None
    current_answer_lines = []
    in_final_answer_section = False

    print(f"📖 开始逐行读取日志文件: {log_file}")
    print(f"   文件大小: {log_file.stat().st_size / 1024 / 1024:.1f} MB")
    print()

    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line_num, line in enumerate(f, 1):
            # 清理ANSI代码
            clean_line = clean_ansi_codes(line)

            # 检测新问题开始
            q_match = re.search(r'📝 问题 (\d)/7[:\s]+(.+?)(?:\n|$)', clean_line)
            if q_match:
                # 保存上一个问题的答案
                if current_question_num and current_answer_lines:
                    answer = '\n'.join(current_answer_lines).strip()
                    qa_pairs.append({
                        'number': current_question_num,
                        'description': current_question_desc,
                        'question': current_question_text or "未找到问题原文",
                        'answer': answer if answer else "⚠️ 未找到完整答案"
                    })
                    print(f"✅ 提取完成 Q{current_question_num}: {len(answer)} 字符")

                # 开始新问题
                current_question_num = q_match.group(1)
                current_question_desc = q_match.group(2).strip()
                current_question_text = None
                current_answer_lines = []
                in_final_answer_section = False

                print(f"📝 检测到 Q{current_question_num}: {current_question_desc}")
                continue

            # 提取问题原文（在问题标题后的几行内）
            if current_question_num and not current_question_text:
                q_text_match = re.search(r'问题[:\s]+(.+?)(?:\n|$)', clean_line)
                if q_text_match:
                    current_question_text = q_text_match.group(1).strip()

            # 检测 "✅ 最终答案" 段落开始
            if '最终答案' in clean_line and current_question_num:
                in_final_answer_section = True
                current_answer_lines = []  # 清空之前的内容
                continue

            # 收集最终答案的内容
            if in_final_answer_section:
                # 检测答案段落结束（遇到新的问题或分隔线）
                if re.match(r'-{40,}', clean_line):
                    continue  # 跳过分隔线
                if re.match(r'={40,}', clean_line):
                    in_final_answer_section = False
                    continue
                if '📝 问题' in clean_line or '测试完成' in clean_line:
                    in_final_answer_section = False
                    continue

                # 添加内容行（跳过空行和时间戳）
                if clean_line.strip() and not re.match(r'^\d{4}-\d{2}-\d{2}', clean_line):
                    current_answer_lines.append(clean_line.rstrip())

        # 保存最后一个问题
        if current_question_num and current_answer_lines:
            answer = '\n'.join(current_answer_lines).strip()
            qa_pairs.append({
                'number': current_question_num,
                'description': current_question_desc,
                'question': current_question_text or "未找到问题原文",
                'answer': answer if answer else "⚠️ 未找到完整答案"
            })
            print(f"✅ 提取完成 Q{current_question_num}: {len(answer)} 字符")

    print()
    print(f"📊 总共提取了 {len(qa_pairs)} 个问题")
    return qa_pairs

def generate_markdown_report(qa_pairs, output_file):
    """生成完整Q&A的markdown报告"""

    report = """# Quellen格式修复 - 7个问题完整测试结果

**测试时间**: 2025-11-10 11:20 - 11:58
**测试目的**: 验证Quellen格式修复后的完整问答效果
**修复内容**: 所有Summarize prompt模板已添加Quellen section

---

"""

    for qa in qa_pairs:
        report += f"""## 问题 {qa['number']}/7: {qa['description']}

### 问题
{qa['question']}

### 回答

{qa['answer']}

---

"""

    # 添加总结
    successful_count = sum(1 for qa in qa_pairs if '未找到' not in qa['answer'])
    quellen_count = sum(1 for qa in qa_pairs if '**Quellen**' in qa['answer'] or 'Quellen:' in qa['answer'])

    report += f"""## 测试总结

- **测试问题数**: {len(qa_pairs)}
- **成功生成答案**: {successful_count}
- **包含Quellen**: {quellen_count}

**验证结果**: {'所有问题均成功生成答案并包含Quellen引用来源 ✅' if quellen_count == len(qa_pairs) else '部分问题缺少Quellen引用'}

---

**报告生成时间**: 2025-11-10
**日志来源**: `11-07测试结果/test_AFTER_QUELLEN_FIX.log`
"""

    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"✅ 报告已生成: {output_file}")
    print(f"   包含 {len(qa_pairs)} 个问题的完整问答内容")
    print(f"   成功生成答案: {successful_count}/{len(qa_pairs)}")
    print(f"   包含Quellen: {quellen_count}/{len(qa_pairs)}")

if __name__ == "__main__":
    log_file = Path("11-07测试结果/test_AFTER_QUELLEN_FIX.log")
    output_file = Path("11-07测试结果/COMPLETE_QA_REPORT.md")

    print("="*60)
    print("从大型日志文件提取完整问答内容")
    print("="*60)
    print()

    if not log_file.exists():
        print(f"❌ 错误: 日志文件不存在: {log_file}")
        exit(1)

    # 提取Q&A
    qa_pairs = extract_qa_from_large_log(log_file)

    if not qa_pairs:
        print("❌ 错误: 未能提取任何问答对")
        exit(1)

    print()
    print("="*60)
    print("生成markdown报告")
    print("="*60)
    print()

    # 生成报告
    generate_markdown_report(qa_pairs, output_file)
    print()
    print("🎉 完成！")
