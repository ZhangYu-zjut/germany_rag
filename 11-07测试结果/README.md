# 11-07测试结果说明

## 修复内容

本次修复针对问题5和问题6发现的bug:

### 问题5: ComparisonTemplate时间范围bug
**原问题**: "请对比2015-2017年联盟党与绿党在移民融合政策方面的主张"只生成2015年的子问题

**根本原因**: `ComparisonTemplate`只使用`start_year`,忽略了时间范围

**修复方案** (`src/graph/templates/decompose_templates.py:280-356`):
- 检查`start_year`和`end_year`是否存在
- 如果时间跨度≤5年,按年拆解
- 如果>5年,使用范围描述

### 问题6: Extract年份展开逻辑bug  
**原问题**: "2019年与2017年相比,联邦议会关于难民遣返的讨论有何变化?"提取了[2017, 2018, 2019],应该只有[2017, 2019]

**根本原因**: `extract_enhanced.py`自动填充中间年份

**修复方案** (`src/graph/nodes/extract_enhanced.py:119-362`):
1. Prompt增强: 明确指出"XX年与YY年相比"只提取离散年份
2. 保护逻辑1: 检测"与...相比"模式,保留LLM提取的年份
3. 保护逻辑2: 如果LLM提供的年份数量与范围不匹配,信任LLM

### 问题8: workflow.py导入错误 ⭐⭐⭐
**致命问题**: `workflow.py`导入了基础版`ExtractNode`,而不是增强版`EnhancedExtractNode`!

**修复方案** (`src/graph/workflow.py:9-19`):
```python
# 修复前
from .nodes import (
    ClassifyNode,
    ExtractNode,  # ❌ WRONG
    RetrieveNode,
    ReRankNode,
)

# 修复后  
from .nodes import (
    ClassifyNode,
    RetrieveNode,
    ReRankNode,
)
from .nodes.extract_enhanced import EnhancedExtractNode as ExtractNode  # ✅ CORRECT
```

## 修复验证

运行`test_fix_validation.py`针对问题5和6进行验证:

**结果**: ✅ 两个问题全部通过

详细验证日志见: `fix_validation_AFTER_workflow_fix.log`

## 文件说明

- `README.md`: 本文件,修复说明
- `LANGGRAPH_TEST_REPORT_WITH_FIXES.md`: 原完整测试报告副本
- `fix_validation_AFTER_workflow_fix.log`: 修复后的验证测试日志
- `workflow_fix_summary.md`: 修复总结

## 修复后的改进

1. 问题5: 现在正确生成2015、2016、2017年的子问题
2. 问题6: 现在只提取2017和2019年,不再包含2018年
3. 所有时间范围相关的问题处理更加准确

