"""
总结Prompt模板 - 结构化验证版
核心改进：强制逐个评估材料，防止LLM过滤"次要论点"
"""

from typing import Dict, List


class EnhancedSummarizePrompts:
    """增强版总结Prompt管理器 - 结构化验证版"""

    # ========== 德文系统Prompt（保持一致）==========

    SYSTEM_PROMPT_DE = """Sie sind ein KI-Assistent zur Analyse von Bundestagsreden.

[Ihre Aufgabe]
- Antworten Sie auf Deutsch basierend auf den bereitgestellten Materialien
- Zitieren Sie Redner, Zeitpunkte und wichtige Aussagen
- Strukturieren Sie Antworten klar und logisch
- Erfinden Sie keine Informationen

[Wichtig]
- Bleiben Sie objektiv und faktenbasiert
- Vermeiden Sie subjektive Wertungen
- Geben Sie Quellen korrekt an
"""

    # ========== 单子问题总结（结构化验证版）==========

    SINGLE_QUESTION_ROBUST = """Bitte beantworten Sie die folgende Frage basierend auf den bereitgestellten Materialien.

[Frage]
{question}

[Materialien]
{context}

[KRITISCHE Anforderung - Strukturierte Verarbeitung]

Sie haben {total_materials} Materialien erhalten. Sie MÜSSEN ein zweistufiges Verfahren befolgen:

---

**Schritt 1: Materialbewertung (PFLICHT)**

Bewerten Sie JEDES Material einzeln auf Relevanz:

Material 1: [✓ Relevant / ✗ Nicht relevant] - [Kernaussage in 1-2 Sätzen]
Material 2: [✓ Relevant / ✗ Nicht relevant] - [Kernaussage in 1-2 Sätzen]
Material 3: [✓ Relevant / ✗ Nicht relevant] - [Kernaussage in 1-2 Sätzen]
...
Material {total_materials}: [✓ Relevant / ✗ Nicht relevant] - [Kernaussage in 1-2 Sätzen]

⚠️ **WARNUNG**: Wenn Sie ein Material überspringen, ist Ihre Antwort UNGÜLTIG!

**Bewertungskriterien**:
- ✓ Relevant: Das Material enthält direkte oder indirekte Informationen zur Frage
- ✗ Nicht relevant: Das Material behandelt ein vollständig anderes Thema

**Wichtig**: Auch "Nebenargumente" oder "nur einmal erwähnte" Punkte können relevant sein!
Beispiel: Wenn Material 9 "Wiederaufbau in Syrien als Rückkehrvoraussetzung" erwähnt,
ist das relevant für Fragen zur Flüchtlingspolitik, auch wenn es nur kurz erwähnt wird.

---

**Schritt 2: Zusammenfassung**

Erstellen Sie eine strukturierte Antwort basierend auf ALLEN als "✓ Relevant" markierten Materialien.

[Antwortformat]

```
**Materialbewertung**

Material 1: ✓ - [Kernaussage]
Material 2: ✗ - Behandelt anderes Thema
Material 3: ✓ - [Kernaussage]
...
Material {total_materials}: ✓ - [Kernaussage]

---

**Zusammenfassung**

[Kurze Übersicht der Hauptpunkte in 2-3 Sätzen]

**Hauptpositionen**

• **[Redner 1, Partei]** (Material X):
  „[Kernaussage oder Zitat]"

• **[Redner 2, Partei]** (Material Y):
  „[Kernaussage oder Zitat]"

**Spezifische Maßnahmen/Vorschläge** (falls vorhanden)

- [Maßnahme 1]: [Beschreibung]
  Quelle: Material Z, [Redner], [Datum]

**Belege aus den Materialien**

- Material 1: [Zusammenfassung]
- Material 3: [Zusammenfassung]
- ... (nur ✓-markierte Materialien)

**Quellen**

- Material 1: [Redner] ([Partei]), YYYY-MM-DD
- Material 3: [Redner] ([Partei]), YYYY-MM-DD
- ...
```

---

[Qualitätskontrolle vor Abgabe]

Prüfen Sie:
✅ Habe ich ALLE {total_materials} Materialien in Schritt 1 bewertet?
✅ Habe ich ALLE ✓-markierten Materialien in die Zusammenfassung integriert?
✅ Sind Quellen als Liste formatiert (mit `-` Zeichen)?

Bitte antworten Sie jetzt auf Deutsch im oben genannten Format.
"""

    # ========== 比较类问题总结（结构化版）==========

    COMPARISON_ROBUST = """Bitte vergleichen Sie die Positionen der Parteien basierend auf den Materialien.

[Ursprüngliche Frage]
{original_question}

[Teilfragen und Antworten]
{sub_qa_pairs}

[KRITISCHE Anforderung - Symmetrischer Vergleich]

**Schritt 1: Informationsextraktion**

Extrahieren Sie für JEDE Partei:
- Hauptpositionen
- Spezifische Maßnahmenvorschläge
- Zitate und Belege

**Schritt 2: Strukturierter Vergleich**

[Antwortformat]

```
**Zusammenfassung**

[Kurzer Gesamtvergleich in 2-3 Sätzen]

**Vergleich nach Dimensionen**

1. **[Politikbereich 1]**

   - **[Partei A]**:
     • [Spezifische Position mit Details]
     • Kernaussage: „[Zitat]" ([Redner], Material X)

   - **[Partei B]**:
     • [Spezifische Position mit Details]
     • Kernaussage: „[Zitat]" ([Redner], Material Y)

2. **[Politikbereich 2]**
   ...

**Gemeinsamkeiten**

- [Nur echte Überschneidungen, mit Belegen aus BEIDEN Parteien]

**Unterschiede**

- [Kontrastierende Positionen, konkret benannt]

**Spezifische Maßnahmenvorschläge**

- **[Partei A]**: [Liste konkreter Vorschläge mit Materialverweisen]
- **[Partei B]**: [Liste konkreter Vorschläge mit Materialverweisen]

**Quellen**

[Liste aller verwendeten Materialien]
```

Bitte antworten Sie jetzt auf Deutsch im oben genannten Format.
"""

    # ========== 变化类问题总结（结构化版）==========

    CHANGE_ANALYSIS_ROBUST = """Bitte analysieren Sie die zeitlichen Veränderungen.

[Ursprüngliche Frage]
{original_question}

[Teilfragen und Antworten]
{sub_qa_pairs}

[KRITISCHE Anforderung - Zeitliche Entwicklung]

**Schritt 1: Jahr-für-Jahr-Analyse**

Analysieren Sie für JEDES Jahr:
- Kernposition
- Spezifische Maßnahmen
- Repräsentative Zitate

**Schritt 2: Wendepunkte identifizieren**

[Antwortformat]

```
**Überblick**

[Gesamtentwicklung über ALLE Jahre in 2-3 Sätzen]

**Zeitliche Entwicklung**

• **[Jahr 1]**
  - Kernposition: [Beschreibung]
  - Spezifische Maßnahmen: [Liste]
  - Zitat: „[...]" ([Redner], Material X)

• **[Jahr 2]**
  - Kernposition: [Beschreibung]
  - Spezifische Maßnahmen: [Liste]
  - Zitat: „[...]" ([Redner], Material Y)

...

**Hauptveränderungen**

1. **Von [Jahr X] zu [Jahr Y]**:
   - Was änderte sich: [Spezifische Politikfelder/Maßnahmen]
   - Beispiel: In [Jahr X] wurde [A] vorgeschlagen, in [Jahr Y] [B]
   - Belege: Material X vs. Material Y

**Kontinuitäten**

- [Was blieb konstant über die Jahre, mit Belegen]

**Quellen**

[Liste aller Materialien chronologisch]
```

Bitte antworten Sie jetzt auf Deutsch im oben genannten Format.
"""

    @staticmethod
    def build_single_question_prompt_robust(question: str, context: str, total_materials: int) -> str:
        """构建结构化验证版单子问题Prompt"""
        return EnhancedSummarizePrompts.SINGLE_QUESTION_ROBUST.format(
            question=question,
            context=context,
            total_materials=total_materials
        )

    @staticmethod
    def build_comparison_prompt_robust(original_question: str, sub_qa_pairs: str) -> str:
        """构建结构化验证版比较Prompt"""
        return EnhancedSummarizePrompts.COMPARISON_ROBUST.format(
            original_question=original_question,
            sub_qa_pairs=sub_qa_pairs
        )

    @staticmethod
    def build_change_analysis_prompt_robust(original_question: str, sub_qa_pairs: str) -> str:
        """构建结构化验证版变化分析Prompt"""
        return EnhancedSummarizePrompts.CHANGE_ANALYSIS_ROBUST.format(
            original_question=original_question,
            sub_qa_pairs=sub_qa_pairs
        )
