"""
增强版增量式总结节点 V2
核心改进：两阶段总结 - 结构化提取 → 基于结构生成
目标：防止信息遗漏，保持原文关键短语

【性能优化】支持并行提取，大幅缩短处理时间
"""

import json
import time
import concurrent.futures
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
        # Pro模型用于最终答案生成（阶段2）
        self.llm = llm_client or GeminiLLMClient()
        # Flash模型用于结构化提取（阶段1）- 更快速、更经济
        self.llm_flash = GeminiLLMClient(model_name="gemini-2.5-flash")

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
        # 阶段1：结构化提取（使用Flash模型加速）
        logger.info("[IncrementalSummarizeV2] 阶段1: 结构化提取（Flash模型）")
        extracted_info = self._extract_structured_info(
            question=question,
            processing_results=processing_results
        )

        logger.info(f"[IncrementalSummarizeV2] 提取信息: {len(extracted_info)} 个子问题")

        # 阶段2：基于结构化信息生成答案（使用Pro模型）
        logger.info("[IncrementalSummarizeV2] 阶段2: 基于结构生成答案（Pro模型）")
        final_answer = self._generate_from_structured(
            question=question,
            question_type=question_type,
            extracted_info=extracted_info,
            processing_results=processing_results
        )

        return final_answer

    def _extract_single_subquestion(
        self,
        idx: int,
        total: int,
        sub_question: str,
        chunks: List[Dict],
        max_retries: int = 3
    ) -> Dict:
        """
        提取单个子问题的结构化信息（支持429重试）

        Args:
            idx: 子问题索引
            total: 总子问题数
            sub_question: 子问题文本
            chunks: 文档块列表
            max_retries: 遇到429错误时的最大重试次数

        Returns:
            提取结果字典
        """
        # 构造提取prompt
        extraction_prompt = self._build_extraction_prompt(
            sub_question=sub_question,
            chunks=chunks
        )

        # 带重试的调用
        last_error = None
        for attempt in range(max_retries):
            try:
                extracted_text = self.llm_flash.invoke(extraction_prompt)

                # 尝试解析JSON
                try:
                    extracted_json = json.loads(extracted_text)
                    logger.info(f"[并行提取] 子问题 {idx+1}/{total} 成功（JSON）")
                except json.JSONDecodeError:
                    extracted_json = {"raw_extraction": extracted_text}
                    logger.info(f"[并行提取] 子问题 {idx+1}/{total} 成功（文本）")

                return {
                    "idx": idx,
                    "sub_question": sub_question,
                    "extracted_info": extracted_json,
                    "num_chunks": len(chunks),
                    "success": True
                }

            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                # 检查是否是429速率限制错误
                if "429" in error_str or "rate" in error_str or "quota" in error_str:
                    wait_time = (2 ** attempt) * 2  # 指数退避: 2, 4, 8秒
                    logger.warning(f"[并行提取] 子问题 {idx+1} 遇到速率限制，等待 {wait_time}s 后重试 ({attempt+1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    # 非速率限制错误，直接失败
                    break

        # 所有重试都失败
        logger.error(f"[并行提取] 子问题 {idx+1}/{total} 提取失败: {last_error}")
        return {
            "idx": idx,
            "sub_question": sub_question,
            "extracted_info": {"error": str(last_error)},
            "num_chunks": len(chunks),
            "success": False
        }

    def _extract_structured_info(
        self,
        question: str,
        processing_results: List[Dict]
    ) -> List[Dict]:
        """
        阶段1：并行提取所有子问题的结构化信息

        【性能优化】使用ThreadPoolExecutor并行处理，大幅缩短处理时间
        - 5个子问题并行处理，从串行5分钟降到1分钟
        - 支持429错误自动重试（指数退避）

        Args:
            question: 原始问题
            processing_results: 检索结果（按子问题分组）

        Returns:
            提取的结构化信息列表
        """
        # 准备并行任务
        tasks = []
        for idx, result in enumerate(processing_results):
            sub_question = result.get("question", question)
            chunks = result.get("chunks", [])

            if not chunks:
                logger.warning(f"[并行提取] 子问题 {idx+1} 无文档，跳过")
                continue

            tasks.append((idx, sub_question, chunks))

        if not tasks:
            logger.warning("[并行提取] 无有效子问题")
            return []

        total = len(tasks)
        logger.info(f"[并行提取] 开始并行处理 {total} 个子问题")

        # 并行执行（最大并发数=子问题数，因为Google API支持高并发）
        max_workers = min(total, 10)  # 最多10个并发，避免过度占用资源
        extracted_results = []

        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_idx = {
                executor.submit(
                    self._extract_single_subquestion,
                    idx, total, sub_question, chunks
                ): idx
                for idx, sub_question, chunks in tasks
            }

            # 收集结果
            for future in concurrent.futures.as_completed(future_to_idx):
                result = future.result()
                extracted_results.append(result)

        # 按原始顺序排序
        extracted_results.sort(key=lambda x: x["idx"])

        # 转换为标准格式
        extracted_list = [
            {
                "sub_question": r["sub_question"],
                "extracted_info": r["extracted_info"],
                "num_chunks": r["num_chunks"]
            }
            for r in extracted_results
        ]

        elapsed = time.time() - start_time
        success_count = sum(1 for r in extracted_results if r.get("success", False))
        logger.info(f"[并行提取] 完成! 耗时: {elapsed:.1f}秒, 成功: {success_count}/{total}")

        return extracted_list

    def _aggregate_chunks_by_speaker(self, chunks: List[Dict]) -> List[Dict]:
        """
        【Speaker Chunk聚合】将同一发言人的多个chunks合并

        目的：确保LLM在总结时能看到同一发言人的完整上下文，
        避免因chunks分散导致信息遗漏

        Args:
            chunks: 原始chunks列表

        Returns:
            聚合后的chunks列表，同一speaker的内容合并为一个chunk
        """
        from collections import defaultdict

        # 按speaker分组
        speaker_chunks = defaultdict(list)
        speaker_metadata = {}

        for chunk in chunks:
            metadata = chunk.get("metadata", {})
            speaker = metadata.get("speaker", "Unknown")
            text = chunk.get("text", "")

            if text.strip():
                speaker_chunks[speaker].append(text)
                # 保留第一个chunk的metadata
                if speaker not in speaker_metadata:
                    speaker_metadata[speaker] = metadata

        # 合并同一speaker的chunks
        aggregated = []
        for speaker, texts in speaker_chunks.items():
            # 合并所有文本，用分隔符连接
            merged_text = "\n\n---\n\n".join(texts)

            aggregated.append({
                "text": merged_text,
                "metadata": speaker_metadata[speaker],
                "chunk_count": len(texts)  # 记录合并了多少个chunk
            })

        # 按chunk数量排序，优先显示内容最多的speaker
        aggregated.sort(key=lambda x: x.get("chunk_count", 0), reverse=True)

        logger.info(f"[SpeakerAggregation] 聚合前: {len(chunks)} chunks, 聚合后: {len(aggregated)} speakers")
        for agg in aggregated[:5]:
            speaker = agg['metadata'].get('speaker', 'Unknown')
            count = agg.get('chunk_count', 1)
            logger.info(f"  - {speaker}: {count} chunks 合并")

        return aggregated

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
        # 【新增】Speaker Chunk聚合 - 将同一发言人的chunks合并
        aggregated_chunks = self._aggregate_chunks_by_speaker(chunks)

        # 构造文档文本（使用聚合后的chunks）
        documents_text = ""
        for i, chunk in enumerate(aggregated_chunks[:15], 1):  # 聚合后通常speaker数量更少
            text = chunk.get("text", "")
            metadata = chunk.get("metadata", {})
            speaker = metadata.get("speaker", "N/A")
            party = metadata.get("group_chinese", metadata.get("group", "N/A"))
            date = metadata.get("date", "N/A")
            chunk_count = chunk.get("chunk_count", 1)

            # 标注这是聚合内容
            agg_note = f" [包含{chunk_count}段发言]" if chunk_count > 1 else ""
            documents_text += f"\n### 发言人 {i}: {speaker} ({party}, {date}){agg_note}\n{text}\n"

        prompt = f"""您是德国议会政治分析专家。请从以下文档中提取关键信息，直接回答问题。

**问题**: {sub_question}

**【核心原则】完整提取所有相关信息**：
1. **直接回答问题所问的内容**
2. **提取所有相关细节**，不要遗漏

**提取要求**：

1. **必须提取的内容类型**：
   - 核心立场/观点：发言人对问题的明确态度
   - 支持理由：为什么持这种立场
   - 批评/反对意见：对其他方案或政策的批评
   - **具体问题/例子**：发言人提到的具体事例、案例、现象（如虐待Mißhandlung、毒品滥用Drogenmißbrauch、自杀Selbsttötungsversuch等）
   - **根本原因分析**：问题产生的根本原因（如过度负担Überlastung、官僚主义Bürokratie、晋升停滞Beförderungsstau等）
   - **解决方案建议**：提出的解决方案和改进措施

2. **必须保留的具体细节**（遗漏任何一项都会导致答案不完整）：
   - **数字**: 百分比、金额、人数、年份 (如 "6%", "4.1亿马克", "10万人", "1975年")
   - **日期**: 具体日期、生效时间 (如 "1月1日", "ab 1975")
   - **法律/政策名称**: (如 "Umsatzsteuergesetz", "Art. 16 GG", "Asylpaket I")
   - **专有名词**: 人名、机构名、项目名
   - **德语原文关键短语**: 保留重要术语的德语原文

3. **按以下结构提取**：
{{
  "发言人/党派": {{
    "核心立场": "对问题的明确回答",
    "支持理由": ["理由1", "理由2"],
    "批评意见": ["批评1", "批评2"],
    "具体问题例子": ["具体事例1（保留德语术语）", "具体事例2"],
    "根本原因": ["原因1", "原因2"],
    "解决方案": ["方案1", "方案2"],
    "关键数据": ["6%", "1975年1月1日", "4.1亿马克"],
    "德语关键词": ["Originalzitat 1", "Originalzitat 2"]
  }}
}}

4. **检查清单**（确保不遗漏）：
   - [ ] 问题的核心答案是否已提取？
   - [ ] 所有数字/日期是否已保留？
   - [ ] 所有法律/政策名称是否已保留？
   - [ ] **所有具体问题/例子是否已提取？**（如虐待、毒品滥用、自杀等）
   - [ ] **根本原因分析是否已提取？**（如官僚主义、晋升停滞等）
   - [ ] 批评/反对意见是否已提取？
   - [ ] 德语关键术语是否已保留？

**文档内容**：
{documents_text}

**请直接输出提取结果**："""

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
        final_answer = self.llm.invoke(generation_prompt)

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
        # 构造Quellen材料列表（用于引用）- 使用集合去重
        quellen_set = set()
        quellen_list = []
        for result in processing_results:
            for chunk in result.get("chunks", [])[:15]:
                metadata = chunk.get("metadata", {})
                speaker = metadata.get("speaker", "N/A")
                party = metadata.get("group", "N/A")
                date = metadata.get("date", "N/A")
                quellen_entry = f"- {speaker} ({party}), {date}"
                # 只添加未出现过的引用
                if quellen_entry not in quellen_set:
                    quellen_set.add(quellen_entry)
                    quellen_list.append(quellen_entry)

        quellen_text = "\n".join(quellen_list[:30])  # 最多30个去重后的引用

        prompt = f"""Sie sind Experte für die deutsche Bundespolitik. Bitte beantworten Sie die folgende Frage VOLLSTÄNDIG und DETAILLIERT auf Deutsch.

**Frage**: {question}

**Extrahierte strukturierte Informationen**:
{structured_text}

**WICHTIGE ANFORDERUNGEN**:

1. **【P1-核心】聚焦问题核心，完整呈现相关信息**:
   - **必须直接回答问题所问的内容**
   - 如果问题问"什么负面后果"，答案必须明确说明具体后果
   - 如果问题问"什么立场"，答案必须明确说明具体立场
   - **必须包含所有具体例子**：如提取信息中有"虐待"、"毒品滥用"、"自杀未遂"等具体问题，必须在答案中呈现
   - **必须包含根本原因分析**：如提取信息中有"过度负担"、"官僚主义"、"晋升停滞"等原因，必须在答案中呈现
   - **必须包含解决方案建议**：如提取信息中有具体建议，必须在答案中呈现
   - **禁止**：用其他党派或其他年份的信息替代问题所问的核心内容

2. **【P0-关键】具体细节必须保留**:
   - **所有数字必须保留**: 百分比(6%, 4%)、金额(4.1亿马克)、人数(10,000人)
   - **所有日期必须保留**: 具体年份(1975年)、月日(1月1日)、时间段
   - **所有法律/政策名称必须保留**: Asylpaket I, Umsatzsteuergesetz, Art. 16 GG
   - **所有专有名词必须保留**: 人名、机构名、地名
   - 这些细节是答案完整性的关键，遗漏任何一个都会导致答案不完整

3. **对立观点平衡呈现**:
   - 如果提取信息包含"温和立场"和"强硬立场"，两者都必须呈现
   - 体现政党立场的完整性和复杂性

4. **Vollständigkeit (完整性要求 - 极其重要)**:
   - **Verwenden Sie ALLE extrahierten Informationen** - 所有提取的信息必须使用
   - Jede Partei, die in den extrahierten Informationen erscheint, MUSS erwähnt werden
   - **Alle konkreten Beispiele MÜSSEN erscheinen** (z.B. Mißhandlungen, Drogenmißbrauch, Selbsttötungsversuche)
   - **Alle Ursachenanalysen MÜSSEN erscheinen** (z.B. Überlastung, Bürokratie, Beförderungsstau)
   - **Alle Lösungsvorschläge MÜSSEN erscheinen**
   - 遗漏任何已提取的信息都是不可接受的

5. **Originalität der Formulierungen**:
   - Verwenden Sie Schlüsselphrasen **wörtlich** aus dem Original
   - Beispiel: "Zwang durchsetzen", "Ausreisegewahrsam verlängern"

6. **Strukturierung nach Fragentyp**:
"""

        # 根据问题类型添加特定要求
        question_type = question_type or ""  # 处理None情况
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
7. **Quellen**:
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
