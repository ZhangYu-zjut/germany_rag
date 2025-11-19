#!/usr/bin/env python3
"""
简化版：从测试日志中提取7个问题的答案内容
策略：找到每个 "答案长度: XXXX 字符" 的下一行，然后读取对应长度的内容
"""
import re
from pathlib import Path

def clean_ansi(text):
    """移除ANSI代码"""
    return re.sub(r'\x1b\[[0-9;]*m', '', text)

def extract_qa_pairs(log_file):
    """从日志文件提取Q&A对"""

    # 7个问题的基本信息（从之前的验证报告获取）
    questions_info = [
        ("1", "多年变化分析 (2015-2024)", "请概述2015年以来德国基民盟对难民政策的立场发生了哪些主要变化。"),
        ("2", "单年多党派对比 (2017)", "2017年，德国联邦议会中各党派对专业人才移民制度改革分别持什么立场？"),
        ("3", "单年单党派观点 (2015)", "2015年，德国联邦议会中绿党在移民国籍问题上的主要立场和诉求是什么？"),
        ("4", "跨年多党派变化 (2015-2018)", "在2015年到2018年期间，德国联邦议会中不同党派在难民家庭团聚问题上的讨论发生了怎样的变化？"),
        ("5", "跨年两党对比 (2015-2017)", "请对比2015-2017年联盟党与绿党在移民融合政策方面的主张。"),
        ("6", "两年对比 (2017, 2019)", "2019年与2017年相比，联邦议会关于难民遣返的讨论有何变化？"),
        ("7", "跨年疫情影响分析 (2019-2021)", "新冠疫情期间（主要是2020年），联邦议院对坚持气候目标的看法发生了什么变化？请使用2019-2021年的资料进行回答。必要时给出具体引语。")
    ]

    print(f"📖 读取日志文件: {log_file}")
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # 清理ANSI代码
    content = clean_ansi(content)

    print(f"   文件大小: {len(content)} 字符")
    print()

    qa_pairs = []

    # 按照问题序号提取
    for q_num, q_desc, q_text in questions_info:
        print(f"📝 提取 Q{q_num}: {q_desc}")

        # 找到这个问题的 "答案长度" 标记
        pattern = rf'问题 {q_num} .*?答案长度:\s*(\d+)\s*字符'
        match = re.search(pattern, content, re.DOTALL)

        if not match:
            print(f"   ⚠️  未找到答案长度标记")
            qa_pairs.append({
                'number': q_num,
                'description': q_desc,
                'question': q_text,
                'answer': '⚠️ 未找到答案内容'
            })
            continue

        answer_length = int(match.group(1))
        answer_start_pos = match.end()

        # 从答案长度标记后开始读取
        # 跳过可能的换行和INFO行
        search_text = content[answer_start_pos:answer_start_pos + answer_length + 500]

        # 找到实际答案开始的位置（跳过日志行）
        lines = search_text.split('\n')
        answer_lines = []
        started = False

        for line in lines:
            # 跳过时间戳和INFO行
            if re.match(r'^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}', line):
                # 检查是否是答案内容行
                parts = line.split(' | ', maxsplit=3)
                if len(parts) >= 4:
                    # 这是logger输出，最后一部分可能是答案内容
                    answer_content = parts[-1].strip()
                    if answer_content and not answer_content.startswith('[') and not answer_content.startswith('===='):
                        answer_lines.append(answer_content)
                        started = True
            elif started and line.strip():
                # 已经开始收集答案，继续收集非空行
                if line.strip().startswith('==='):
                    break  # 遇到分隔线，结束
                answer_lines.append(line)

        answer = '\n'.join(answer_lines).strip()

        # 如果提取的长度接近预期长度，认为成功
        if abs(len(answer) - answer_length) < answer_length * 0.3:  # 允许30%误差
            print(f"   ✅ 成功提取 {len(answer)} 字符 (预期 {answer_length})")
            qa_pairs.append({
                'number': q_num,
                'description': q_desc,
                'question': q_text,
                'answer': answer if answer else '⚠️ 提取的答案为空'
            })
        else:
            print(f"   ⚠️  提取长度不匹配: {len(answer)} vs 预期 {answer_length}")
            # 即使长度不匹配，也尝试使用提取的内容
            qa_pairs.append({
                'number': q_num,
                'description': q_desc,
                'question': q_text,
                'answer': answer if answer else '⚠️ 未找到答案内容'
            })

    return qa_pairs

def generate_markdown(qa_pairs, output_file):
    """生成markdown报告"""

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

    # 统计
    successful = sum(1 for qa in qa_pairs if '未找到' not in qa['answer'])
    has_quellen = sum(1 for qa in qa_pairs if '**Quellen**' in qa['answer'] or 'Quellen:' in qa['answer'])

    report += f"""## 测试总结

- **测试问题数**: {len(qa_pairs)}
- **成功生成答案**: {successful}
- **包含Quellen**: {has_quellen}

**验证结果**: {'所有问题均成功生成答案并包含Quellen引用来源 ✅' if has_quellen == len(qa_pairs) else '部分问题需要检查'}

---

**报告生成时间**: 2025-11-10
**日志来源**: `11-07测试结果/test_AFTER_QUELLEN_FIX.log`
"""

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print()
    print(f"✅ 报告已生成: {output_file}")
    print(f"   成功提取: {successful}/{len(qa_pairs)}")
    print(f"   包含Quellen: {has_quellen}/{len(qa_pairs)}")

if __name__ == "__main__":
    log_file = Path("11-07测试结果/test_AFTER_QUELLEN_FIX.log")
    output_file = Path("11-07测试结果/COMPLETE_QA_REPORT.md")

    print("="*60)
    print("从测试日志提取完整问答内容")
    print("="*60)
    print()

    qa_pairs = extract_qa_pairs(log_file)

    if not qa_pairs:
        print("❌ 未能提取任何问答对")
        exit(1)

    print()
    print("="*60)
    print("生成Markdown报告")
    print("="*60)
    generate_markdown(qa_pairs, output_file)
    print()
    print("🎉 完成!")
