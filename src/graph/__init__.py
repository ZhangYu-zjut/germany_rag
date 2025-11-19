"""
LangGraph工作流模块

实现CoA (Chain of Agents) 工作流:
1. 意图判断 - 判断问题复杂度
2. 问题分类 - 分类问题类型
3. 参数提取 - 提取关键参数
4. 问题拆解 - 拆解复杂问题
5. 数据检索 - 混合检索
6. 总结 - 生成答案
7. 异常处理 - 兜底处理
"""

from .state import GraphState
from .workflow import QuestionAnswerWorkflow

__all__ = [
    "GraphState",
    "QuestionAnswerWorkflow",
]
