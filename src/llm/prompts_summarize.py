"""
总结Prompt模板 - 增强版
支持模块化输出和分层总结
"""

from typing import Dict, List


class SummarizePrompts:
    """总结Prompt管理器"""
    
    # ========== 德文系统Prompt ==========
    
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
    
    # ========== 单子问题总结（模块化输出）==========
    
    SINGLE_QUESTION_MODULAR = """Bitte beantworten Sie die folgende Frage basierend auf den bereitgestellten Materialien.

[Frage]
{question}

[Materialien]
{context}

[Anforderungen]

1. **Antwortformat** (auf Deutsch):

```
**Zusammenfassung**
[Kurze Zusammenfassung der Hauptpunkte in 2-3 Sätzen]

**Wichtige Aussagen**

• **[Redner 1, Partei]**:
  „[Kernaussage oder Zitat]"
  
• **[Redner 2, Partei]**:
  „[Kernaussage oder Zitat]"

**Belege aus den Materialien**
- [Belegnummer 1]: [Zusammenfassung des Belegs]
- [Belegnummer 2]: [Zusammenfassung des Belegs]

**Quellen**
- Material 1: [text_id (falls vorhanden)], Redner (Partei), YYYY-MM-DD
- Material 2: [text_id (falls vorhanden)], Redner (Partei), YYYY-MM-DD
- ...
```

2. **Wichtige Regeln**:
   - Verwenden Sie nur Informationen aus den Materialien
   - Zitieren Sie wörtlich oder paraphrasieren Sie akkurat
   - Geben Sie bei jeder Aussage Redner und Datum an
   - Ordnen Sie nach Relevanz
   - **KRITISCH**: Der Quellen-Abschnitt MUSS als Liste formatiert werden (mit `-` Zeichen)
   - **KRITISCH**: Jede Quelle MUSS enthalten: Redner, (Partei), Datum im Format YYYY-MM-DD
   - **KRITISCH**: Verwenden Sie NIEMALS Absatzform für Quellen, sondern nur Listenpunkte

3. **【NEU】Informationsvollständigkeit - Politikdimensionen Checklist**:

   ⚠️ **KRITISCH**: Prüfen Sie, ob die Materialien folgende Politikbereiche erwähnen, und integrieren Sie sie in die Antwort:

   - [ ] **Sichere Herkunftsländer** (Einstufung von Ländern als sichere Herkunftsstaaten)
   - [ ] **Grenzkontrollen** (Binnengrenzkontrollen, Grenzschutz, europäische Außengrenzen)
   - [ ] **Familiennachzug** (Regelungen zum Familiennachzug für Flüchtlinge)
   - [ ] **Abschiebung/Rückführung** (Rückführungspolitik, Ausreisepflicht, Abschiebungen)
   - [ ] **Europäische Lösung** (EU-Verteilquoten, europäische Zusammenarbeit, GEAS)
   - [ ] **Integration** (Integrationsmaßnahmen, Sprachkurse, Arbeitsmarktintegration)
   - [ ] **Asylverfahren** (Beschleunigung, Asylpakete, Verfahrensreformen)
   - [ ] **Fluchtursachenbekämpfung** (Entwicklungshilfe, Stabilisierung von Herkunftsländern)
   - [ ] **Unterscheidung Asyl/Migration** (Trennung von Asyl und Arbeitsmigration)
   - [ ] **Obergrenze/Kontingente** (Zahlenbegrenzungen, Aufnahmekontingente)

   **Wichtig**:
   - Wenn ein Politikbereich in den Materialien MEHRFACH erwähnt wird, ist er besonders wichtig → MUSS in der Antwort erscheinen!
   - Bevorzugen Sie KONKRETE MASSNAHMEN vor ALLGEMEINEN AUSSAGEN
   - Beispiel RICHTIG: "Einstufung der Balkanstaaten als sichere Herkunftsländer"
   - Beispiel FALSCH: "Ordnung und Steuerung" (zu allgemein, Details fehlen)

4. **Wenn Materialien unzureichend sind**:
   Geben Sie klar an: "Die vorliegenden Materialien sind nicht ausreichend, um diese Frage vollständig zu beantworten."

Bitte antworten Sie jetzt auf Deutsch im oben genannten Format.
"""
    
    # ========== 变化类问题总结 ==========
    
    CHANGE_ANALYSIS_SUMMARY = """Bitte analysieren Sie die Veränderungen basierend auf den Teilfragen und ihren Antworten.

[Ursprüngliche Frage]
{original_question}

[Teilfragen und Antworten]
{sub_qa_pairs}

[Anforderungen für die Zusammenfassung]

1. **Struktur der Antwort** (auf Deutsch):

**⚠️ WICHTIG**: Sie MÜSSEN für JEDES Jahr aus den Teilfragen einen eigenen Abschnitt erstellen! Lassen Sie KEIN Jahr aus!

```
**Überblick**
[2-3 Sätze zur Gesamtentwicklung über ALLE untersuchten Jahre]

**Zeitliche Entwicklung**

⚠️ **PFLICHT**: Erstellen Sie einen Abschnitt für JEDES Jahr aus den Teilfragen! Beispiel unten zeigt NUR das Format - Sie müssen ALLE Jahre abdecken!

• **2015**
  - Position: [Zusammenfassung der Position 2015]
  - Zitat: „[Repräsentatives Zitat]" (Redner, Datum)

• **2016**
  - Position: [Zusammenfassung der Position 2016]
  - Zitat: „[Repräsentatives Zitat]" (Redner, Datum)

• **2017**
  - Position: [Zusammenfassung der Position 2017]
  - Zitat: „[Repräsentatives Zitat]" (Redner, Datum)

... [Fahren Sie fort für ALLE weiteren Jahre aus den Teilfragen]

**Hauptveränderungen**

1. **Partei 1**:
   Von [Position Jahr 1] zu [Position Jahr N]
   Wendepunkte: [Jahr X - Ereignis]

2. **Partei 2**:
   Von [Position Jahr 1] zu [Position Jahr N]
   Wendepunkte: [Jahr X - Ereignis]

**Gemeinsamkeiten und Unterschiede**
- Gemeinsamkeiten: [Beschreibung]
- Unterschiede: [Beschreibung]

**Zusammenfassung**
[Abschließende Bewertung der Entwicklung]

**Quellen**
- Material 1: [text_id (falls vorhanden)], Redner (Partei), YYYY-MM-DD
- Material 2: [text_id (falls vorhanden)], Redner (Partei), YYYY-MM-DD
- ...
```

2. **Analysefokus**:
   - **PFLICHT**: Decken Sie ALLE Jahre aus den Teilfragen ab - lassen Sie KEIN Jahr aus!
   - Identifizieren Sie **Wendepunkte** (wann änderte sich die Position?)
   - Erklären Sie **Gründe** für Veränderungen (wenn in Materialien erwähnt)
   - Vergleichen Sie **Tempo und Richtung** der Veränderungen
   - Verwenden Sie für JEDES Jahr mindestens ein Zitat mit Quellenangabe

3. **【NEU】Informationsvollständigkeit - Politikdimensionen Checklist**:

   ⚠️ **KRITISCH**: Prüfen Sie für JEDES Jahr, ob die Materialien folgende Politikbereiche erwähnen, und integrieren Sie sie in die Zusammenfassung:

   - [ ] **Sichere Herkunftsländer** (Einstufung von Ländern als sichere Herkunftsstaaten)
   - [ ] **Grenzkontrollen** (Binnengrenzkontrollen, Grenzschutz, europäische Außengrenzen)
   - [ ] **Familiennachzug** (Regelungen zum Familiennachzug für Flüchtlinge)
   - [ ] **Abschiebung/Rückführung** (Rückführungspolitik, Ausreisepflicht, Abschiebungen)
   - [ ] **Europäische Lösung** (EU-Verteilquoten, europäische Zusammenarbeit, GEAS)
   - [ ] **Integration** (Integrationsmaßnahmen, Sprachkurse, Arbeitsmarktintegration)
   - [ ] **Asylverfahren** (Beschleunigung, Asylpakete, Verfahrensreformen)
   - [ ] **Fluchtursachenbekämpfung** (Entwicklungshilfe, Stabilisierung von Herkunftsländern)
   - [ ] **Unterscheidung Asyl/Migration** (Trennung von Asyl und Arbeitsmigration)
   - [ ] **Obergrenze/Kontingente** (Zahlenbegrenzungen, Aufnahmekontingente)

   **Wichtig**:
   - Wenn ein Politikbereich in den Materialien MEHRFACH erwähnt wird, ist er besonders wichtig → MUSS in der Zusammenfassung erscheinen!
   - Bevorzugen Sie KONKRETE MASSNAHMEN vor ALLGEMEINEN AUSSAGEN
   - Beispiel RICHTIG: "Einstufung der Balkanstaaten als sichere Herkunftsländer"
   - Beispiel FALSCH: "Ordnung und Steuerung" (zu allgemein, Details fehlen)

3. **Quellenverweis**:
   - **PFLICHT**: Zitieren Sie mindestens EINE Quelle pro Jahr!
   - Geben Sie bei wichtigen Aussagen Redner und Datum an
   - Nutzen Sie repräsentative Zitate
   - **KRITISCH**: Der Quellen-Abschnitt MUSS als Liste formatiert werden (mit `-` Zeichen)
   - **KRITISCH**: Jede Quelle MUSS enthalten: Redner, (Partei), Datum im Format YYYY-MM-DD
   - **KRITISCH**: Verwenden Sie NIEMALS Absatzform für Quellen, sondern nur Listenpunkte
   - **KRITISCH**: Stellen Sie sicher, dass Quellen aus ALLEN Jahren in den Teilfragen erscheinen!

Bitte antworten Sie jetzt auf Deutsch im strukturierten Format.
"""
    
    # ========== 对比类问题总结 ==========
    
    COMPARISON_SUMMARY = """Bitte erstellen Sie einen Vergleich basierend auf den Teilfragen und ihren Antworten.

[Ursprüngliche Frage]
{original_question}

[Teilfragen und Antworten]
{sub_qa_pairs}

[Anforderungen für den Vergleich]

1. **Struktur der Antwort** (auf Deutsch):

```
**Überblick**
[2-3 Sätze zum Gesamtvergleich]

**Positionen der einzelnen Akteure**

• **Partei/Redner 1**
  Position: [Zusammenfassung]
  Kernargumente:
  - [Argument 1]
  - [Argument 2]
  Zitat: „[Repräsentatives Zitat]" (Datum)

• **Partei/Redner 2**
  Position: [Zusammenfassung]
  Kernargumente:
  - [Argument 1]
  - [Argument 2]
  Zitat: „[Repräsentatives Zitat]" (Datum)

**Vergleichstabelle**

| Aspekt | Partei 1 | Partei 2 | Partei 3 |
|--------|----------|----------|----------|
| Grundposition | [Position] | [Position] | [Position] |
| Hauptargumente | [Argumente] | [Argumente] | [Argumente] |
| Vorschläge | [Vorschläge] | [Vorschläge] | [Vorschläge] |

**Gemeinsamkeiten**
- [Gemeinsamer Punkt 1]
- [Gemeinsamer Punkt 2]

**Unterschiede**
- [Unterschied 1]
- [Unterschied 2]

**Zusammenfassung**
[Abschließende Bewertung des Vergleichs]

**Quellen**
- Material 1: [text_id (falls vorhanden)], Redner (Partei), YYYY-MM-DD
- Material 2: [text_id (falls vorhanden)], Redner (Partei), YYYY-MM-DD
- ...
```

2. **Analysefokus**:
   - Identifizieren Sie **Kernunterschiede**
   - Finden Sie **überraschende Gemeinsamkeiten**
   - Bewerten Sie **Stärke der Unterschiede**

3. **【NEU】Informationsvollständigkeit - Politikdimensionen Checklist**:

   ⚠️ **KRITISCH**: Prüfen Sie, ob die Materialien folgende Politikbereiche erwähnen, und integrieren Sie sie in den Vergleich:

   - [ ] **Sichere Herkunftsländer** (Einstufung von Ländern als sichere Herkunftsstaaten)
   - [ ] **Grenzkontrollen** (Binnengrenzkontrollen, Grenzschutz, europäische Außengrenzen)
   - [ ] **Familiennachzug** (Regelungen zum Familiennachzug für Flüchtlinge)
   - [ ] **Abschiebung/Rückführung** (Rückführungspolitik, Ausreisepflicht, Abschiebungen)
   - [ ] **Europäische Lösung** (EU-Verteilquoten, europäische Zusammenarbeit, GEAS)
   - [ ] **Integration** (Integrationsmaßnahmen, Sprachkurse, Arbeitsmarktintegration)
   - [ ] **Asylverfahren** (Beschleunigung, Asylpakete, Verfahrensreformen)
   - [ ] **Fluchtursachenbekämpfung** (Entwicklungshilfe, Stabilisierung von Herkunftsländern)
   - [ ] **Unterscheidung Asyl/Migration** (Trennung von Asyl und Arbeitsmigration)
   - [ ] **Obergrenze/Kontingente** (Zahlenbegrenzungen, Aufnahmekontingente)

   **Wichtig**:
   - Wenn ein Politikbereich in den Materialien MEHRFACH erwähnt wird, ist er besonders wichtig → MUSS im Vergleich erscheinen!
   - Bevorzugen Sie KONKRETE MASSNAHMEN vor ALLGEMEINEN AUSSAGEN
   - Beispiel RICHTIG: "CDU fordert Einstufung der Balkanstaaten als sichere Herkunftsländer, Grüne lehnen dies ab"
   - Beispiel FALSCH: "CDU betont Ordnung, Grüne betonen Humanität" (zu allgemein, Details fehlen)

4. **Objektive Darstellung**:
   - Vermeiden Sie Wertungen
   - Präsentieren Sie alle Positionen gleichberechtigt

5. **Quellen-Format (KRITISCH)**:
   - Der Quellen-Abschnitt MUSS als Liste formatiert werden (mit `-` Zeichen)
   - Jede Quelle MUSS enthalten: Redner, (Partei), Datum im Format YYYY-MM-DD
   - Verwenden Sie NIEMALS Absatzform für Quellen, sondern nur Listenpunkte

Bitte antworten Sie jetzt auf Deutsch im strukturierten Format.
"""
    
    # ========== 总结类问题总结 ==========
    
    SUMMARY_TYPE_SUMMARY = """Bitte erstellen Sie eine Zusammenfassung basierend auf den Teilfragen und ihren Antworten.

[Ursprüngliche Frage]
{original_question}

[Teilfragen und Antworten]
{sub_qa_pairs}

[Anforderungen für die Zusammenfassung]

1. **Struktur der Antwort** (auf Deutsch):

```
**Überblick**
[2-3 Sätze zur Hauptaussage]

**Hauptpositionen**

Nach Themen geordnet:

• **Thema/Aspekt 1**
  Partei/Redner: [Position und Argumente]
  Zitat: „[Kernzitat]" (Datum)

• **Thema/Aspekt 2**
  Partei/Redner: [Position und Argumente]
  Zitat: „[Kernzitat]" (Datum)

**Kernaussagen der wichtigsten Redner**

• **Redner 1, Partei** (Datum):
  - [Hauptaussage 1]
  - [Hauptaussage 2]

• **Redner 2, Partei** (Datum):
  - [Hauptaussage 1]
  - [Hauptaussage 2]

**Zusammenfassung**
[Abschließende Zusammenfassung der wichtigsten Punkte]

**Quellen**
- Material 1: [text_id (falls vorhanden)], Redner (Partei), YYYY-MM-DD
- Material 2: [text_id (falls vorhanden)], Redner (Partei), YYYY-MM-DD
- ...
```

2. **Strukturierung**:
   - Gruppieren Sie nach Themen oder Aspekten
   - Heben Sie Hauptredner hervor
   - Extrahieren Sie Kernbotschaften

3. **Vollständigkeit**:
   - Decken Sie alle relevanten Aspekte ab
   - Geben Sie repräsentative Zitate
   - Verweisen Sie auf Quellen

4. **【NEU】Informationsvollständigkeit - Politikdimensionen Checklist**:

   ⚠️ **KRITISCH**: Prüfen Sie, ob die Materialien folgende Politikbereiche erwähnen, und integrieren Sie sie in die Zusammenfassung:

   - [ ] **Sichere Herkunftsländer** (Einstufung von Ländern als sichere Herkunftsstaaten)
   - [ ] **Grenzkontrollen** (Binnengrenzkontrollen, Grenzschutz, europäische Außengrenzen)
   - [ ] **Familiennachzug** (Regelungen zum Familiennachzug für Flüchtlinge)
   - [ ] **Abschiebung/Rückführung** (Rückführungspolitik, Ausreisepflicht, Abschiebungen)
   - [ ] **Europäische Lösung** (EU-Verteilquoten, europäische Zusammenarbeit, GEAS)
   - [ ] **Integration** (Integrationsmaßnahmen, Sprachkurse, Arbeitsmarktintegration)
   - [ ] **Asylverfahren** (Beschleunigung, Asylpakete, Verfahrensreformen)
   - [ ] **Fluchtursachenbekämpfung** (Entwicklungshilfe, Stabilisierung von Herkunftsländern)
   - [ ] **Unterscheidung Asyl/Migration** (Trennung von Asyl und Arbeitsmigration)
   - [ ] **Obergrenze/Kontingente** (Zahlenbegrenzungen, Aufnahmekontingente)

   **Wichtig**:
   - Wenn ein Politikbereich in den Materialien MEHRFACH erwähnt wird, ist er besonders wichtig → MUSS in der Zusammenfassung erscheinen!
   - Bevorzugen Sie KONKRETE MASSNAHMEN vor ALLGEMEINEN AUSSAGEN
   - Beispiel RICHTIG: "Einstufung der Balkanstaaten als sichere Herkunftsländer"
   - Beispiel FALSCH: "Ordnung und Steuerung" (zu allgemein, Details fehlen)

5. **Quellen-Format (KRITISCH)**:
   - Der Quellen-Abschnitt MUSS als Liste formatiert werden (mit `-` Zeichen)
   - Jede Quelle MUSS enthalten: Redner, (Partei), Datum im Format YYYY-MM-DD
   - Verwenden Sie NIEMALS Absatzform für Quellen, sondern nur Listenpunkte

Bitte antworten Sie jetzt auf Deutsch im strukturierten Format.
"""
    
    # ========== 趋势分析总结 ==========
    
    TREND_ANALYSIS_SUMMARY = """Bitte analysieren Sie den Trend basierend auf den Teilfragen und ihren Antworten.

[Ursprüngliche Frage]
{original_question}

[Teilfragen und Antworten]
{sub_qa_pairs}

[Anforderungen für die Trendanalyse]

1. **Struktur der Antwort** (auf Deutsch):

```
**Überblick**
[2-3 Sätze zum Gesamttrend]

**Zeitreihenanalyse**

• **Phase 1: Zeitraum**
  Charakteristik: [Beschreibung]
  Schlüsselereignisse: [Ereignisse]

• **Phase 2: Zeitraum**
  Charakteristik: [Beschreibung]
  Veränderungen gegenüber Phase 1: [Veränderungen]

• **Phase 3: Zeitraum**
  Charakteristik: [Beschreibung]
  Veränderungen gegenüber Phase 2: [Veränderungen]

**Trendentwicklung**

• **Aufwärtstrend**
- [Aspekt 1]: Von [Zustand A] zu [Zustand B]
- [Aspekt 2]: Von [Zustand A] zu [Zustand B]

• **Rückläufige Entwicklung**
- [Aspekt 1]: Von [Zustand A] zu [Zustand B]

• **Zyklische Muster**
- [Beschreibung wiederkehrender Muster]

**Wendepunkte**
- Jahr: [Ereignis und Auswirkung]
- Jahr: [Ereignis und Auswirkung]

**Zusammenfassung**
[Abschließende Bewertung des Trends und mögliche Implikationen]

**Quellen**
- Material 1: [text_id (falls vorhanden)], Redner (Partei), YYYY-MM-DD
- Material 2: [text_id (falls vorhanden)], Redner (Partei), YYYY-MM-DD
- ...
```

2. **Analysefokus**:
   - Identifizieren Sie **klare Phasen**
   - Erkennen Sie **Wendepunkte**
   - Beschreiben Sie **Richtung und Geschwindigkeit**

3. **Evidenzbasiert**:
   - Belegen Sie Trends mit konkreten Daten
   - Zitieren Sie repräsentative Aussagen
   - Vermeiden Sie Spekulationen

4. **【NEU】Informationsvollständigkeit - Politikdimensionen Checklist**:

   ⚠️ **KRITISCH**: Prüfen Sie für ALLE Zeitphasen, ob die Materialien folgende Politikbereiche erwähnen, und integrieren Sie sie in die Trendanalyse:

   - [ ] **Sichere Herkunftsländer** (Einstufung von Ländern als sichere Herkunftsstaaten)
   - [ ] **Grenzkontrollen** (Binnengrenzkontrollen, Grenzschutz, europäische Außengrenzen)
   - [ ] **Familiennachzug** (Regelungen zum Familiennachzug für Flüchtlinge)
   - [ ] **Abschiebung/Rückführung** (Rückführungspolitik, Ausreisepflicht, Abschiebungen)
   - [ ] **Europäische Lösung** (EU-Verteilquoten, europäische Zusammenarbeit, GEAS)
   - [ ] **Integration** (Integrationsmaßnahmen, Sprachkurse, Arbeitsmarktintegration)
   - [ ] **Asylverfahren** (Beschleunigung, Asylpakete, Verfahrensreformen)
   - [ ] **Fluchtursachenbekämpfung** (Entwicklungshilfe, Stabilisierung von Herkunftsländern)
   - [ ] **Unterscheidung Asyl/Migration** (Trennung von Asyl und Arbeitsmigration)
   - [ ] **Obergrenze/Kontingente** (Zahlenbegrenzungen, Aufnahmekontingente)

   **Wichtig**:
   - Wenn ein Politikbereich in den Materialien MEHRFACH erwähnt wird, ist er besonders wichtig → MUSS in der Trendanalyse erscheinen!
   - Bevorzugen Sie KONKRETE MASSNAHMEN vor ALLGEMEINEN AUSSAGEN
   - Zeigen Sie Trends bei spezifischen Politikbereichen auf (z.B. "Sichere Herkunftsländer wurden 2015 nicht erwähnt, ab 2016 zunehmend diskutiert")
   - Beispiel RICHTIG: "Trend bei Grenzkontrollen: 2015 Ablehnung, 2016-2018 schrittweise Akzeptanz"
   - Beispiel FALSCH: "Trend zur restriktiveren Politik" (zu allgemein, Details fehlen)

5. **Quellen-Format (KRITISCH)**:
   - Der Quellen-Abschnitt MUSS als Liste formatiert werden (mit `-` Zeichen)
   - Jede Quelle MUSS enthalten: Redner, (Partei), Datum im Format YYYY-MM-DD
   - Verwenden Sie NIEMALS Absatzform für Quellen, sondern nur Listenpunkte

Bitte antworten Sie jetzt auf Deutsch im strukturierten Format.
"""
    
    # ========== 通用多问题总结（兜底）==========
    
    GENERAL_MULTI_QUESTION_SUMMARY = """Bitte erstellen Sie eine umfassende Antwort basierend auf den Teilfragen und ihren Antworten.

[Ursprüngliche Frage]
{original_question}

[Teilfragen und Antworten]
{sub_qa_pairs}

[Anforderungen]

1. **Struktur**:
   - Beginnen Sie mit einem Überblick
   - Organisieren Sie Informationen logisch
   - Schließen Sie mit einer Zusammenfassung ab

2. **Integration**:
   - Synthetisieren Sie Informationen aus allen Teilantworten
   - Vermeiden Sie bloße Aneinanderreihung
   - Schaffen Sie Zusammenhänge

3. **Format** (auf Deutsch):
   - Verwenden Sie Überschriften und Aufzählungen
   - Zitieren Sie Quellen (Redner, Datum)
   - Strukturieren Sie klar und übersichtlich

4. **Qualität**:
   - Bleiben Sie faktentreu
   - Seien Sie präzise und vollständig
   - Antworten Sie auf Deutsch

5. **Quellenangabe**:
   - Geben Sie am Ende eine Liste aller verwendeten Materialien an
   - Format: [text_id (falls vorhanden)], Redner (Partei), YYYY-MM-DD

Bitte erstellen Sie jetzt die umfassende Antwort mit vollständiger Quellenangabe.
"""
    
    # ========== 辅助方法 ==========
    
    @staticmethod
    def select_summary_template(question_type: str) -> str:
        """
        根据问题类型选择合适的总结模板
        
        Args:
            question_type: 问题类型
            
        Returns:
            对应的Prompt模板
        """
        templates = {
            "变化类": SummarizePrompts.CHANGE_ANALYSIS_SUMMARY,
            "对比类": SummarizePrompts.COMPARISON_SUMMARY,
            "总结类": SummarizePrompts.SUMMARY_TYPE_SUMMARY,
            "趋势分析": SummarizePrompts.TREND_ANALYSIS_SUMMARY,
        }
        
        return templates.get(question_type, SummarizePrompts.GENERAL_MULTI_QUESTION_SUMMARY)
    
    @staticmethod
    def format_sub_qa_pairs(sub_answers: List[Dict]) -> str:
        """
        格式化子问题和答案对
        
        Args:
            sub_answers: 子答案列表
            
        Returns:
            格式化的字符串
        """
        formatted = []
        
        for i, sub_answer in enumerate(sub_answers, 1):
            question = sub_answer["question"]
            answer = sub_answer["answer"]
            sources = sub_answer.get("sources", [])
            
            qa_text = f"""
[Teilfrage {i}]
{question}

[Antwort]
{answer}
"""
            
            if sources:
                sources_text = "\n".join([
                    f"  - {src.get('speaker', 'N/A')} ({src.get('group', 'N/A')}), {src.get('date', 'N/A')}"
                    for src in sources[:3]
                ])
                qa_text += f"\n[Quellen]\n{sources_text}\n"
            
            formatted.append(qa_text)
        
        return "\n".join(formatted)


if __name__ == "__main__":
    # 测试Prompt选择
    print("=== 总结Prompt模板测试 ===\n")
    
    for q_type in ["变化类", "对比类", "总结类", "趋势分析", "其他"]:
        template = SummarizePrompts.select_summary_template(q_type)
        template_name = template.split('\n')[0] if template else "Unknown"
        print(f"{q_type}: {template_name[:50]}...")
    
    print("\n测试完成！")

