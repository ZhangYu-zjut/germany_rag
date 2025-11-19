"""
增强版参数提取节点
支持时间语义理解("2015年以来"、"近年来"等)
"""

import json
import re
from typing import Dict, Optional
from datetime import datetime
from ...llm.client import GeminiLLMClient
from ...llm.prompts import PromptTemplates
from ...utils.logger import logger
from ..state import GraphState, update_state


class EnhancedExtractNode:
    """
    增强版参数提取节点

    新增功能:
    1. 时间语义理解: "2015年以来" -> ['2015', '2016', ..., '2024']
    2. 相对时间理解: "近年来" -> 近3-5年
    3. 更智能的年份范围展开
    4. 输出详细的提取思考过程
    """

    def __init__(self, llm_client: GeminiLLMClient = None):
        """
        初始化参数提取节点

        Args:
            llm_client: LLM客户端,如果为None则自动创建
        """
        self.llm = llm_client or GeminiLLMClient()
        self.prompts = PromptTemplates()
        self.current_year = datetime.now().year

    def __call__(self, state: GraphState) -> GraphState:
        """
        执行参数提取

        Args:
            state: 当前状态

        Returns:
            更新后的状态
        """
        question = state["question"]
        logger.info(f"[EnhancedExtractNode] 开始提取参数: {question}")

        thinking_process = []
        thinking_process.append("=== 参数提取过程 ===")
        thinking_process.append(f"原始问题: {question}")

        try:
            # 1. LLM提取基础参数
            prompt = self._build_enhanced_prompt(question)
            response = self.llm.invoke(prompt)

            logger.debug(f"[EnhancedExtractNode] LLM响应: {response[:200]}...")
            thinking_process.append(f"LLM提取结果: {response[:200]}...")

            # 2. 解析响应
            parameters = self._parse_response(response)
            thinking_process.append(f"解析后参数: {json.dumps(parameters, ensure_ascii=False)}")

            # 3. 增强时间语义理解
            parameters = self._enhance_time_semantics(question, parameters, thinking_process)
            thinking_process.append(f"增强后参数: {json.dumps(parameters, ensure_ascii=False)}")

            logger.info(
                f"[EnhancedExtractNode] 提取参数完成: "
                f"{json.dumps(parameters, ensure_ascii=False, indent=2)}"
            )

            # 4. 判断是否需要拆解
            is_decomposed = self._need_decomposition(state, parameters)
            thinking_process.append(f"需要拆解: {is_decomposed}")

            # 输出思考过程
            logger.info(f"\n[提取思考过程]\n" + "\n".join(thinking_process))

            # 更新状态
            return update_state(
                state,
                parameters=parameters,
                is_decomposed=is_decomposed,
                extraction_thinking="\n".join(thinking_process),
                current_node="extract",
                next_node="decompose" if is_decomposed else "retrieve"
            )

        except Exception as e:
            logger.error(f"[EnhancedExtractNode] 参数提取失败: {str(e)}")
            thinking_process.append(f"提取失败: {str(e)}")

            # 返回空参数,继续流程
            return update_state(
                state,
                parameters={},
                is_decomposed=False,
                extraction_thinking="\n".join(thinking_process),
                current_node="extract",
                next_node="retrieve"
            )

    def _build_enhanced_prompt(self, question: str) -> str:
        """
        构建增强版提取Prompt

        Args:
            question: 问题

        Returns:
            Prompt文本
        """
        enhanced_prompt = f"""你是一个专业的时间和参数提取专家。请从问题中提取关键参数。

【重要】特别注意时间语义理解：
- "2015年以来" = 从2015年到当前年份({self.current_year})
- "近年来" = 近3-5年
- "最近几年" = 近3年
- "XXX之后" = 从XXX年到当前
- "XXX以前" = 从较早年份到XXX年
- "2015-2017年" = 2015、2016、2017年（连续范围）
- "2019年与2017年相比" = 仅2019年、2017年（离散对比，不要填充中间年份！）

【关键】对于"XX年与YY年相比"这种离散对比：
- 只输出 specific_years: ["2017", "2019"]
- 不要填充中间年份（如2018）
用户问题: {question}

【提取规则】

1. **时间范围** (最重要!)
   - 识别年份: "2019年" → start_year="2019", end_year="2019", specific_years=["2019"]
   - 识别连续范围: "2015-2018年" → start_year="2015", end_year="2018", specific_years=["2015","2016","2017","2018"]
   - ⚠️ **离散对比**: "2019年与2017年相比" → start_year="2017", end_year="2019", specific_years=["2017","2019"] (不要填充2018!)
   - 识别语义: "2015年以来" → start_year="2015", end_year="{self.current_year}"
   - 识别相对: "近年来" → start_year="{self.current_year - 3}", end_year="{self.current_year}"
   - **关键**: 离散对比(如"XX年与YY年相比")只提取明确提到的年份,不要自动填充中间年份!

2. **党派**（请使用Pinecone存储的标准名称）
   - CDU/CSU
   - SPD
   - FDP
   - Grüne/Bündnis 90（不要用BÜNDNIS 90/DIE GRÜNEN）
   - DIE LINKE
   - AfD
   - "不同党派"/"各党派" → ["ALL_PARTIES"]

3. **议员**
   - 保持原格式

4. **主题**
   - 核心议题关键词

【输出格式】

```json
{{
    "time_range": {{
        "start_year": "YYYY",
        "end_year": "YYYY",
        "specific_years": ["YYYY", "YYYY", ...],  // 展开的年份列表
        "time_expression": "原始时间表述"
    }},
    "parties": ["党派1"] 或 ["ALL_PARTIES"] 或 null,
    "speakers": ["议员1"] 或 null,
    "topics": ["主题1", "主题2"],
    "keywords": ["关键词1"]
}}
```

【示例】

问题1: "请概述2015年以来德国基民盟对难民政策的立场发生了哪些主要变化。"

```json
{{
    "time_range": {{
        "start_year": "2015",
        "end_year": "{self.current_year}",
        "specific_years": ["2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024"],
        "time_expression": "2015年以来"
    }},
    "parties": ["CDU/CSU"],
    "speakers": null,
    "topics": ["难民", "难民政策"],
    "keywords": ["变化", "立场"]
}}
```

问题2: "2017年，德国联邦议会中各党派对专业人才移民制度改革分别持什么立场？"

```json
{{
    "time_range": {{
        "start_year": "2017",
        "end_year": "2017",
        "specific_years": ["2017"],
        "time_expression": "2017年"
    }},
    "parties": ["ALL_PARTIES"],
    "speakers": null,
    "topics": ["专业人才移民", "移民制度改革"],
    "keywords": ["立场", "改革"]
}}
```

问题3 (⚠️ 重要示例 - 离散对比): "2019年与2017年相比，联邦议会关于难民遣返的讨论有何变化？"

```json
{{
    "time_range": {{
        "start_year": "2017",
        "end_year": "2019",
        "specific_years": ["2017", "2019"],
        "time_expression": "2019年与2017年相比"
    }},
    "parties": ["ALL_PARTIES"],
    "speakers": null,
    "topics": ["难民遣返", "难民"],
    "keywords": ["变化", "讨论"]
}}
```

现在请提取用户问题的参数。只输出JSON代码块，不要包含任何解释。
"""
        return enhanced_prompt

    def _parse_response(self, response: str) -> Dict:
        """
        解析LLM响应,提取参数

        Args:
            response: LLM响应文本

        Returns:
            参数字典
        """
        # 尝试提取JSON
        try:
            # 查找JSON代码块
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 查找第一个完整的JSON对象
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    json_str = response

            # 解析JSON
            parameters = json.loads(json_str)

            # 清理空值
            parameters = self._clean_parameters(parameters)

            return parameters

        except json.JSONDecodeError as e:
            logger.warning(f"[EnhancedExtractNode] JSON解析失败: {str(e)}, 使用规则提取")
            return self._rule_based_extraction(response)

    def _enhance_time_semantics(
        self,
        question: str,
        parameters: Dict,
        thinking_process: list
    ) -> Dict:
        """
        增强时间语义理解

        处理:
        1. "2015年以来" -> 展开为['2015', ..., '2024']
        2. "近年来" -> 近3-5年
        3. 确保specific_years总是填充

        Args:
            question: 原始问题
            parameters: 已提取的参数
            thinking_process: 思考过程列表

        Returns:
            增强后的参数
        """
        thinking_process.append("\n--- 时间语义增强 ---")

        time_range = parameters.get("time_range", {})
        if not time_range:
            return parameters

        start_year = time_range.get("start_year")
        end_year = time_range.get("end_year")
        specific_years = time_range.get("specific_years", [])

        # 特殊语义识别
        semantic_patterns = [
            (r'(\d{4})\s*年以来', 'since_year'),
            (r'近年来', 'recent_years'),
            (r'最近几年', 'last_few_years'),
            (r'(\d{4})\s*年之后', 'after_year'),
        ]

        for pattern, sem_type in semantic_patterns:
            match = re.search(pattern, question)
            if match:
                thinking_process.append(f"识别语义: {sem_type}")

                if sem_type == 'since_year':
                    year = match.group(1)
                    start_year = year
                    end_year = str(self.current_year - 1)  # 使用2024作为截止
                    thinking_process.append(f"'{year}年以来' -> {start_year}~{end_year}")

                elif sem_type == 'recent_years':
                    start_year = str(self.current_year - 3)
                    end_year = str(self.current_year - 1)
                    thinking_process.append(f"'近年来' -> {start_year}~{end_year}")

                elif sem_type == 'last_few_years':
                    start_year = str(self.current_year - 2)
                    end_year = str(self.current_year - 1)
                    thinking_process.append(f"'最近几年' -> {start_year}~{end_year}")

                elif sem_type == 'after_year':
                    year = match.group(1)
                    start_year = str(int(year) + 1)
                    end_year = str(self.current_year - 1)
                    thinking_process.append(f"'{year}年之后' -> {start_year}~{end_year}")

                break

        # 🔒 保护措施1: 检测离散对比模式（"XX年与YY年相比"）
        is_discrete_comparison = False
        if "与" in question and "相比" in question:
            if specific_years and len(specific_years) >= 2:
                # LLM已经正确识别了离散年份，保持不变
                thinking_process.append(f"检测到离散对比模式，保留LLM提取的年份: {specific_years}")
                is_discrete_comparison = True

        # 展开年份范围
        if start_year and end_year and not is_discrete_comparison:
            try:
                start = int(start_year)
                end = int(end_year)

                # 🔒 保护措施2: 如果LLM已提供specific_years且与范围不匹配，信任LLM
                if specific_years:
                    expected_count = end - start + 1
                    if len(specific_years) != expected_count:
                        # LLM提供的年份数量与范围不匹配，可能是离散对比
                        thinking_process.append(
                            f"LLM提取的年份({len(specific_years)}个)与范围({expected_count}个)不匹配，"
                            f"保留LLM结果: {specific_years}"
                        )
                        # 不展开，保留LLM提取的结果
                    else:
                        # 数量匹配，继续展开验证
                        year_list = [str(y) for y in range(start, end + 1)]
                        specific_years = year_list
                        thinking_process.append(f"展开年份: {len(year_list)}年 ({year_list[0]}~{year_list[-1]})")
                else:
                    # LLM未提供specific_years，自动展开
                    year_list = [str(y) for y in range(start, end + 1)]

                    # 限制范围（避免过长）
                    if len(year_list) > 30:
                        thinking_process.append(f"警告: 年份跨度过大({len(year_list)}年), 限制到30年")
                        year_list = year_list[:30]

                    specific_years = year_list
                    thinking_process.append(f"展开年份: {len(year_list)}年 ({year_list[0]}~{year_list[-1]})")

            except Exception as e:
                logger.warning(f"[EnhancedExtractNode] 年份展开失败: {str(e)}")
                thinking_process.append(f"年份展开失败: {str(e)}")

        # 更新参数
        parameters["time_range"] = {
            "start_year": start_year,
            "end_year": end_year,
            "specific_years": specific_years,
            "time_expression": time_range.get("time_expression")
        }

        return parameters

    def _clean_parameters(self, params: Dict) -> Dict:
        """清理参数,移除空值"""
        cleaned = {}

        for key, value in params.items():
            if isinstance(value, dict):
                cleaned_sub = {k: v for k, v in value.items() if v and v != "null"}
                if cleaned_sub:
                    cleaned[key] = cleaned_sub
            elif isinstance(value, list):
                cleaned_list = [v for v in value if v and v != "null"]
                if cleaned_list:
                    cleaned[key] = cleaned_list
            elif value and value != "null":
                cleaned[key] = value

        return cleaned

    def _rule_based_extraction(self, text: str) -> Dict:
        """基于规则的参数提取(备用方案)"""
        params = {
            "time_range": {},
            "parties": [],
            "speakers": [],
            "topics": [],
            "keywords": []
        }

        # 提取年份
        years = re.findall(r'\b(19\d{2}|20\d{2})\b', text)
        if years:
            params["time_range"]["specific_years"] = list(set(years))
            if len(years) >= 2:
                params["time_range"]["start_year"] = min(years)
                params["time_range"]["end_year"] = max(years)

        # 提取常见党派
        parties = ["CDU/CSU", "SPD", "FDP", "GRÜNE", "DIE LINKE", "AfD"]
        for party in parties:
            if party in text:
                params["parties"].append(party)

        return params

    def _need_decomposition(self, state: GraphState, parameters: Dict) -> bool:
        """判断是否需要问题拆解"""
        # 如果是简单问题,不需要拆解
        if state.get("intent") == "simple":
            return False

        # 复杂问题的拆解条件
        question_type = state.get("question_type", "")

        # 变化类、对比类、总结类通常需要拆解
        if question_type in ["变化类", "对比类", "总结类"]:
            return True

        # 如果涉及多个维度,需要拆解
        time_range = parameters.get("time_range", {})
        parties = parameters.get("parties", [])

        # 多年份 + 多党派 = 需要拆解
        years = time_range.get("specific_years", [])
        if len(years) > 2 and len(parties) > 1:
            return True

        return False


if __name__ == "__main__":
    # 测试增强版提取节点
    from ..state import create_initial_state, update_state

    print("=== 增强版参数提取测试 ===")

    # 测试"2015年以来"
    question = "请概述2015年以来德国基民盟对难民政策的立场发生了哪些主要变化。"
    state = create_initial_state(question)
    state = update_state(state, intent="complex", question_type="变化类")

    print(f"问题: {question}")
    print("\n如需完整测试,请确保LLM客户端配置正确")
    print("\n预期提取结果:")
    print("- start_year: 2015")
    print("- end_year: 2024")
    print("- specific_years: ['2015', '2016', ..., '2024']")
    print("- parties: ['CDU/CSU']")
