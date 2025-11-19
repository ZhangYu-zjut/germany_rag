# 问题5和问题6修复总结

**修复时间**: 2025-11-07  
**修复人**: Claude  
**验证状态**: ✅ 全部通过

---

## 一、发现的问题

### 问题5: 对比类模板时间范围处理不完整
**表现**: "请对比2015-2017年联盟党与绿党在移民融合政策方面的主张"  
→ 只生成2015年的子问题,缺少2016和2017年

**期望**: 生成2015、2016、2017三个年份的子问题

### 问题6: 离散年份对比被错误展开
**表现**: "2019年与2017年相比,联邦议会关于难民遣返的讨论有何变化?"  
→ 提取了[2017, 2018, 2019]

**期望**: 只提取[2017, 2019],不包含中间年份2018

---

## 二、根因分析

### 问题5根因
**文件**: `src/graph/templates/decompose_templates.py`  
**位置**: `ComparisonTemplate.generate_sub_questions()` (第304行)

**问题代码**:
```python
time_str = f"{start_year}年" if start_year else ""
# ❌ 只使用start_year,忽略了end_year和specific_years
```

**影响**: 对于时间范围类问题(如"2015-2017年"),只考虑起始年份,导致子问题拆解不完整

### 问题6根因
**文件**: `src/graph/nodes/extract_enhanced.py`  
**位置**: 年份范围展开逻辑 (第322行)

**问题代码**:
```python
if start_year and end_year:
    year_list = [str(y) for y in range(start, end + 1)]
    specific_years = year_list
    # ❌ 对所有范围都自动展开,不区分连续范围vs离散对比
```

**影响**: "2019年与2017年"这种离散对比被错误识别为连续范围,自动填充了中间年份

### 致命问题: workflow.py导入错误
**文件**: `src/graph/workflow.py`  
**位置**: 第11行

**问题**: 导入了基础版`ExtractNode`,而不是增强版`EnhancedExtractNode`

**影响**: 所有对`extract_enhanced.py`的修改都不生效!

---

## 三、修复方案

### 修复1: ComparisonTemplate时间范围处理 ✅

**文件**: `src/graph/templates/decompose_templates.py` (280-356行)

**修复逻辑**:
```python
def generate_sub_questions(self, parameters: Dict[str, Any]) -> List[str]:
    time_range = parameters.get("time_range", {})
    start_year = time_range.get("start_year")
    end_year = time_range.get("end_year")
    specific_years = time_range.get("specific_years", [])
    
    # 🔧 新增: 处理时间范围情况
    if start_year and end_year and start_year != end_year:
        if specific_years and len(specific_years) <= 5:
            # 时间跨度≤5年,按每年拆解
            years_to_process = specific_years  # ✅ 使用完整年份列表
        else:
            # 时间跨度>5年,使用范围描述
            time_str = f"{start_year}-{end_year}年"
            years_to_process = [time_str]
    elif start_year:
        time_str = f"{start_year}年"
        years_to_process = [time_str]
    
    # 为每个对象 × 每年生成独立问题
    for year_str in years_to_process:
        for obj in compare_objects:
            sub_questions.append(
                f"{year_str}{obj}在{topic_str}上的立场和主要观点是什么？"
            )
```

**关键改进**:
1. 检查`specific_years`字段
2. 根据时间跨度决定拆解粒度
3. 为每个年份×对象组合生成子问题

### 修复2: 离散对比年份识别 ✅

**文件**: `src/graph/nodes/extract_enhanced.py` (119-362行)

**修复1: Prompt增强**:
```python
【重要】特别注意时间语义理解：
- "2015-2017年" = 2015、2016、2017年(连续范围)
- "2019年与2017年相比" = 仅2019年、2017年(离散对比,不要填充中间年份!)

【关键】对于"XX年与YY年相比"这种离散对比：
- 只输出 specific_years: ["2017", "2019"]
- 不要填充中间年份(如2018)
```

**修复2: 双重保护逻辑**:
```python
# 🔒 保护措施1: 检测离散对比模式
is_discrete_comparison = False
if "与" in question and "相比" in question:
    if specific_years and len(specific_years) >= 2:
        # LLM已经正确识别了离散年份,保持不变
        is_discrete_comparison = True

# 展开年份范围
if start_year and end_year and not is_discrete_comparison:
    # 🔒 保护措施2: 如果LLM提供的年份与范围不匹配,信任LLM
    if specific_years:
        expected_count = end - start + 1
        if len(specific_years) != expected_count:
            # 可能是离散对比,保留LLM结果
            pass  # 不展开
        else:
            year_list = [str(y) for y in range(start, end + 1)]
            specific_years = year_list
```

**关键改进**:
1. Prompt明确指导LLM区分连续范围和离散对比
2. 检测"与...相比"模式,避免错误展开
3. 检查LLM提取的年份数量,如果不符合范围期望则信任LLM

### 修复3: workflow.py导入修正 ⭐⭐⭐

**文件**: `src/graph/workflow.py` (9-19行)

**修复前**:
```python
from .nodes import (
    ClassifyNode,
    ExtractNode,  # ❌ 基础版
    RetrieveNode,
    ReRankNode,
)
```

**修复后**:
```python
from .nodes import (
    ClassifyNode,
    RetrieveNode,
    ReRankNode,
)
# ✅ 使用增强版
from .nodes.extract_enhanced import EnhancedExtractNode as ExtractNode
```

**重要性**: 这是最致命的问题!如果不修复这个,所有对enhanced文件的修改都不生效。

---

## 四、验证结果

### 验证脚本
`test_fix_validation.py` - 只测试问题5和6

### 验证结果
```
====================================================================
问题 5 修复验证成功!
====================================================================
【参数提取验证】
  提取的年份: ['2015', '2016', '2017']
  期望年份: ['2015', '2016', '2017']
  ✅ 年份提取正确

【子问题拆解验证】
  生成子问题数: 9
  子问题中出现的年份: ['2015', '2016', '2017']
  ✅ 子问题拆解正确,包含所有期望年份

  生成的子问题:
    1. 2015CDU/CSU在移民融合、移民融合政策上的立场和主要观点是什么？
    2. 2015Grüne/Bündnis 90在移民融合、移民融合政策上的立场和主要观点是什么？
    3. 2016CDU/CSU在移民融合、移民融合政策上的立场和主要观点是什么？
    4. 2016Grüne/Bündnis 90在移民融合、移民融合政策上的立场和主要观点是什么？
    5. 2017CDU/CSU在移民融合、移民融合政策上的立场和主要观点是什么？
    ...

====================================================================
问题 6 修复验证成功!
====================================================================
【参数提取验证】
  提取的年份: ['2017', '2019']
  期望年份: ['2017', '2019']
  ✅ 年份提取正确 (不再包含2018)

【子问题拆解验证】
  生成子问题数: 4
  子问题中出现的年份: ['2017', '2019']
  ✅ 子问题拆解正确,包含所有期望年份

==================================================================
 📊 验证总结
==================================================================
成功: 2/2

🎉 所有修复验证通过!
```

**结论**: ✅ 两个问题的修复全部验证通过

---

## 五、修复文件清单

| 文件 | 修改内容 | 代码行数 |
|------|---------|---------|
| `src/graph/templates/decompose_templates.py` | ComparisonTemplate时间范围处理 | 280-356 |
| `src/graph/nodes/extract_enhanced.py` | 离散对比识别+双重保护逻辑 | 119-362 |
| `src/graph/workflow.py` | 导入EnhancedExtractNode | 9-19 |

**总计**: 3个文件, ~150行代码修改

---

## 六、影响范围

### 直接受益
- ✅ 问题5: 对比类问题时间范围完整拆解
- ✅ 问题6: 离散年份对比准确提取

### 间接受益
- 所有涉及时间范围的对比类问题
- 所有"XX年与YY年相比"格式的问题
- 提升了时间语义理解的准确性

### 无影响
- 单年份问题
- 总结类、事实查询类问题
- 不涉及时间范围的问题

---

## 七、经验教训

1. **配置一致性至关重要**: workflow.py导入错误导致所有修改无效
2. **测试要覆盖边界情况**: 离散对比vs连续范围需要明确区分
3. **双重保护更鲁棒**: Prompt指导+代码逻辑双重保护
4. **小范围验证先行**: 针对问题5和6的验证测试效率更高

---

## 八、后续建议

1. **重构节点导入机制**: 统一使用enhanced版本,避免混用
2. **增加单元测试**: 覆盖时间范围提取的各种边界情况
3. **文档化设计决策**: 记录为什么5年是时间跨度阈值
4. **监控修复效果**: 在生产环境验证修复的长期稳定性

