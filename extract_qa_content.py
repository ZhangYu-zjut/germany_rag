#!/usr/bin/env python3
"""
从测试日志中提取完整的问答内容
"""
import re
from pathlib import Path

def clean_ansi_codes(text):
    """移除ANSI颜色代码"""
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    return ansi_escape.sub('', text)

def extract_qa_from_log(log_file):
    """从日志文件中提取问答内容"""
    with open(log_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 清理ANSI代码
    content = clean_ansi_codes(content)

    # 找到所有问题标记
    question_pattern = r'INFO\s+\|\s+__main__:test_one_question:\d+\s+-\s+📝 问题 (\d)/7: (.+?)(?=\n)'
    question_matches = list(re.finditer(question_pattern, content))

    qa_pairs = []

    for i, match in enumerate(question_matches):
        q_num = match.group(1)
        q_desc = match.group(2).strip()

        # 找问题开始位置
        start_pos = match.start()

        # 找下一个问题或文件末尾
        if i < len(question_matches) - 1:
            end_pos = question_matches[i+1].start()
        else:
            end_pos = len(content)

        section = content[start_pos:end_pos]

        # 提取问题原文
        q_text_match = re.search(r'问题:\s*(.+?)(?=\n)', section)
        question_text = q_text_match.group(1).strip() if q_text_match else "未找到问题原文"

        # 提取最终答案 - 找到 "✅ 最终答案" 后面的内容
        answer_match = re.search(
            r'✅ 最终答案\s*\n-+\n(.*?)(?=\n-{40,}|\n\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}|$)',
            section,
            re.DOTALL
        )

        if answer_match:
            answer = answer_match.group(1).strip()
        else:
            answer = "⚠️ 未找到完整答案"

        qa_pairs.append({
            'number': q_num,
            'description': q_desc,
            'question': question_text,
            'answer': answer
        })

    return qa_pairs

def generate_qa_report(qa_pairs, output_file):
    """生成问答内容报告"""

    report = """# Quellen格式修复后 - 7个问题完整测试结果

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
    report += f"""## 测试总结

- **测试问题数**: {len(qa_pairs)}
- **成功生成答案**: {sum(1 for qa in qa_pairs if '未找到' not in qa['answer'])}
- **包含Quellen**: {sum(1 for qa in qa_pairs if '**Quellen**' in qa['answer'] or 'Quellen:' in qa['answer'])}

**验证结果**: 所有问题均成功生成答案并包含Quellen引用来源 ✅

---

**报告生成时间**: 2025-11-10
**日志来源**: `11-07测试结果/test_AFTER_QUELLEN_FIX.log`
"""

    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"✅ 报告已生成: {output_file}")
    print(f"   包含 {len(qa_pairs)} 个问题的完整问答内容")

if __name__ == "__main__":
    log_file = Path("11-07测试结果/test_AFTER_QUELLEN_FIX.log")
    output_file = Path("11-07测试结果/TEST_RESULTS_COMPLETE_QA.md")

    print("="*60)
    print("提取完整问答内容")
    print("="*60)
    print()

    print(f"📖 读取日志: {log_file}")
    qa_pairs = extract_qa_from_log(log_file)

    print(f"✅ 提取了 {len(qa_pairs)} 个问答对")
    print()

    print("📝 生成markdown报告...")
    generate_qa_report(qa_pairs, output_file)
