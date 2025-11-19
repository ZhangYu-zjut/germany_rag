"""
增强版增量式总结节点 V2
核心改进：两阶段总结 - 结构化提取 → 基于结构生成
目标：防止信息遗漏，保持原文关键短语
"""

import json
from typing import List, Dict, Optional, Tuple
from ...llm.client import GeminiLLMClient
from ...utils.logger import logger
from ..state import GraphState, update_state


class IncrementalSummarizeNodeV2:
    """
    增强版增量式总结节点

    核心策略：
    1. 阶段1 - 结构化提取：从每个文档中提取关键信息（党派立场、具体措施、关键短语）
    2. 阶段2 - 基于结构生成：基于提取的结构化信息生成完整答案

    优势：
    - 自适应：不依赖预定义的检查清单
    - 通用：适用于任何主题（难民、环境、教育等）
    - 鲁棒：强制结构化，防止LLM遗漏关键信息
    """

    def __init__(self, llm_client: GeminiLLMClient = None):
        """初始化增量式总结节点"""
        self.llm = llm_client or GeminiLLMClient()

    def __call__(self, state: GraphState) -> GraphState:
        """
        执行两阶段总结

        Args:
            state: 当前状态

        Returns:
            更新后的状态
        """
        question = state["question"]
        question_type = state.get("question_type", "")
        reranked_results = state.get("reranked_results", [])
        retrieval_results = state.get("retrieval_results", [])

        # 优先使用重排序结果
        processing_results = reranked_results if reranked_results else retrieval_results

        logger.info(f"[IncrementalSummarizeV2] 开始两阶段总结")
        logger.info(f"[IncrementalSummarizeV2] 问题类型: {question_type}")
        logger.info(f"[IncrementalSummarizeV2] 处理结果数: {len(processing_results)}")

        try:
            # 检查是否有材料
            if not processing_results:
                logger.warning("[IncrementalSummarizeV2] 无检索结果")
                return update_state(
                    state,
                    error="未找到相关材料",
                    error_type="NO_MATERIAL",
                    no_material_found=True,
                    current_node="summarize",
                    next_node="exception"
                )

            # 执行两阶段总结
            final_answer = self._two_stage_summarize(
                question=question,
                question_type=question_type,
                processing_results=processing_results
            )

            logger.info(f"[IncrementalSummarizeV2] 总结完成")
            logger.info(f"[IncrementalSummarizeV2] 答案长度: {len(final_answer)} 字符")

            return update_state(
                state,
                final_answer=final_answer,
                current_node="summarize",
                next_node="end"
            )

        except Exception as e:
            logger.error(f"[IncrementalSummarizeV2] 总结失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

            return update_state(
                state,
                error=f"总结失败: {str(e)}",
                error_type="SUMMARIZE_ERROR",
                current_node="summarize",
                next_node="exception"
            )

    def _two_stage_summarize(
        self,
        question: str,
        question_type: str,
        processing_results: List[Dict]
    ) -> str:
        """
        两阶段总结：结构化提取 → 基于结构生成

        Args:
            question: 原始问题
            question_type: 问题类型
            processing_results: ReRank后的检索结果

        Returns:
            最终答案
        """
        # 阶段1：结构化提取
        logger.info("[IncrementalSummarizeV2] 阶段1: 结构化提取")
        extracted_info = self._extract_structured_info(
            question=question,
            processing_results=processing_results
        )

        logger.info(f"[IncrementalSummarizeV2] 提取信息: {len(extracted_info)} 个子问题")

        # 阶段2：基于结构化信息生成答案
        logger.info("[IncrementalSummarizeV2] 阶段2: 基于结构生成答案")
        final_answer = self._generate_from_structured(
            question=question,
            question_type=question_type,
            extracted_info=extracted_info,
            processing_results=processing_results
        )

        return final_answer

    def _extract_structured_info(
        self,
        question: str,
        processing_results: List[Dict]
    ) -> List[Dict]:
        """
        阶段1：从每个子问题的文档中提取结构化信息

        Args:
            question: 原始问题
            processing_results: 检索结果（按子问题分组）

        Returns:
            提取的结构化信息列表
        """
        extracted_list = []

        for idx, result in enumerate(processing_results):
            sub_question = result.get("question", question)
            chunks = result.get("chunks", [])

            if not chunks:
                logger.warning(f"[IncrementalSummarizeV2] 子问题 {idx+1} 无文档")
                continue

            logger.info(f"[IncrementalSummarizeV2] 提取子问题 {idx+1}/{len(processing_results)}: {len(chunks)} 个文档")

            # 构造提取prompt
            extraction_prompt = self._build_extraction_prompt(
                sub_question=sub_question,
                chunks=chunks
            )

            # 调用LLM提取
            try:
                extracted_text = self.llm.generate(extraction_prompt)

                # 尝试解析JSON（如果LLM返回JSON格式）
                try:
                    extracted_json = json.loads(extracted_text)
                    logger.info(f"[IncrementalSummarizeV2] 子问题 {idx+1} 提取成功（JSON格式）")
                except json.JSONDecodeError:
                    # 如果不是JSON，保留原文
                    extracted_json = {"raw_extraction": extracted_text}
                    logger.info(f"[IncrementalSummarizeV2] 子问题 {idx+1} 提取成功（文本格式）")

                extracted_list.append({
                    "sub_question": sub_question,
                    "extracted_info": extracted_json,
                    "num_chunks": len(chunks)
                })

            except Exception as e:
                logger.error(f"[IncrementalSummarizeV2] 子问题 {idx+1} 提取失败: {e}")
                # 失败时仍然添加空结构，避免遗漏子问题
                extracted_list.append({
                    "sub_question": sub_question,
                    "extracted_info": {"error": str(e)},
                    "num_chunks": len(chunks)
                })

        return extracted_list

    def _build_extraction_prompt(
        self,
        sub_question: str,
        chunks: List[Dict]
    ) -> str:
        """
        构造结构化提取的prompt

        核心要求：
        1. 提取每个党派的核心立场和具体措施
        2. 保留原文中的关键短语和术语
        3. 提取数字、日期、法律名称
        """
        # 构造文档文本
        documents_text = ""
        for i, chunk in enumerate(chunks[:15], 1):  # 最多15个文档
            text = chunk.get("text", "")
            metadata = chunk.get("metadata", {})
            speaker = metadata.get("speaker", "N/A")
            party = metadata.get("group_chinese", metadata.get("group", "N/A"))
            date = metadata.get("date", "N/A")

            documents_text += f"\n### 文档 {i} ({speaker} - {party}, {date})\n{text}\n"

        prompt = f"""您是德国议会政治分析专家。请从以下文档中提取关键信息，回答这个问题：

**问题**: {sub_question}

**【核心原则】对立观点平衡提取**：
政治立场往往包含多个维度，必须**完整提取**，避免片面化。对于每个政策主题，必须同时查找：
- 温和/人道主义立场 AND 强硬/限制性立场
- 支持性措施 AND 限制性措施
- 理想目标 AND 实际执行手段

**要求**：
1. 按照以下JSON结构提取信息：
{{
  "党派1": {{
    "政策主题A": {{
      "温和立场": ["立场1（原文短语）", "立场2", ...],
      "强硬立场": ["立场1（原文短语）", "立场2", ...],
      "具体措施": ["措施1（数字/日期/法律名）", "措施2", ...],
      "关键短语": ["Originalzitat 1", "Originalzitat 2", ...]
    }},
    "政策主题B": {{ ... }}
  }},
  "党派2": {{ ... }}
}}

2. **对立观点检查清单**（必须同时查找）：

   遣返政策：
   - 温和："拒绝遣返到不安全国家" / "人道主义考量"
   - 强硬："强制遣返" (Zwang/Abschiebung) / "加快遣返速度" / "延长拘留"

   边境管控：
   - 温和："人道主义走廊" / "接纳难民"
   - 强硬："边境管控" (Grenzkontrollen) / "上限" (Obergrenze)

   欧洲政策：
   - 温和："gemeinsame europäische Antwort" / "团结"
   - 强硬："各国责任" / "配额拒绝"

3. **关键短语**必须保留原文（德语），例如：
   - "Zwang durchsetzen" (强制执行)
   - "Ausreisegewahrsam verlängern" (延长遣返拘留)
   - "sichere Herkunftsländer" (安全来源国)
   - "gemeinsame europäische Antwort" (共同的欧洲答案)

4. **具体措施**必须包含：
   - 数字、日期（如"2015年"、"10万人"）
   - 法律名称（如"Asylpaket I"）
   - 执行手段（如"Ausreisegewahrsam"、"Rückführung"）

5. 如果文档中**多次提及**某个政策维度，说明它很重要，必须提取。

6. 提取**所有**党派的信息（CDU/CSU、SPD、绿党、左翼党、AfD等）。

**⚠️ 重要**：如果只提取了"温和立场"而未找到"强硬立场"，请**重新检查文档**，CDU/CSU等政党通常同时包含两种维度。

**文档内容**：
{documents_text}

**请输出JSON格式的提取结果**："""

        return prompt

    def _generate_from_structured(
        self,
        question: str,
        question_type: str,
        extracted_info: List[Dict],
        processing_results: List[Dict]
    ) -> str:
        """
        阶段2：基于结构化提取的信息生成完整答案

        Args:
            question: 原始问题
            question_type: 问题类型
            extracted_info: 阶段1提取的结构化信息
            processing_results: 原始检索结果（用于生成Quellen引用）

        Returns:
            最终答案（德语，包含Quellen引用）
        """
        # 构造结构化信息的文本表示
        structured_text = ""
        for idx, item in enumerate(extracted_info, 1):
            sub_q = item.get("sub_question", "")
            extracted = item.get("extracted_info", {})

            structured_text += f"\n## 子问题 {idx}: {sub_q}\n"

            # 如果是JSON格式
            if isinstance(extracted, dict) and "raw_extraction" not in extracted:
                for party, info in extracted.items():
                    if party == "error":
                        structured_text += f"（提取失败：{info}）\n"
                        continue

                    structured_text += f"\n### {party}\n"
                    if isinstance(info, dict):
                        for key, value in info.items():
                            if isinstance(value, list):
                                structured_text += f"**{key}**:\n"
                                for v in value:
                                    structured_text += f"- {v}\n"
                            else:
                                structured_text += f"**{key}**: {value}\n"
                    else:
                        structured_text += f"{info}\n"
            else:
                # 原始文本格式
                structured_text += f"{extracted.get('raw_extraction', str(extracted))}\n"

        # 构造生成prompt
        generation_prompt = self._build_generation_prompt(
            question=question,
            question_type=question_type,
            structured_text=structured_text,
            processing_results=processing_results
        )

        # 调用LLM生成答案
        final_answer = self.llm.generate(generation_prompt)

        return final_answer

    def _build_generation_prompt(
        self,
        question: str,
        question_type: str,
        structured_text: str,
        processing_results: List[Dict]
    ) -> str:
        """
        构造基于结构化信息生成答案的prompt
        """
        # 构造Quellen材料列表（用于引用）
        quellen_list = []
        for result in processing_results:
            for chunk in result.get("chunks", [])[:15]:
                metadata = chunk.get("metadata", {})
                speaker = metadata.get("speaker", "N/A")
                party = metadata.get("group", "N/A")
                date = metadata.get("date", "N/A")
                quellen_list.append(f"- {speaker} ({party}), {date}")

        quellen_text = "\n".join(quellen_list[:30])  # 最多30个引用

        prompt = f"""Sie sind Experte für die deutsche Bundespolitik. Bitte beantworten Sie die folgende Frage VOLLSTÄNDIG und DETAILLIERT auf Deutsch.

**Frage**: {question}

**Extrahierte strukturierte Informationen**:
{structured_text}

**WICHTIGE ANFORDERUNGEN**:

1. **【核心】对立观点平衡呈现**:
   - 如果提取信息包含"温和立场"和"强硬立场"，**两者都必须在答案中呈现**
   - 避免片面化：不能只强调人道主义而忽略执行措施
   - 例如遣返政策：既要提"拒绝遣返到不安全国家"，也要提"强制遣返"、"延长拘留"
   - 体现政党立场的完整性和复杂性

2. **Vollständigkeit**:
   - Verwenden Sie ALLE extrahierten Informationen
   - Jede Partei, die in den extrahierten Informationen erscheint, MUSS in der Antwort erwähnt werden
   - Jede "具体措施" MUSS in der Antwort erscheinen
   - Sowohl "温和立场" als auch "强硬立场" MÜSSEN erwähnt werden

3. **Originalität der Formulierungen**:
   - Verwenden Sie die "关键短语" (Schlüsselphrasen) **wörtlich** aus dem Original
   - Beispiel: Wenn extrahiert wurde "Zwang durchsetzen", schreiben Sie genau das
   - Wenn extrahiert wurde "Ausreisegewahrsam verlängern", schreiben Sie genau das
   - Wenn extrahiert wurde "gemeinsame europäische Antwort", schreiben Sie genau das

4. **Konkrete Details**:
   - Zahlen, Daten, Gesetze MÜSSEN in der Antwort erscheinen
   - Beispiel: "2015", "Asylpaket I", "10.000 Flüchtlinge"
   - Beispiel: "Höchstdauer des Ausreisegewahrsams verlängern"

5. **Strukturierung nach Fragentyp**:
"""

        # 根据问题类型添加特定要求
        if "VERGLEICH" in question_type or "COMPARISON" in question_type:
            prompt += """   - Vergleichen Sie die Positionen der verschiedenen Parteien
   - Heben Sie Gemeinsamkeiten und Unterschiede hervor
"""
        elif "ÄNDERUNG" in question_type or "CHANGE" in question_type:
            prompt += """   - Zeigen Sie die Entwicklung der Positionen über die Zeit
   - Identifizieren Sie wichtige Wendepunkte
"""
        else:
            prompt += """   - Fassen Sie die wichtigsten Positionen zusammen
   - Gruppieren Sie nach Themenbereichen
"""

        prompt += f"""
5. **Quellen**:
   - Am Ende der Antwort fügen Sie eine Liste "**Quellen**" hinzu
   - Format: "- Speaker (Partei), Datum"
   - Verwenden Sie die folgenden Quellen:

{quellen_text}

**Bitte generieren Sie nun die vollständige Antwort auf Deutsch**:"""

        return prompt


# 用于测试的辅助函数
def test_incremental_v2():
    """测试增强版增量式总结节点"""
    from ...llm.client import GeminiLLMClient

    # 创建测试状态
    test_state = {
        "question": "Welche Positionen vertraten die verschiedenen Parteien zur Flüchtlingspolitik im Jahr 2015?",
        "question_type": "SUMMARY",
        "reranked_results": [
            {
                "question": "Positionen zur Flüchtlingspolitik 2015",
                "chunks": [
                    {
                        "text": "Die CDU/CSU fordert eine Einstufung der Balkanstaaten als sichere Herkunftsländer...",
                        "metadata": {
                            "speaker": "Angela Merkel",
                            "group": "CDU/CSU",
                            "date": "2015-09-15"
                        }
                    }
                ]
            }
        ]
    }

    # 创建节点并测试
    node = IncrementalSummarizeNodeV2()
    result_state = node(test_state)

    print("最终答案:", result_state.get("final_answer", ""))


if __name__ == "__main__":
    test_incremental_v2()
