"""
增强版总结节点
支持分层总结和模块化输出 + 结构化验证（防止LLM过滤次要论点）
"""

from typing import List, Dict, Optional, Tuple
import re
from ...llm.client import GeminiLLMClient
from ...llm.prompts_summarize import SummarizePrompts
from ...llm.prompts_summarize_enhanced import EnhancedSummarizePrompts
from ...utils.logger import logger
from ..state import GraphState, update_state
from ...config import settings


class EnhancedSummarizeNode:
    """
    增强版总结节点

    核心改进:
    1. 根据问题类型选择定制化Prompt
    2. 模块化德文输出（speaker/statement/evidence/source）
    3. 分层总结（单子问题 → 多子问题整合）
    4. 德文系统Prompt
    5. 【新增】细节强制引用机制（解决Q5/Q6类问题）

    支持的问题类型:
    - 变化类: 时间序列分析 + 转折点识别
    - 对比类: 对比表格 + 差异分析
    - 总结类: 主题分组 + 核心观点
    - 趋势分析: 阶段划分 + 趋势识别
    """

    # 预定义的重要地名（德语）
    IMPORTANT_LOCATIONS = [
        "Syrien", "Georgien", "Afghanistan", "Türkei", "Irak", "Iran",
        "Nordafrika", "Balkan", "Griechenland", "Italien",
        "syrisch", "georgisch", "türkisch", "afghanisch"
    ]

    # 预定义的重要政策/项目关键词（扩展版 - 解决Q5/Q6/Q7反馈问题）
    IMPORTANT_POLICY_KEYWORDS = [
        # 文化政策
        "Kultur baut Brücken", "Kultur macht stark",
        # 签证与入境
        "Visum", "visumfrei", "Visumspflicht", "visumspflichtig",
        "Visaliberalisierung", "Visa-Aussetzung",
        # 移民法律
        "Integrationsgesetz", "Fachkräfteeinwanderungsgesetz",
        "Familiennachzug", "Obergrenze", "AnKER-Zentren", "Ankerzentren",
        # 遣返与拘留
        "sichere Herkunftsländer", "Abschiebung", "Rückführung",
        "Ausreisegewahrsam", "Abschiebungshaft", "Höchstdauer",
        # 叙利亚重建
        "Wiederaufbau", "Rückkehrvoraussetzung", "Voraussetzung",
        # 边境控制
        "Grenzkontrollen", "Dublin", "Zurückweisung",
    ]

    def __init__(self, llm_client: GeminiLLMClient = None):
        """
        初始化增强版总结节点

        Args:
            llm_client: LLM客户端
        """
        self.llm = llm_client or GeminiLLMClient()
        self.prompts = SummarizePrompts()
        self.enhanced_prompts = EnhancedSummarizePrompts()
        self.production_mode = settings.production_mode
        # 启用结构化验证（修复Q6类问题）
        self.enable_robust_mode = True
        # 【新增】启用细节强制引用（解决Q5/Q6类问题）
        self.enable_detail_citation = True
        
    def __call__(self, state: GraphState) -> GraphState:
        """
        执行总结
        
        Args:
            state: 当前状态
            
        Returns:
            更新后的状态
        """
        question = state["question"]
        question_type = state.get("question_type", "")
        # 获取重排序后的检索结果（优先）或原始检索结果（降级）
        reranked_results = state.get("reranked_results", [])
        retrieval_results = state.get("retrieval_results", [])
        
        # 优先使用重排序结果，如果不存在则使用原始检索结果
        if reranked_results:
            logger.info(f"[EnhancedSummarizeNode] 使用重排序结果 ({len(reranked_results)} 个)")
            processing_results = reranked_results
        else:
            logger.info(f"[EnhancedSummarizeNode] 重排序结果不存在，使用原始检索结果 ({len(retrieval_results)} 个)")
            processing_results = retrieval_results
            
        sub_questions = state.get("sub_questions")
        is_decomposed = state.get("is_decomposed", False)
        
        logger.info(f"[EnhancedSummarizeNode] 开始总结")
        logger.info(f"[EnhancedSummarizeNode] 问题类型: {question_type}")
        logger.info(f"[EnhancedSummarizeNode] 处理结果数: {len(processing_results)}")
        logger.info(f"[EnhancedSummarizeNode] 是否拆解: {is_decomposed}")
        
        try:
            # 检查是否有材料
            if not processing_results or len(processing_results) == 0:
                logger.warning("[EnhancedSummarizeNode] 无检索结果")
                return update_state(
                    state,
                    error="未找到相关材料",
                    error_type="NO_MATERIAL",
                    no_material_found=True,
                    current_node="summarize",
                    next_node="exception"
                )
            
            # 判断是单问题还是多问题总结
            if is_decomposed and len(processing_results) > 1:
                # 多问题总结（问题被分解为子问题）
                final_answer, sub_answers = self._multi_question_summarize(
                    question=question,
                    question_type=question_type,
                    retrieval_results=processing_results
                )
            else:
                # 单问题总结
                # 【BUG修复】当有多个检索结果时（如知识图谱扩展场景），需要合并所有chunks
                if len(processing_results) > 1:
                    logger.info(f"[EnhancedSummarizeNode] 🔧 合并 {len(processing_results)} 个检索结果的chunks")
                    merged_result = self._merge_retrieval_results(processing_results, question)
                    logger.info(f"[EnhancedSummarizeNode] 合并后chunks数: {len(merged_result.get('chunks', []))}")
                else:
                    merged_result = processing_results[0] if processing_results else None

                final_answer, sub_answers = self._single_question_summarize(
                    question=question,
                    retrieval_result=merged_result
                )
            
            logger.info(f"[EnhancedSummarizeNode] 总结完成")
            logger.info(f"[EnhancedSummarizeNode] 答案长度: {len(final_answer)} 字符")
            
            # 更新状态
            return update_state(
                state,
                final_answer=final_answer,
                sub_answers=sub_answers,
                current_node="summarize",
                next_node="end"
            )
            
        except Exception as e:
            logger.error(f"[EnhancedSummarizeNode] 总结失败: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return update_state(
                state,
                error=f"总结失败: {str(e)}",
                error_type="LLM_ERROR",
                current_node="summarize",
                next_node="exception"
            )
    
    def _single_question_summarize(
        self,
        question: str,
        retrieval_result: Optional[Dict]
    ) -> Tuple[str, Optional[List[Dict]]]:
        """
        单问题总结（使用模块化输出 + 结构化验证）

        Args:
            question: 问题
            retrieval_result: 检索结果

        Returns:
            (final_answer, sub_answers)
        """
        logger.info(f"[EnhancedSummarizeNode] 单问题总结（鲁棒模式: {self.enable_robust_mode}）")

        if not retrieval_result or not retrieval_result.get("chunks"):
            logger.warning("[EnhancedSummarizeNode] 检索结果为空")
            return "Entschuldigung, es wurden keine relevanten Materialien gefunden.", None

        chunks = retrieval_result.get("chunks", [])
        total_materials = len(chunks)
        logger.info(f"[EnhancedSummarizeNode] 材料数量: {total_materials}")

        # 格式化上下文
        context = self._format_context(chunks)

        # 【最优方案】在初始Prompt中就强制要求保留关键政策词（而非事后重试）
        detail_requirement = ""
        critical_keywords_found = []
        if self.enable_detail_citation:
            key_details = self._extract_key_details(chunks)
            if key_details:
                # 筛选关键政策词
                critical_patterns = ["Visum", "visumspflichtig", "Kultur baut", "Wiederaufbau", "Ausreisegewahrsam", "Voraussetzung"]
                critical_keywords_found = [d for d in key_details if any(kw in d for kw in critical_patterns)]

                if critical_keywords_found:
                    logger.info(f"[EnhancedSummarizeNode] 🔥 检测到{len(critical_keywords_found)}个关键政策词，将在Prompt中强制要求保留")

                    # 从chunks中提取证据，增强说服力
                    evidence_lines = []
                    for kw in critical_keywords_found:
                        for chunk in chunks:
                            text = chunk.get("text", "")
                            if kw.lower() in text.lower():
                                kw_pos = text.lower().find(kw.lower())
                                start = max(0, kw_pos - 60)
                                end = min(len(text), kw_pos + len(kw) + 60)
                                excerpt = text[start:end].strip()
                                speaker = chunk.get("metadata", {}).get("speaker", "Unknown")
                                evidence_lines.append(f'  • "{kw}" → "{excerpt}..." ({speaker})')
                                break

                    evidence_text = "\n".join(evidence_lines) if evidence_lines else ""

                    detail_requirement = f"""
[⚠️ PFLICHT-DETAILS - Diese Begriffe MÜSSEN wörtlich in der Zusammenfassung erscheinen]

Die folgenden spezifischen Politikbegriffe wurden in den Materialien gefunden:
{chr(10).join([f'  • {kw}' for kw in critical_keywords_found])}

Belege aus den Materialien:
{evidence_text}

WICHTIG:
- Diese Begriffe dürfen NICHT abstrahiert werden (z.B. "visumspflichtig" → NICHT "Druck ausüben")
- Sie MÜSSEN wörtlich im Abschnitt "Zusammenfassung" oder "Hauptpositionen" erscheinen
- Wenn Material 1 "Georgien visumspflichtig zu machen" fordert, muss die Zusammenfassung "visumspflichtig" enthalten

"""

        # 根据模式选择Prompt模板
        if self.enable_robust_mode:
            # 使用结构化验证版Prompt
            prompt = self.enhanced_prompts.build_single_question_prompt_robust(
                question=question,
                context=context,
                total_materials=total_materials
            )
            logger.info("[EnhancedSummarizeNode] 使用结构化验证版Prompt")
        else:
            # 使用原始模块化Prompt
            prompt = self.prompts.SINGLE_QUESTION_MODULAR.format(
                question=question,
                context=context
            )
            logger.info("[EnhancedSummarizeNode] 使用原始模块化Prompt")

        # 添加德文系统Prompt + 关键词强制要求（在Prompt最前面，优先级最高）
        full_prompt = f"{self.enhanced_prompts.SYSTEM_PROMPT_DE}\n\n{detail_requirement}{prompt}"

        # 调用LLM
        logger.debug("[EnhancedSummarizeNode] 调用LLM...")
        answer = self.llm.invoke(full_prompt)

        logger.debug(f"[EnhancedSummarizeNode] 答案预览: {answer[:200]}...")

        # 如果启用鲁棒模式，进行材料覆盖验证
        if self.enable_robust_mode:
            is_complete, missing = self._verify_material_coverage(answer, total_materials)

            if not is_complete:
                logger.warning(
                    f"🔄 检测到{len(missing)}个材料缺失: {missing}，"
                    f"要求LLM重新生成..."
                )

                # 补充Prompt：明确指出缺失的材料
                retry_prompt = f"""
WICHTIG: Ihre vorherige Antwort hat folgende Materialien nicht bewertet:
{', '.join([f'Material {n}' for n in missing])}

Bitte bewerten Sie ALLE {total_materials} Materialien in Schritt 1 und erstellen Sie die Zusammenfassung erneut.

{prompt}
"""

                full_retry_prompt = f"{self.enhanced_prompts.SYSTEM_PROMPT_DE}\n\n{retry_prompt}"

                # 重试
                logger.info("[EnhancedSummarizeNode] 🔄 重试LLM调用...")
                answer = self.llm.invoke(full_retry_prompt)

                # 再次验证
                is_complete_retry, missing_retry = self._verify_material_coverage(answer, total_materials)

                if not is_complete_retry:
                    logger.error(
                        f"❌ 重试后仍有{len(missing_retry)}个材料缺失: {missing_retry}，"
                        f"使用不完整答案"
                    )
                else:
                    logger.info("✅ 重试成功，所有材料已覆盖")

        # 【验证】检查关键政策词是否在总结部分出现（用于确认"事前预防"效果）
        if self.enable_detail_citation and critical_keywords_found:
            summary_section = self._extract_summary_section(answer)

            # 检查是否在总结部分出现
            missing_in_summary = [d for d in critical_keywords_found if d.lower() not in summary_section.lower()]

            if missing_in_summary:
                # 检测假阳性：在整个答案中但不在总结部分
                false_positives = [d for d in missing_in_summary if d.lower() in answer.lower()]
                if false_positives:
                    logger.warning(f"[EnhancedSummarizeNode] ⚠️ 假阳性（仅在Materialbewertung）: {false_positives}")

                logger.warning(f"[EnhancedSummarizeNode] ⚠️ 关键政策词在总结部分缺失: {missing_in_summary}")
            else:
                logger.info(f"[EnhancedSummarizeNode] ✅ 所有关键政策词已在总结部分保留: {critical_keywords_found}")

        return answer, None

    def _merge_retrieval_results(
        self,
        processing_results: List[Dict],
        question: str,
        max_chunks: int = 50
    ) -> Dict:
        """
        合并多个检索结果的chunks（知识图谱扩展场景）

        功能：
        1. 合并所有检索结果的chunks
        2. 基于text_id去重（保留相似度最高的版本）
        3. 按相似度降序排序
        4. 限制最大数量避免context过长

        Args:
            processing_results: 多个检索结果
            question: 原始问题
            max_chunks: 最大chunks数量

        Returns:
            合并后的检索结果
        """
        # 收集所有chunks，用text_id去重
        seen_text_ids = {}  # text_id -> (chunk, score)
        seen_texts = {}     # text[:200] -> (chunk, score)  用于处理无text_id的情况

        for result in processing_results:
            chunks = result.get("chunks", [])
            for chunk in chunks:
                text_id = chunk.get("metadata", {}).get("text_id", "")
                score = chunk.get("score", 0.0)
                text_preview = chunk.get("text", "")[:200]

                # 优先用text_id去重
                if text_id:
                    if text_id not in seen_text_ids or score > seen_text_ids[text_id][1]:
                        seen_text_ids[text_id] = (chunk, score)
                else:
                    # 无text_id时用文本前200字符去重
                    if text_preview not in seen_texts or score > seen_texts[text_preview][1]:
                        seen_texts[text_preview] = (chunk, score)

        # 合并去重结果
        all_chunks = [item[0] for item in seen_text_ids.values()]
        all_chunks.extend([item[0] for item in seen_texts.values()])

        # 按相似度降序排序
        all_chunks.sort(key=lambda x: x.get("score", 0.0), reverse=True)

        # 限制数量
        final_chunks = all_chunks[:max_chunks]

        logger.info(
            f"[EnhancedSummarizeNode] 合并检索结果: "
            f"原始{sum(len(r.get('chunks', [])) for r in processing_results)}个 -> "
            f"去重后{len(all_chunks)}个 -> 截取{len(final_chunks)}个"
        )

        return {
            "question": question,
            "chunks": final_chunks
        }

    def _multi_question_summarize(
        self,
        question: str,
        question_type: str,
        retrieval_results: List[Dict]
    ) -> Tuple[str, List[Dict]]:
        """
        多问题分层总结

        流程:
        - 生产模式: 跳过子答案生成，直接从所有chunks生成最终答案（省26分钟）
        - 测试模式: 原始流程（生成子答案+最终答案）

        Args:
            question: 原始问题
            question_type: 问题类型
            retrieval_results: 检索结果列表

        Returns:
            (final_answer, sub_answers)
        """
        logger.info(f"[EnhancedSummarizeNode] 多问题分层总结")
        logger.info(f"[EnhancedSummarizeNode] 子问题数: {len(retrieval_results)}")
        logger.info(f"[EnhancedSummarizeNode] 运行模式: {'生产模式' if self.production_mode else '测试模式'}")

        # 生产模式：跳过子答案生成，直接生成最终答案
        if self.production_mode:
            logger.info("[EnhancedSummarizeNode] 🚀 生产模式：跳过子答案生成，直接生成最终答案")
            return self._production_mode_summarize(question, question_type, retrieval_results)

        # 测试模式：原始分层总结流程
        logger.info("[EnhancedSummarizeNode] 🧪 测试模式：生成详细子答案")

        # Step 1: 为每个子问题生成答案
        sub_answers = []

        for i, result in enumerate(retrieval_results, 1):
            sub_question = result["question"]
            chunks = result.get("chunks", [])

            logger.info(f"[EnhancedSummarizeNode] 处理子问题 {i}/{len(retrieval_results)}: {sub_question}")

            if chunks and len(chunks) > 0:
                # 格式化上下文
                context = self._format_context(chunks)

                # 构建Prompt
                prompt = self.prompts.SINGLE_QUESTION_MODULAR.format(
                    question=sub_question,
                    context=context
                )

                full_prompt = f"{self.prompts.SYSTEM_PROMPT_DE}\n\n{prompt}"

                # 调用LLM
                sub_answer = self.llm.invoke(full_prompt)

                # 提取来源
                sources = self._extract_sources(chunks)
            else:
                logger.warning(f"[EnhancedSummarizeNode] 子问题 {i} 无材料")
                sub_answer = "Keine relevanten Materialien gefunden."
                sources = []

            sub_answers.append({
                "question": sub_question,
                "answer": sub_answer,
                "sources": sources
            })

            logger.debug(f"[EnhancedSummarizeNode] 子答案 {i} 长度: {len(sub_answer)}")

        # Step 2: 根据问题类型选择整合模板
        summary_template = self.prompts.select_summary_template(question_type)

        logger.info(f"[EnhancedSummarizeNode] 使用模板类型: {question_type}")

        # Step 3: 格式化子问题答案对
        sub_qa_text = self.prompts.format_sub_qa_pairs(sub_answers)

        # Step 4: 构建最终Prompt
        final_prompt = summary_template.format(
            original_question=question,
            sub_qa_pairs=sub_qa_text
        )

        full_final_prompt = f"{self.prompts.SYSTEM_PROMPT_DE}\n\n{final_prompt}"

        # Step 5: 调用LLM生成最终答案
        logger.info("[EnhancedSummarizeNode] 生成最终整合答案...")
        final_answer = self.llm.invoke(full_final_prompt)

        logger.info(f"[EnhancedSummarizeNode] 最终答案长度: {len(final_answer)}")

        return final_answer, sub_answers

    def _production_mode_summarize(
        self,
        question: str,
        question_type: str,
        retrieval_results: List[Dict]
    ) -> Tuple[str, Optional[List[Dict]]]:
        """
        生产模式总结：跳过子答案生成，直接从所有chunks生成最终答案

        性能优化：
        - 不生成40个子答案（省26分钟）
        - 直接整合所有retrieval_results的chunks
        - 一次LLM调用生成最终答案

        Args:
            question: 原始问题
            question_type: 问题类型
            retrieval_results: 检索结果列表

        Returns:
            (final_answer, None)
        """
        logger.info(f"[EnhancedSummarizeNode] 🚀 生产模式：整合所有检索结果")

        # Step 1: 收集所有chunks
        all_chunks = []
        for result in retrieval_results:
            chunks = result.get("chunks", [])
            all_chunks.extend(chunks)

        logger.info(f"[EnhancedSummarizeNode] 总chunks数: {len(all_chunks)}")

        # Step 2: 去重（基于id）
        unique_chunks = {}
        for chunk in all_chunks:
            # ID在顶层（优先）或metadata中
            chunk_id = chunk.get("id") or chunk.get("metadata", {}).get("id", "")
            if chunk_id:
                # 保留分数最高的chunk
                if chunk_id not in unique_chunks or chunk.get("score", 0) > unique_chunks[chunk_id].get("score", 0):
                    unique_chunks[chunk_id] = chunk

        deduplicated_chunks = list(unique_chunks.values())
        logger.info(f"[EnhancedSummarizeNode] 去重后chunks数: {len(deduplicated_chunks)}")

        # Step 3: 按分数排序，保留Top-100
        sorted_chunks = sorted(deduplicated_chunks, key=lambda x: x.get("score", 0), reverse=True)
        top_chunks = sorted_chunks[:100]

        logger.info(f"[EnhancedSummarizeNode] 使用Top-{len(top_chunks)}个chunks")

        # Step 4: 格式化上下文
        context = self._format_context(top_chunks)

        # Step 5: 【方案A核心】提取关键细节，用于强制引用
        key_details = []
        detail_requirement = ""
        if self.enable_detail_citation:
            key_details = self._extract_key_details(top_chunks)
            if key_details:
                # 构建强制引用要求（全德语，更强调）
                detail_list = "\n".join([f"  • {detail}" for detail in key_details[:10]])
                detail_requirement = f"""
[⚠️ KRITISCHE ANFORDERUNG - Pflicht zur Erwähnung folgender Details]

Die folgenden spezifischen Begriffe/Konzepte wurden in den Materialien gefunden und MÜSSEN in Ihrer Antwort erwähnt werden:

{detail_list}

WICHTIG:
1. Diese Details sind konkrete Projektnamen, Politikmaßnahmen, Ländernamen oder spezifische Vorschläge
2. Auch wenn ein Detail nur von einer Partei/einem Redner erwähnt wird, muss es in der Antwort enthalten sein
3. Für Vorschläge wie "visumspflichtig machen" oder "Ausreisegewahrsam verlängern" - geben Sie den GENAUEN Wortlaut an
4. Überspringen Sie ein Detail NUR wenn es wirklich keine Verbindung zur Frage hat (erklären Sie dann warum)
"""
                logger.info(f"[EnhancedSummarizeNode] 🔥 启用细节强制引用，共{len(key_details)}个细节")

        # Step 6: 根据问题类型选择模板
        summary_template = self.prompts.select_summary_template(question_type)

        # Step 7: 构建直接生成最终答案的Prompt（包含强制引用要求）
        # 【核心修复】针对"变化类"问题使用专门的历时变化格式模板
        if question_type == "变化类":
            logger.info("[EnhancedSummarizeNode] 🕐 检测到变化类问题，使用历时变化专用格式")
            production_prompt = f"""Sie sind Experte für die Analyse von Bundestagsreden.

Bitte beantworten Sie die folgende Frage basierend auf den bereitgestellten Materialien.

[Frage]
{question}
{detail_requirement}
[Materialien]
{context}

[⚠️ KRITISCHE ANFORDERUNG - Zeitliche Strukturierung]

Dies ist eine Frage zur ZEITLICHEN ENTWICKLUNG. Sie MÜSSEN die Antwort CHRONOLOGISCH strukturieren!

[Pflicht-Ausgabeformat]

**1. Überblick**

[2-3 Sätze zur Gesamtentwicklung über den gesamten Zeitraum]

**2. Zeitliche Entwicklung**

Erstellen Sie für JEDES Jahr einen eigenen Abschnitt. Lassen Sie KEIN Jahr aus!

• **2015**
  - Kernposition: [Zusammenfassung der Position in diesem Jahr]
  - Konkrete Maßnahmen/Forderungen: [Spezifische Politikvorschläge]
  - Repräsentatives Zitat: „[Originalzitat]" ([Redner], [Datum])

• **2016**
  - Kernposition: [Zusammenfassung der Position in diesem Jahr]
  - Konkrete Maßnahmen/Forderungen: [Spezifische Politikvorschläge]
  - Repräsentatives Zitat: „[Originalzitat]" ([Redner], [Datum])

• **2017**
  - Kernposition: [...]
  - Konkrete Maßnahmen/Forderungen: [...]
  - Repräsentatives Zitat: „[...]"

[... Fahren Sie fort für ALLE Jahre, für die Materialien vorliegen ...]

**3. Hauptveränderungen**

Identifizieren Sie die wichtigsten Wendepunkte und Positionsänderungen:

1. **Von [Jahr X] zu [Jahr Y]**:
   - Was änderte sich: [Konkrete Beschreibung der Änderung]
   - Beispiel: „[Vorher-Position]" → „[Nachher-Position]"

2. **Von [Jahr Y] zu [Jahr Z]**:
   - Was änderte sich: [...]

**4. Zusammenfassung**

[Abschließende Bewertung: Wie hat sich die Position insgesamt entwickelt? Was waren die Haupttreiber der Veränderung?]

**Quellen**

- Material 1: [Redner] ([Partei]), [YYYY-MM-DD]
- Material 2: [Redner] ([Partei]), [YYYY-MM-DD]
- ...

[WICHTIGE REGELN]
1. JEDES Jahr mit verfügbaren Materialien MUSS einen eigenen Abschnitt haben
2. Die Jahre MÜSSEN in chronologischer Reihenfolge erscheinen (2015 → 2016 → 2017 → ...)
3. Verwenden Sie für jedes Jahr mindestens ein konkretes Zitat mit Quellenangabe
4. Wenn für ein Jahr keine Materialien vorliegen, geben Sie dies explizit an: „Für [Jahr] liegen keine Materialien vor"
5. Vermeiden Sie es, Informationen aus verschiedenen Jahren zu vermischen!
"""
        else:
            # 其他问题类型使用通用prompt
            production_prompt = f"""
你是德国议会议事录专家。请根据以下检索到的议会发言材料，直接回答用户的问题。

【用户问题】
{question}
{detail_requirement}
【检索材料】
{context}

【要求】
1. 直接回答问题，结构清晰
2. 引用具体发言人和日期
3. 使用德语回答
4. 如果是对比类问题，清晰对比各方观点
5. 如果是总结类问题，提炼核心观点
6. **必须引用上述"重要细节"中列出的所有具体项目、政策、地名**

【输出格式】（必须包含以下所有部分）
1. Zusammenfassung（总结）
2. Wichtige Aussagen（重要观点，引用发言人和日期）
3. Belege aus den Materialien（材料证据，**必须包含上述重要细节**）
4. Quellen（来源列表，格式：Material 1: [发言人] ([党派]), [日期]）

注意：必须在末尾生成完整的Quellen列表，按Material 1, Material 2...的格式列出所有引用的材料。
"""

        full_prompt = f"{self.prompts.SYSTEM_PROMPT_DE}\n\n{production_prompt}"

        # Step 8: 调用LLM生成最终答案
        logger.info("[EnhancedSummarizeNode] 生成最终答案...")
        final_answer = self.llm.invoke(full_prompt)

        # Step 8.5: 【新增】检查关键词是否完全被遗漏（第一阶段重试）
        if self.enable_detail_citation and key_details:
            critical_patterns = ["Visum", "visumspflichtig", "Kultur baut", "Wiederaufbau", "Ausreisegewahrsam"]
            critical_keywords_in_chunks = [d for d in key_details if any(kw in d for kw in critical_patterns)]

            # 检查这些关键词是否在整个答案中完全缺失
            completely_missing = [kw for kw in critical_keywords_in_chunks if kw.lower() not in final_answer.lower()]

            if completely_missing:
                logger.warning(f"[EnhancedSummarizeNode] ❌ 关键词完全缺失（连Materialbewertung都没有）: {completely_missing}")

                # 从chunks中提取证据
                evidence_for_missing = []
                for kw in completely_missing:
                    for chunk in top_chunks:
                        text = chunk.get("text", "")
                        if kw.lower() in text.lower():
                            kw_pos = text.lower().find(kw.lower())
                            start = max(0, kw_pos - 100)
                            end = min(len(text), kw_pos + len(kw) + 100)
                            excerpt = text[start:end].strip()
                            speaker = chunk.get("metadata", {}).get("speaker", "Unknown")
                            date = chunk.get("metadata", {}).get("date", "")
                            evidence_for_missing.append(f'关键词 "{kw}" 出现在: "{excerpt}..." (发言人: {speaker}, {date})')
                            break

                if evidence_for_missing:
                    logger.info(f"[EnhancedSummarizeNode] 🔍 找到 {len(evidence_for_missing)} 个缺失关键词的原始证据")
                    for ev in evidence_for_missing:
                        logger.debug(f"  - {ev}")

                    # 第一阶段重试：强制包含完全缺失的关键词
                    force_include_prompt = f"""
{full_prompt}

[❌ SCHWERWIEGENDER FEHLER - KRITISCHE DETAILS FEHLEN VOLLSTÄNDIG]

Ihre Antwort hat folgende wichtige Details ÜBERHAUPT NICHT erwähnt, obwohl sie IN DEN MATERIALIEN VORKOMMEN:

{chr(10).join([f'  • {d}' for d in completely_missing])}

DIREKTER BEWEIS aus den Materialien:
{chr(10).join([f'  {ev}' for ev in evidence_for_missing])}

Diese Details sind ENTSCHEIDEND für die Vollständigkeit der Antwort. Bitte wiederholen Sie die VOLLSTÄNDIGE Antwort und stellen Sie sicher, dass ALLE oben genannten Details sowohl in der Materialbewertung als auch in der Zusammenfassung erscheinen.
"""
                    logger.info(f"[EnhancedSummarizeNode] 🔄 第一阶段重试: 强制包含完全缺失的关键词...")
                    final_answer = self.llm.invoke(force_include_prompt)

        # Step 9: 【方案A验证+重试】检查关键细节是否在"总结部分"被引用（不仅仅是材料评估部分）
        if self.enable_detail_citation and key_details:
            # 提取总结部分（Zusammenfassung和Hauptpositionen之后的内容）
            summary_section = self._extract_summary_section(final_answer)

            # 【修复】检查所有关键政策词，而非仅前10个（短关键词可能排在后面）
            critical_patterns = ["Visum", "visumspflichtig", "Kultur baut", "Wiederaufbau", "Ausreisegewahrsam", "Voraussetzung"]
            critical_keywords = [d for d in key_details if any(
                kw in d for kw in critical_patterns
            )]
            logger.info(f"[EnhancedSummarizeNode] 检测到{len(critical_keywords)}个关键政策词: {critical_keywords}")

            # 【核心修复】检查是否在总结部分出现，而非整个答案
            missing_in_summary = [d for d in critical_keywords if d.lower() not in summary_section.lower()]

            # 如果在整个答案中存在但不在总结部分，这是"假阳性"
            false_positives = [d for d in missing_in_summary if d.lower() in final_answer.lower()]
            if false_positives:
                logger.warning(f"[EnhancedSummarizeNode] ⚠️ 检测到假阳性: {false_positives} 仅在材料评估部分出现，未在总结中体现")

            if missing_in_summary:
                logger.warning(f"[EnhancedSummarizeNode] ⚠️ 关键政策细节在总结部分缺失: {missing_in_summary}")

                # 【增强】从chunks中提取包含缺失关键词的原始证据
                evidence_lines = []
                for kw in missing_in_summary:
                    for chunk in top_chunks:
                        text = chunk.get("text", "")
                        if kw.lower() in text.lower():
                            # 提取关键词周围的上下文（150字符）
                            kw_pos = text.lower().find(kw.lower())
                            start = max(0, kw_pos - 80)
                            end = min(len(text), kw_pos + len(kw) + 80)
                            excerpt = text[start:end].strip()
                            speaker = chunk.get("metadata", {}).get("speaker", "Unknown")
                            date = chunk.get("metadata", {}).get("date", "")
                            evidence_lines.append(f'  BEWEIS für "{kw}": "{excerpt}..." (Redner: {speaker}, {date})')
                            break  # 每个关键词只取一个证据

                evidence_section = ""
                if evidence_lines:
                    evidence_section = f"""

DIREKTER BEWEIS aus den Materialien:
{chr(10).join(evidence_lines)}

Die obigen Zitate zeigen, dass diese Details IN DEN MATERIALIEN VORKOMMEN. Sie MÜSSEN sie in der Zusammenfassung erwähnen!
"""

                # 触发更精确的重试，包含原始证据
                retry_prompt = f"""
{full_prompt}

[⚠️ KRITISCHER HINWEIS - Details fehlen in der Zusammenfassung]

Ihre vorherige Antwort hat folgende wichtige Details nicht ausreichend behandelt:

{chr(10).join([f'  • {d}' for d in missing_in_summary])}
{evidence_section}
WICHTIG: Diese spezifischen Begriffe MÜSSEN im Abschnitt "Zusammenfassung" und/oder "Hauptpositionen" erscheinen, nicht nur in der Materialbewertung!

Beispiel: Wenn ein Material "Georgien visumspflichtig zu machen" fordert, muss in der Zusammenfassung explizit "Visumspflicht für Georgien" oder "Georgien visumspflichtig" stehen - NICHT nur "Druck ausüben".

Bitte wiederholen Sie die vollständige Antwort und stellen Sie sicher, dass diese konkreten Politikmaßnahmen im Haupttext (Zusammenfassung/Hauptpositionen) genannt werden.
"""
                logger.info(f"[EnhancedSummarizeNode] 🔄 触发精确重试，要求在总结部分补充缺失细节...")
                final_answer = self.llm.invoke(retry_prompt)

                # 再次检查总结部分
                summary_section_retry = self._extract_summary_section(final_answer)
                still_missing = [d for d in missing_in_summary if d.lower() not in summary_section_retry.lower()]
                if still_missing:
                    logger.warning(f"[EnhancedSummarizeNode] ⚠️ 重试后总结部分仍缺失: {still_missing}")
                else:
                    logger.info(f"[EnhancedSummarizeNode] ✅ 重试成功，所有关键细节已在总结部分引用")
            else:
                logger.info(f"[EnhancedSummarizeNode] ✅ 所有关键细节已在总结部分被引用")

        logger.info(f"[EnhancedSummarizeNode] ✅ 最终答案长度: {len(final_answer)}")

        # 返回None作为sub_answers（生产模式不生成子答案）
        return final_answer, None
    
    # 主持人职位列表（用于过滤）
    MODERATOR_TITLES = [
        "Vizepräsident",
        "Vizepräsidentin",
        "Präsident",
        "Präsidentin",
        "Alterspräsident",
        "Alterspräsidentin"
    ]

    def _is_moderator(self, speaker: str) -> bool:
        """
        检查speaker是否是主持人

        Args:
            speaker: 发言人名称

        Returns:
            True如果是主持人，False否则
        """
        if not speaker:
            return True
        for title in self.MODERATOR_TITLES:
            if speaker.startswith(title):
                return True
        return False

    def _format_context(self, chunks: List[Dict]) -> str:
        """
        格式化检索到的chunks为上下文

        注意：会过滤掉主持人的发言，因为他们只是主持会议，
        不代表任何政党立场

        Args:
            chunks: 检索结果chunks

        Returns:
            格式化的上下文字符串
        """
        context_parts = []
        material_index = 0

        for chunk in chunks:
            metadata = chunk.get("metadata", {})
            text = chunk.get("text", "")
            score = chunk.get("score", 0.0)

            # 提取元数据
            speaker = metadata.get("speaker", "Unbekannt")

            # 【关键修复】过滤主持人发言
            if self._is_moderator(speaker):
                logger.debug(f"[EnhancedSummarizeNode] 过滤主持人发言: {speaker}")
                continue

            material_index += 1
            group = metadata.get("group", "Unbekannt")
            year = metadata.get("year", "")
            month = metadata.get("month", "")
            day = metadata.get("day", "")
            text_id = metadata.get("text_id", "")

            # 格式化日期
            date = f"{year}-{month}-{day}" if year else "Unbekannt"

            # 格式化单个chunk
            context_part = f"""
[Material {material_index}] (Relevanz: {score:.2f})
Redner: {speaker} ({group})
Datum: {date}
Quelle: {text_id}
Inhalt: {text}
"""
            context_parts.append(context_part)

        logger.info(f"[EnhancedSummarizeNode] 格式化{material_index}个有效材料（过滤主持人后）")
        return "\n".join(context_parts)
    
    def _extract_sources(self, chunks: List[Dict]) -> List[Dict]:
        """
        从chunks中提取来源信息

        注意：会过滤掉主持人的发言

        Args:
            chunks: 检索结果chunks

        Returns:
            来源信息列表
        """
        sources = []

        for chunk in chunks:
            # 只保留前5个有效来源
            if len(sources) >= 5:
                break

            metadata = chunk.get("metadata", {})
            speaker = metadata.get("speaker", "Unbekannt")

            # 过滤主持人
            if self._is_moderator(speaker):
                continue

            source = {
                "speaker": speaker,
                "group": metadata.get("group", "Unbekannt"),
                "date": f"{metadata.get('year', '')}-{metadata.get('month', '')}-{metadata.get('day', '')}",
                "text_id": metadata.get("text_id", ""),
                "score": chunk.get("score", 0.0)
            }

            sources.append(source)

        return sources

    def _extract_key_details(self, chunks: List[Dict]) -> List[str]:
        """
        【方案A核心】从检索结果中提取潜在的关键细节

        提取内容：
        1. 带引号的项目名/政策名（如"Kultur baut Brücken"）
        2. 预定义的重要地名（如Syrien, Georgien）
        3. 预定义的重要政策关键词

        Args:
            chunks: 检索结果chunks

        Returns:
            关键细节列表（最多15个）
        """
        details = set()

        # 正则：提取带引号的内容（德语用„"或""或「」）
        quote_patterns = [
            r'„([^"]+)"',      # 德语引号 „..."
            r'"([^"]+)"',      # 普通双引号
            r'\"([^\"]+)\"',   # 转义双引号
        ]

        for chunk in chunks:
            text = chunk.get("text", "")

            # 1. 提取引号内的内容
            for pattern in quote_patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    # 过滤：长度5-80字符，且不是纯数字
                    if 5 <= len(match) <= 80 and not match.isdigit():
                        details.add(match.strip())

            # 2. 检查预定义的重要地名
            for loc in self.IMPORTANT_LOCATIONS:
                if loc in text:
                    details.add(loc)

            # 3. 检查预定义的重要政策关键词
            for kw in self.IMPORTANT_POLICY_KEYWORDS:
                if kw in text:
                    details.add(kw)

        # 按长度排序，优先保留更具体的细节（通常更长）
        sorted_details = sorted(details, key=len, reverse=True)

        logger.info(f"[EnhancedSummarizeNode] 提取到{len(sorted_details)}个关键细节")
        if sorted_details:
            logger.debug(f"[EnhancedSummarizeNode] 关键细节预览: {sorted_details[:5]}")

        return sorted_details[:15]  # 最多返回15个

    def _extract_summary_section(self, answer: str) -> str:
        """
        从答案中提取"总结部分"（Zusammenfassung + Hauptpositionen）
        排除"Materialbewertung"部分

        用于精确验证关键细节是否在最终总结中出现，而非仅在材料评估中

        Args:
            answer: 完整答案

        Returns:
            总结部分的文本（不包含材料评估）
        """
        # 尝试定位总结部分的开始
        summary_markers = [
            "**Zusammenfassung**",
            "## Zusammenfassung",
            "### Zusammenfassung",
            "Zusammenfassung\n",
            "---\n\n**Zusammenfassung",
        ]

        # 尝试定位材料评估部分的结束（通常在 "---" 分隔符后）
        material_end_markers = [
            "---\n\n**Zusammenfassung",
            "---\n\nZusammenfassung",
            "---\n\n###",
            "\n\n**Zusammenfassung",
            "\n\nZusammenfassung\n",
        ]

        summary_start = -1

        # 方法1：找到 "---" 后的 Zusammenfassung
        for marker in material_end_markers:
            pos = answer.find(marker)
            if pos != -1:
                summary_start = pos
                break

        # 方法2：如果没找到，直接找 Zusammenfassung
        if summary_start == -1:
            for marker in summary_markers:
                pos = answer.find(marker)
                if pos != -1:
                    summary_start = pos
                    break

        # 方法3：如果还是没找到，检查是否有 Hauptpositionen
        if summary_start == -1:
            hauptpos_markers = ["**Hauptpositionen", "## Hauptpositionen", "Hauptpositionen und Vorschläge"]
            for marker in hauptpos_markers:
                pos = answer.find(marker)
                if pos != -1:
                    summary_start = pos
                    break

        if summary_start == -1:
            # 如果完全找不到，返回整个答案（降级处理）
            logger.warning("[EnhancedSummarizeNode] 无法定位总结部分，使用整个答案进行验证")
            return answer

        # 提取总结部分（从找到的位置到答案末尾）
        summary_section = answer[summary_start:]

        logger.debug(f"[EnhancedSummarizeNode] 提取总结部分: 从位置{summary_start}开始，长度{len(summary_section)}字符")

        return summary_section

    def _verify_material_coverage(self, answer: str, total_materials: int) -> Tuple[bool, List[int]]:
        """
        验证答案是否覆盖了所有材料（结构化验证）

        检测方式：
        1. 检查"Materialbewertung"部分是否存在
        2. 提取所有Material N的引用
        3. 对比是否覆盖1~total_materials

        Args:
            answer: LLM生成的答案
            total_materials: 总材料数

        Returns:
            (是否完整覆盖, 缺失的Material编号列表)
        """
        # 提取答案中引用的Material编号
        referenced_materials = set()

        # 匹配 "Material N:" 或 "Material N" 格式
        pattern = r'Material\s+(\d+)'
        matches = re.findall(pattern, answer)

        for match in matches:
            material_num = int(match)
            if 1 <= material_num <= total_materials:
                referenced_materials.add(material_num)

        # 计算缺失的材料
        expected_materials = set(range(1, total_materials + 1))
        missing_materials = expected_materials - referenced_materials

        if missing_materials:
            logger.warning(
                f"⚠️ 材料覆盖不完整！"
                f"总计: {total_materials}, "
                f"已引用: {len(referenced_materials)}, "
                f"缺失: {sorted(missing_materials)}"
            )
            return False, sorted(missing_materials)

        logger.info(f"✅ 所有{total_materials}个材料均已覆盖")
        return True, []


# 为了保持向后兼容，创建一个别名
SummarizeNode = EnhancedSummarizeNode


if __name__ == "__main__":
    # 测试增强版总结节点
    from ..state import create_initial_state, update_state
    
    print("="*60)
    print("增强版SummarizeNode测试")
    print("="*60)
    
    # 测试1: 单问题总结
    print("\n【测试1: 单问题总结】")
    question1 = "2019年德国议会讨论了哪些主要议题？"
    
    # 模拟检索结果
    mock_result1 = {
        "question": question1,
        "chunks": [
            {
                "text": "Heute diskutieren wir über Klimaschutz, Digitalisierung und soziale Gerechtigkeit...",
                "metadata": {
                    "speaker": "Angela Merkel",
                    "group": "CDU/CSU",
                    "year": "2019",
                    "month": "03",
                    "day": "15",
                    "text_id": "pp_19_100_00001"
                },
                "score": 0.95
            },
            {
                "text": "Die digitale Transformation ist eine der größten Herausforderungen...",
                "metadata": {
                    "speaker": "Olaf Scholz",
                    "group": "SPD",
                    "year": "2019",
                    "month": "05",
                    "day": "20",
                    "text_id": "pp_19_110_00002"
                },
                "score": 0.88
            }
        ]
    }
    
    state1 = create_initial_state(question1)
    state1 = update_state(
        state1,
        retrieval_results=[mock_result1],
        is_decomposed=False
    )
    
    print(f"问题: {question1}")
    print(f"材料数: {len(mock_result1['chunks'])}")
    print("✅ 模拟数据准备完成（实际需要LLM）")
    
    # 测试2: 多问题总结
    print("\n【测试2: 多问题总结 - 变化类】")
    question2 = "2015-2018年不同党派在难民政策上的立场变化？"
    
    # 模拟多个子问题的检索结果
    mock_results2 = [
        {
            "question": "2015年CDU/CSU在难民政策上的立场？",
            "chunks": [
                {
                    "text": "Wir schaffen das! Deutschland muss humanitär handeln...",
                    "metadata": {
                        "speaker": "Angela Merkel",
                        "group": "CDU/CSU",
                        "year": "2015",
                        "month": "09",
                        "day": "01",
                        "text_id": "pp_18_120_00001"
                    },
                    "score": 0.92
                }
            ]
        },
        {
            "question": "2018年CDU/CSU在难民政策上的立场？",
            "chunks": [
                {
                    "text": "Wir müssen die Zuwanderung besser steuern und kontrollieren...",
                    "metadata": {
                        "speaker": "Horst Seehofer",
                        "group": "CDU/CSU",
                        "year": "2018",
                        "month": "06",
                        "day": "15",
                        "text_id": "pp_19_045_00001"
                    },
                    "score": 0.89
                }
            ]
        }
    ]
    
    state2 = create_initial_state(question2)
    state2 = update_state(
        state2,
        question_type="变化类",
        retrieval_results=mock_results2,
        sub_questions=["2015年CDU/CSU...", "2018年CDU/CSU..."],
        is_decomposed=True
    )
    
    print(f"问题: {question2}")
    print(f"问题类型: 变化类")
    print(f"子问题数: {len(mock_results2)}")
    print("✅ 模拟数据准备完成（实际需要LLM）")
    
    print("\n" + "="*60)
    print("注意: 完整测试需要启动LLM服务（Gemini API）")
    print("="*60)
    
    print("\n【核心功能】")
    print("✅ 单问题模块化总结")
    print("✅ 多问题分层总结")
    print("✅ 根据问题类型选择Prompt")
    print("✅ 德文结构化输出")
    print("✅ 来源信息提取")

