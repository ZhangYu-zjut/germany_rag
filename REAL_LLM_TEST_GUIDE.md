# 真实LLM测试指南

**目的**: 使用真实的Gemini API测试意图识别和问题分类的准确性

---

## 🚀 快速开始

### 步骤1: 激活环境

```bash
cd /Users/zhangyu/project/germany_latest/tj_germany
source venv/bin/activate
```

### 步骤2: 验证环境配置

```bash
# 检查.env文件是否存在
ls -la .env

# 验证API key（不会显示完整key）
python -c "from src.config.settings import settings; print('✅ API Key已配置' if settings.GEMINI_API_KEY else '❌ API Key未配置')"
```

### 步骤3: 运行测试

```bash
# 完整测试（意图识别 + 问题分类 + 参数提取）
python tests/test_real_llm.py
```

---

## 📋 测试内容

### 测试1: 意图判断准确性 ✅

**测试目标**: 验证系统能否正确区分简单问题和复杂问题

**测试用例**:
1. ✅ "2019年德国议会讨论了哪些主要议题？" → **简单**
2. ✅ "在2015-2018年期间，CDU/CSU和SPD在难民政策上的立场有何变化？" → **复杂**
3. ✅ "对比CDU/CSU、SPD和FDP在2019年数字化政策上的立场差异" → **复杂**
4. ⚠️ "2021年绿党在气候保护方面的主要观点是什么？" → **简单或复杂**（待LLM判断）

**预期输出**:
```
【测试1: 意图判断准确性】
--- 测试用例 1 ---
问题: 2019年德国议会讨论了哪些主要议题？
预期意图: simple (单一时间点的事实查询)
🔄 调用LLM进行意图判断...
✅ LLM返回成功
判断结果: simple
分析: 这是一个简单的事实查询...
验证: ✅ PASS
```

### 测试2: 问题分类准确性 ✅

**测试目标**: 验证系统能否正确分类问题类型

**测试用例**:
1. ✅ "在2015-2018年期间，不同党派在难民政策上的立场有何变化？" → **变化类**
2. ✅ "对比CDU/CSU和SPD在数字化政策上的立场差异" → **对比类**
3. ✅ "请总结2021年绿党在气候保护方面的主要观点" → **总结类**
4. ✅ "2010年到2020年德国议会对气候政策的态度演变趋势" → **趋势分析**
5. ✅ "2019年Merkel在欧盟一体化问题上的发言是什么？" → **事实查询**

**预期输出**:
```
【测试2: 问题分类准确性】
--- 测试用例 1 ---
问题: 在2015-2018年期间，不同党派在难民政策上的立场有何变化？
预期类型: 变化类 (明确询问'变化'，时间跨度4年)
🔄 调用LLM进行问题分类...
✅ LLM返回成功
分类结果: 变化类
验证: ✅ PASS
```

### 测试3: 参数提取准确性 ✅

**测试目标**: 验证系统能否正确提取时间、党派、主题等参数

**测试用例**:
1. ✅ "在2015-2018年期间，CDU/CSU和SPD在难民政策上的立场有何变化？"
   - 时间: 2015-2018
   - 党派: CDU/CSU, SPD
   - 主题: 难民政策

2. ✅ "2019年绿党在气候保护方面的观点"
   - 时间: 2019
   - 党派: 绿党
   - 主题: 气候保护

**预期输出**:
```
【测试3: 参数提取准确性】
--- 测试用例 1 ---
问题: 在2015-2018年期间，CDU/CSU和SPD在难民政策上的立场有何变化？
🔄 调用LLM进行参数提取...
✅ LLM返回成功
提取结果:
  - 时间: {'start_year': '2015', 'end_year': '2018'}
  - 党派: ['CDU/CSU', 'SPD']
  - 主题: ['难民政策']
验证: ✅ PASS
```

---

## 📊 评估标准

### 通过率标准

| 通过率 | 评估 | 建议 |
|--------|------|------|
| ≥80% | ✅ 优秀 | Prompt效果符合预期 |
| 60-79% | ⚠️ 良好 | 建议微调Prompt |
| <60% | ❌ 需改进 | 需要重新设计Prompt |

### 最终报告示例

```
📊 最终测试报告
================================================================================

INTENT:
  通过率: 3/4 (75.0%)

CLASSIFY:
  通过率: 4/5 (80.0%)

EXTRACT:
  通过率: 2/2 (100.0%)

总体通过率: 9/11 (81.8%)

🎉 测试结果良好！Prompt效果符合预期。
```

---

## ⚠️ 故障排查

### 问题1: LLM连接失败

**错误信息**:
```
❌ LLM连接失败: API key not found
```

**解决方案**:
1. 检查`.env`文件是否存在
2. 确认`GEMINI_API_KEY=your_key_here`已正确配置
3. 重新加载环境变量：`source venv/bin/activate`

### 问题2: 网络超时

**错误信息**:
```
❌ LLM连接失败: Connection timeout
```

**解决方案**:
1. 检查网络连接
2. 确认API endpoint可访问
3. 增加超时时间（在`src/llm/client.py`中）

### 问题3: API额度不足

**错误信息**:
```
❌ LLM连接失败: Quota exceeded
```

**解决方案**:
1. 检查Gemini API额度
2. 等待额度重置
3. 考虑升级API计划

---

## 🔧 进阶测试

### 单独测试某个节点

```python
# 只测试意图判断
from src.graph.nodes.intent_enhanced import EnhancedIntentNode
from src.graph.state import create_initial_state

question = "2015-2018年CDU/CSU在难民政策上的立场变化？"
state = create_initial_state(question)

intent_node = EnhancedIntentNode()
result = intent_node(state)

print(f"意图: {result['intent']}")
print(f"分析: {result.get('complexity_analysis', '')}")
```

### 测试自定义问题

在`test_real_llm.py`中添加你自己的测试用例：

```python
test_cases = [
    {
        "question": "你的自定义问题",
        "expected_intent": "simple",  # 或 "complex"
        "reason": "你的判断理由"
    },
    # ... 更多测试用例
]
```

---

## 📝 测试结果记录

### 建议记录内容

1. **测试时间**: 2025-11-01
2. **LLM模型**: Gemini 2.5 Pro
3. **通过率**:
   - 意图判断: ___%
   - 问题分类: ___%
   - 参数提取: ___%
4. **发现的问题**:
   - [ ] 问题1描述
   - [ ] 问题2描述
5. **改进建议**:
   - [ ] 建议1
   - [ ] 建议2

---

## 🎯 下一步

根据测试结果：

### 如果通过率≥80% ✅
→ 进入Phase 3: 完整端到端测试（包含检索和总结）

### 如果通过率60-79% ⚠️
→ 微调Prompt，重新测试

### 如果通过率<60% ❌
→ 分析失败用例，重新设计Prompt

---

## 💡 Prompt优化提示

如果测试结果不理想，可以优化：

1. **意图判断Prompt** (`src/llm/prompts.py` - `INTENT_CLASSIFICATION`)
   - 增加判断标准的具体示例
   - 调整复杂度判断的阈值描述

2. **问题分类Prompt** (`src/llm/prompts.py` - `QUESTION_CLASSIFICATION`)
   - 强化每类问题的关键词识别
   - 增加边界情况的处理说明

3. **参数提取Prompt** (`src/llm/prompts.py` - `PARAMETER_EXTRACTION`)
   - 明确参数格式要求
   - 增加党派名称的标准化规则

---

**准备好了吗？开始测试！** 🚀

```bash
cd /Users/zhangyu/project/germany_latest/tj_germany
source venv/bin/activate
python tests/test_real_llm.py
```

