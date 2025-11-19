# 多年份RAG系统完整测试报告

**测试时间**: 2025-11-18 15:35:06

**测试问题数**: 7

---

## 测试总览

| ID | 类型 | 期望年份 | 实际年份 | 耗时(秒) | 状态 |
|----|------|----------|----------|----------|------|
| Q1 | 多年变化分析 | 10年 | 0年 | 654.91 | ✅成功 |
| Q2 | 单年多党派对比 | 1年 | 0年 | 86.21 | ✅成功 |
| Q3 | 单年单党派观点 | 1年 | 0年 | 74.86 | ✅成功 |
| Q4 | 跨年多党派变化 | 4年 | 0年 | 101.44 | ✅成功 |
| Q5 | 跨年两党对比 | 3年 | 0年 | 554.06 | ✅成功 |
| Q6 | 离散年份对比 | 2年 | 0年 | 173.08 | ✅成功 |
| Q7 | 单年单党派观点 | 1年 | 0年 | 72.48 | ✅成功 |

---

## 问题 1: 多年变化分析

**问题**: Bitte fassen Sie die wichtigsten Veränderungen in der Flüchtlingspolitik der CDU/CSU seit 2015 zusammen.

### 参数提取

```json
{
  "time_range": {
    "start_year": "2015",
    "end_year": "2025",
    "specific_years": [
      "2015",
      "2016",
      "2017",
      "2018",
      "2019",
      "2020",
      "2021",
      "2022",
      "2023",
      "2024",
      "2025"
    ],
    "time_expression": "seit 2015"
  },
  "parties": [
    "CDU/CSU"
  ],
  "topics": [
    "难民政策",
    "难民"
  ],
  "keywords": [
    "变化",
    "总结"
  ]
}
```

### 检索信息

- **意图**: complex
- **问题类型**: 变化类
- **年份分布**: {}
- **检索文档数**: 508
- **ReRank后文档数**: 12

### 子问题拆解

1. {'question': 'Was ist die Position von CDU/CSU zum Thema 难民政策, 难民 im Jahr 2015?', 'target_year': '2015', 'target_party': 'CDU/CSU', 'retrieval_strategy': 'single_year'}
2. {'question': 'Was ist die Position von CDU/CSU zum Thema 难民政策, 难民 im Jahr 2016?', 'target_year': '2016', 'target_party': 'CDU/CSU', 'retrieval_strategy': 'single_year'}
3. {'question': 'Was ist die Position von CDU/CSU zum Thema 难民政策, 难民 im Jahr 2017?', 'target_year': '2017', 'target_party': 'CDU/CSU', 'retrieval_strategy': 'single_year'}
4. {'question': 'Was ist die Position von CDU/CSU zum Thema 难民政策, 难民 im Jahr 2018?', 'target_year': '2018', 'target_party': 'CDU/CSU', 'retrieval_strategy': 'single_year'}
5. {'question': 'Was ist die Position von CDU/CSU zum Thema 难民政策, 难民 im Jahr 2019?', 'target_year': '2019', 'target_party': 'CDU/CSU', 'retrieval_strategy': 'single_year'}
6. {'question': 'Was ist die Position von CDU/CSU zum Thema 难民政策, 难民 im Jahr 2020?', 'target_year': '2020', 'target_party': 'CDU/CSU', 'retrieval_strategy': 'single_year'}
7. {'question': 'Was ist die Position von CDU/CSU zum Thema 难民政策, 难民 im Jahr 2021?', 'target_year': '2021', 'target_party': 'CDU/CSU', 'retrieval_strategy': 'single_year'}
8. {'question': 'Was ist die Position von CDU/CSU zum Thema 难民政策, 难民 im Jahr 2022?', 'target_year': '2022', 'target_party': 'CDU/CSU', 'retrieval_strategy': 'single_year'}
9. {'question': 'Was ist die Position von CDU/CSU zum Thema 难民政策, 难民 im Jahr 2023?', 'target_year': '2023', 'target_party': 'CDU/CSU', 'retrieval_strategy': 'single_year'}
10. {'question': 'Was ist die Position von CDU/CSU zum Thema 难民政策, 难民 im Jahr 2024?', 'target_year': '2024', 'target_party': 'CDU/CSU', 'retrieval_strategy': 'single_year'}
11. {'question': 'Was ist die Position von CDU/CSU zum Thema 难民政策, 难民 im Jahr 2025?', 'target_year': '2025', 'target_party': 'CDU/CSU', 'retrieval_strategy': 'single_year'}
12. {'question': 'Wie hat sich die Position von CDU/CSU zum Thema 难民政策, 难民 von 2015 bis 2025 verändert?', 'target_year': None, 'target_party': 'CDU/CSU', 'retrieval_strategy': 'multi_year', 'year_range': ['2015', '2025']}

### 最终答案

Basierend auf den bereitgestellten Materialien lässt sich die Veränderung der Position der CDU/CSU in der Flüchtlingspolitik von 2015 bis 2024 wie folgt analysieren:

**Überblick**
Die Position der CDU/CSU zur Flüchtlingspolitik hat sich von 2015 bis 2024 von einem anfänglichen Ansatz, der humanitäre Hilfe mit dem Ziel der Steuerung und Ordnung verband, zu einer zunehmend restriktiven Haltung entwickelt. Während der Regierungszeit wurden zahlreiche Verschärfungen des Asylrechts umgesetzt. Seit dem Übergang in die Opposition (ab Ende 2021) hat sich die Rhetorik weiter verschärft, mit Forderungen nach einem Stopp der irregulären Migration und der Prüfung von Asylanträgen in Drittstaaten.

**Zeitliche Entwicklung**

• **2015**
  - **Position**: Die Position war geprägt von einer Doppelstrategie: Einerseits sollten Menschen in Not geholfen und die Integration Schutzbedürftiger gesichert werden, andererseits sollte die Zuwanderung geordnet, gesteuert und reduziert werden. Zentrale Forderungen waren die Bekämpfung von Fluchtursachen, eine klare Trennung zwischen Asyl und Arbeitsmigration, die Beschleunigung von Asylverfahren (Asylpaket I) und eine europäische Lösung.
  - **Zitat**: „Zuwanderung ordnen und steuern sowie Fluchtursachen bekämpfen, um so die Zahl der Flüchtlinge zu reduzieren, [...] und zweitens – Menschen in Not zu helfen und die Integration Schutzbedürftiger zu sichern.“ (Barbara Woltmann, 2015-11-11)

• **2016**
  - **Position**: Der Fokus verschob sich klar auf die „massive und dauerhafte Reduzierung der Zuwanderung“. Als Begründung wurde die begrenzte Aufnahme- und Integrationsfähigkeit Deutschlands angeführt. Konkrete Maßnahmen waren die Ausweitung der Liste sicherer Herkunftsstaaten (Maghreb-Staaten), die konsequentere Rückführung und die Aussetzung des Familiennachzugs für subsidiär Schutzberechtigte für zwei Jahre.
  - **Zitat**: „Unser erstes Ziel ist die massive und dauerhafte Reduzierung der Zuwanderung. [...] Unser zweites Ziel ist es, die Kontrolle über die Zuwanderung zu verbessern.“ (Andrea Lindholz, 2016-02-25)

• **2017**
  - **Position**: Die Politik verband humanitäre Verantwortung mit konsequenter Rechtsdurchsetzung. Die Aussetzung des Familiennachzugs wurde mit der Überlastung bei der Integration verteidigt. Weitere Maßnahmen waren die Förderung freiwilliger Rückkehr und die Auswertung von Mobiltelefondaten zur Identitätsfeststellung. Die Begrenzung der Zuwanderung wurde als Voraussetzung für gelingende Integration dargestellt.
  - **Zitat**: „dass man Zuwanderung begrenzen muss, um integrieren zu können.“ (Dr. Astrid Freudenstein, 2017-02-16)

• **2018**
  - **Position**: Der Ansatz der „Steuerung, Ordnung und Begrenzung“ wurde durch konkrete Instrumente untermauert. Dazu zählten die Einrichtung von AnKER-Zentren zur Beschleunigung von Asylverfahren, die erneute Forderung nach Ausweitung sicherer Herkunftsstaaten und ein „Masterplan für Rückführungen“. Das EU-Türkei-Abkommen wurde als Vorbild für weitere Partnerschaften genannt.
  - **Zitat**: „Wer kein Bleiberecht hat, der muss auch wieder gehen. Wer kriminell ist, der hat sein Bleiberecht verwirkt. [...] Wir werden die AnKER-Zentren aufbauen [...]“ (Alexander Dobrindt, 2018-05-16)

• **2019**
  - **Position**: Unter dem Leitbild „Humanität und Ordnung“ wurde die konsequente Abschiebung abgelehnter Asylbewerber als notwendig erachtet, um die Akzeptanz für den Flüchtlingsschutz in der Bevölkerung zu erhalten. Die Einstufung der Maghreb-Staaten und Georgiens als sichere Herkunftsländer blieb eine zentrale Forderung zur Eindämmung von Asylmissbrauch.
  - **Zitat**: „Wer die Akzeptanz in der Bevölkerung für den umfassenden Flüchtlingsschutz aufrechterhalten will, der muss auch dafür sorgen, dass Asylbewerber, die rechtskräftig abgelehnt sind, das Land tatsächlich verlassen und nicht nur in der Theorie“ (Alexander Throm, 2019-06-07)

• **2020**
  - **Position**: Der Fokus lag stark auf einer europäischen Lösung. Kernforderungen waren eine Reform des Gemeinsamen Europäischen Asylsystems (GEAS) mit beschleunigten Grenzverfahren und ein robuster Schutz der EU-Außengrenzen, u.a. durch die Stärkung von Frontex. Die Botschaft, dass die Grenzen nicht wie 2015 geöffnet seien, wurde klar kommuniziert.
  - **Zitat**: „Eine Flucht führt in die Sackgasse; denn 2020 ist nicht 2015...“ (Alexander Throm, 2020-03-04)

• **2021**
  - **Position**: Geprägt durch die Lage an der belarussisch-polnischen Grenze, wurde die Instrumentalisierung von Migranten als „hybride Kriegsführung“ bezeichnet. Die Forderungen konzentrierten sich auf den Schutz der EU-Außengrenzen, die Unterbindung von Sekundärmigration und präventive Kommunikation in den Herkunftsländern.
  - **Zitat**: „Der weißrussische Diktator Lukaschenko benutzt dort verzweifelte Migranten, um die EU zu spalten, und das dürfen wir ihm nicht durchgehen lassen.“ (Andrea Lindholz, 2021-11-11)

• **2022**
  - **Position**: In der Opposition wurde die Kritik an der Ampel-Regierung zum zentralen Element. Deren Politik schaffe falsche Anreize („Koalition der Aufnahmewilligen“). Das „Chancen-Aufenthaltsrecht“ wurde scharf als „Bleiberecht für Täuscher“ abgelehnt und stattdessen eine „Rückführungsoffensive“ sowie Asylverfahren an den Außengrenzen gefordert.
  - **Zitat**: „[Das Chancen-Aufenthaltsrecht ist ein] Bleiberecht für abgelehnte Asylbewerber, die ihre Identität verschleiern.“ (Andrea Lindholz, 2022-09-30)

• **2023**
  - **Position**: Die Lage wurde als akute „Migrationskrise“ beschrieben, die die Kommunen überlaste. Die Forderungen nach einer europäischen Lösung (GEAS-Reform mit Grenzverfahren), der Ausweitung sicherer Herkunftsstaaten und einer konsequenten Rückführungspolitik wurden mit Nachdruck wiederholt. Der Regierung wurde Untätigkeit vorgeworfen.
  - **Zitat**: „Humanität und Ordnung sind kein Gegensatz, sondern zwei Seiten derselben Medaille. [...] Das Asylverfahren dient einzig und alleine [...] dem Schutz von verfolgten Menschen und darf nicht für eine allgemeine Zuwanderung missbraucht werden.“ (Detlef Seif, 2023-03-16)

• **2024**
  - **Position**: Die Rhetorik verschärfte sich weiter mit der Forderung, die „irreguläre Migration zu stoppen“. Als Instrumente wurden konsequente Grenzkontrollen, Zurückweisungen an der Grenze und die Prüfung von Asylanträgen in Drittstaaten gefordert. Das neue EU-Asylrecht (GEAS) wurde als unzureichend kritisiert und Dänemark als Vorbild für eine strengere Politik genannt.
  - **Zitat**: „Wir als CDU/CSU-Bundestagsfraktion fordern daher die Bundesregierung auf, die irreguläre Migration nach Deutschland zu stoppen und klar zwischen Arbeitsmigration und Asyl zu unterscheiden.“ (Florian Oßner, 2024-07-04)

**Hauptveränderungen**

Die Position der CDU/CSU hat sich von einem reaktiven Management der Krise 2015 zu einer proaktiven und zunehmend restriktiven Politik entwickelt.

- **Von**: Einer Doppelstrategie aus humanitärer Hilfe und dem Ziel der Ordnung und Steuerung (2015).
- **Zu**: Einer Forderung nach einem Stopp der irregulären Migration durch Grenzkontrollen, Zurückweisungen und Drittstaatenlösungen (2024).

**Wendepunkte**:
- **2016**: Die explizite Formulierung der „massiven Reduzierung“ als oberstes Ziel und die Umsetzung konkreter Verschärfungen wie die Aussetzung des Familiennachzugs markieren eine klare Kurskorrektur.
- **2021/2022**: Der Übergang in die Opposition führte zu einer deutlichen Verschärfung der Rhetorik. Die Kritik an der Regierungspolitik (z.B. Chancen-Aufenthaltsrecht) und die Rahmung der Situation als permanente „Krise“ wurden zum Kern der Kommunikation.

**Gemeinsamkeiten und Unterschiede**

- **Gemeinsamkeiten**: Über den gesamten Zeitraum hinweg blieben bestimmte Grundpfeiler erhalten: das Bekenntnis zur Bekämpfung von Fluchtursachen, die Forderung nach einer europäischen Lösung und die strikte Trennung zwischen Asylrecht für Schutzbedürftige und Arbeitsmigration. Das Leitmotiv „Humanität und Ordnung“ wurde ebenfalls durchgängig verwendet.
- **Unterschiede**: Das Gleichgewicht zwischen „Humanität“ und „Ordnung“ hat sich massiv verschoben. Während 2015 die humanitäre Komponente noch stark betont wurde, dominiert seit 2016 klar die Forderung nach Ordnung, Begrenzung und Kontrolle. Die vorgeschlagenen Instrumente wurden radikaler: von beschleunigten Verfahren (2015) über AnKER-Zentren (2018) bis hin zu Zurückweisungen an der Grenze und Drittstaatenlösungen (2024).

**Zusammenfassung**
Die Entwicklung der Flüchtlingspolitik der CDU/CSU von 2015 bis 2024 zeigt eine klare Verschiebung hin zu einer restriktiveren Linie. Ausgehend von der Notwendigkeit, die hohe Zuwanderung von 2015 zu steuern, wurden schrittweise die Forderungen und Maßnahmen verschärft. Die anfängliche Doppelstrategie aus Hilfe und Ordnung wich schnell einem Fokus auf Begrenzung und Kontrolle. In der Opposition hat sich diese Tendenz verstärkt, wobei die Partei nun eine grundlegende Neuausrichtung des Asylsystems mit dem Ziel fordert, irreguläre Migration weitestgehend zu unterbinden.

**Quellen**
- Barbara Woltmann (CDU/CSU), 2015-11-11
- Andrea Lindholz (CDU/CSU), 2016-02-25
- Dr. Astrid Freudenstein (CDU/CSU), 2017-02-16
- Alexander Dobrindt (CDU/CSU), 2018-05-16
- Alexander Throm (CDU/CSU), 2019-06-07
- Alexander Throm (CDU/CSU), 2020-03-04
- Andrea Lindholz (CDU/CSU), 2021-11-11
- Andrea Lindholz (CDU/CSU), 2022-09-30
- Detlef Seif (CDU/CSU), 2023-03-16
- Florian Oßner (CDU/CSU), 2024-07-04

---

## 问题 2: 单年多党派对比

**问题**: Welche Positionen vertraten die verschiedenen Parteien im Deutschen Bundestag 2017 zur Reform des Fachkräfteeinwanderungsgesetzes?

### 参数提取

```json
{
  "time_range": {
    "start_year": "2017",
    "end_year": "2017",
    "specific_years": [
      "2017"
    ],
    "time_expression": "2017"
  },
  "parties": [
    "ALL_PARTIES"
  ],
  "topics": [
    "Fachkräfteeinwanderungsgesetz",
    "专业人才移民",
    "移民制度改革"
  ],
  "keywords": [
    "Positionen",
    "Reform",
    "立场",
    "改革"
  ]
}
```

### 检索信息

- **意图**: complex
- **问题类型**: 对比类
- **年份分布**: {}
- **检索文档数**: 50
- **ReRank后文档数**: 1

### 子问题拆解

1. {'question': 'Was ist die Position von ALL_PARTIES im Jahr 2017 zu Fachkräfteeinwanderungsgesetz, 专业人才移民, 移民制度改革?', 'target_year': None, 'target_party': 'ALL_PARTIES', 'retrieval_strategy': 'multi_year'}

### 最终答案

**Zusammenfassung**
Im Jahr 2017 drängten SPD und Bündnis 90/Die Grünen auf eine Reform des Fachkräfteeinwanderungsrechts durch ein neues Gesetz, das unter anderem ein Punktesystem zur Anwerbung qualifizierter Arbeitskräfte vorsah. Die CDU/CSU lehnte dies ab und hielt die bestehenden Regelungen für ausreichend und modern, favorisierte eine Zuwanderung nach konkretem Arbeitsplatzangebot statt nach einem Punktesystem. DIE LINKE kritisierte den Ansatz, Menschen nach ihrer Nützlichkeit zu bewerten, während die AfD die Zuwanderung grundsätzlich als ungeeignete Lösung für demografische Probleme ansah.

**Wichtige Aussagen**

• **Stephan Mayer (CDU/CSU)**:
  „Wir von der CDU/CSU wollen, dass eine Zuwanderung in den Arbeitsmarkt erfolgt und nicht ins Arbeitsamt. [...] wir wollen, dass die Arbeitgeber, die Unternehmer, entscheiden, wer für sie der richtige Mitarbeiter oder die richtige Mitarbeiterin ist, und nicht, dass mittels eines hochkomplexen Punktesystems entschieden wird, wer nach Deutschland kommen darf, ohne dass er einen konkreten Arbeitsvertrag in der Tasche hat.“ (2017-11-22)

• **Sebastian Hartmann (SPD)**:
  Kritisierte die Union dafür, dass sie sich „nicht dazu durchringen konnte, endlich Verantwortung für das Land und eine moderne Einwanderungsgesellschaft zu übernehmen“, und verwies auf einen bereits 2016 von der SPD eingebrachten Gesetzentwurf. (2017-11-22)

• **Katrin Göring-Eckardt (Bündnis 90/Die Grünen)**:
  „Was wir haben, ist schlicht eher eine Ausladung als eine Einladung. [...] Deswegen sage ich Ihnen: Diese Änderung ist, auch wenn wir ökonomisch erfolgreich sein wollen, wenn wir Wachstum wollen, längst überfällig und längst notwendig.“ (2017-06-01)

• **Sevim Dağdelen (DIE LINKE)**:
  „Ein Einwanderungsgesetz, das sich nach der Nützlichkeit der Menschen richtet, in der der einzelne Mensch als Ware ge- und behandelt wird, lehnen wir als Linke ab.“ (2017-06-01)

• **Dr. Gottfried Curio (AfD)**:
  „Migration löst hier das demografische Problem nicht. [...] Die Flutung mit Geringqualifizierten plus geplantem Familiennachzug stabilisiert nicht Arbeitsmarkt und Rentensystem, [...] sondern erhöht Arbeitslosigkeit und Sozialleistungsbezug“. (2017-11-22)

**Belege aus den Materialien**
- **CDU/CSU**: Die Union sah die bestehenden Regelungen zur Fachkräftezuwanderung als „gut“ und „modern“ an und verwies auf positive Bewertungen der OECD (Material 4, 10). Sie lehnte ein neues Einwanderungsgesetz und insbesondere ein Punktesystem ab, da dieses als zu komplex und starr angesehen wurde (Material 1, 4). Stattdessen sollte die Zuwanderung bedarfsgerecht gesteuert werden, indem Arbeitgeber entscheiden, wen sie einstellen (Material 1). Die CDU/CSU betonte, Migration „steuern, zu begrenzen“ zu wollen (Material 9) und das bestehende, teils europäisch geregelte System beizubehalten (Material 5).

- **SPD**: Die SPD warf der CDU/CSU vor, einen bereits im November 2016 von ihr eingebrachten Gesetzentwurf zur „Neuordnung der Einwanderung qualifizierter Fachkräfte“ blockiert zu haben (Material 3). Sie sah die Notwendigkeit, die Einwanderung für eine „moderne Einwanderungsgesellschaft“ neu zu regeln und führte eine Debatte über die Gestaltung der Einwanderung in einem modernen Staat (Material 3, 6).

- **Bündnis 90/Die Grünen**: Die Grünen forderten ein modernes Einwanderungsgesetz, um im internationalen Wettbewerb um Fachkräfte bestehen zu können (Material 12). Sie kritisierten die bestehenden Regelungen als bürokratisch und als „Ausladung“ statt „Einladung“ (Material 11). Ihr Vorschlag umfasste ein Auswahlverfahren über ein Punktesystem und eine „Talentkarte“, die Einwanderern die Einreise zur Jobsuche für ein Jahr ermöglichen sollte (Material 12).

- **DIE LINKE**: Die Linksfraktion lehnte ein Punktesystem und ein Einwanderungsgesetz, das Menschen nach ihrer ökonomischen Nützlichkeit bewertet, fundamental ab (Material 7). Sie argumentierte, dass es keinen pauschalen Fachkräftemangel gäbe, sondern eine Abwanderung gut ausgebildeter Menschen aufgrund schlechter Löhne und Arbeitsbedingungen (Material 7). Stattdessen forderte sie ein sicheres Aufenthaltsrecht für Einwanderer und ihre Familien sowie die Festschreibung sozialer und demokratischer Rechte (Material 13).

- **AfD**: Die AfD vertrat die Position, dass Migration die demografischen Probleme Deutschlands nicht lösen könne. Einwanderung, insbesondere von Geringqualifizierten und der damit verbundene Familiennachzug, würde laut der Partei nicht das Rentensystem stabilisieren, sondern Arbeitslosigkeit und Sozialleistungsbezug erhöhen. Als zielführendere Maßnahme wurde die Erhöhung der Geburtenrate genannt (Material 15).

**Quellen**
- Material 1: Stephan Mayer (Altötting) (CDU/CSU), 2017-11-22
- Material 2: Anita Schäfer (Saalstadt) (CDU/CSU), 2017-06-01
- Material 3: Sebastian Hartmann (SPD), 2017-11-22
- Material 4: Ansgar Heveling (CDU/CSU), 2017-11-22
- Material 5: Vizepräsidentin Claudia Roth (None), 2017-06-01
- Material 6: Vizepräsidentin Claudia Roth (None), 2017-06-01
- Material 7: Sevim Dağdelen (DIE LINKE), 2017-06-01
- Material 8: Dr. Rosemarie Hein (DIE LINKE), 2017-03-24
- Material 9: Nina Warken (CDU/CSU), 2017-06-01
- Material 10: Stephan Mayer (Altötting) (CDU/CSU), 2017-11-22
- Material 11: Katrin Göring-Eckardt (Grüne/Bündnis 90), 2017-06-01
- Material 12: Katrin Göring-Eckardt (Grüne/Bündnis 90), 2017-06-01
- Material 13: Ulla Jelpke (DIE LINKE), 2017-06-01
- Material 14: Nina Warken (CDU/CSU), 2017-06-01
- Material 15: Dr. Gottfried Curio (AfD), 2017-11-22

---

## 问题 3: 单年单党派观点

**问题**: Was waren die Hauptpositionen und Forderungen der Grünen zur Migrationsfrage im Deutschen Bundestag 2015?

### 参数提取

```json
{
  "time_range": {
    "start_year": "2015",
    "end_year": "2015",
    "specific_years": [
      "2015"
    ],
    "time_expression": "2015"
  },
  "parties": [
    "Grüne/Bündnis 90"
  ],
  "topics": [
    "Migrationsfrage",
    "Migration"
  ],
  "keywords": [
    "Hauptpositionen",
    "Forderungen"
  ]
}
```

### 检索信息

- **意图**: simple
- **问题类型**: None
- **年份分布**: {}
- **检索文档数**: 25
- **ReRank后文档数**: 1

### 最终答案

Basierend auf den bereitgestellten Materialien lassen sich die Hauptpositionen und Forderungen der Grünen zur Migrationsfrage im Deutschen Bundestag 2015 wie folgt zusammenfassen:

**Zusammenfassung**
Die Grünen positionierten Deutschland 2015 als modernes Einwanderungsland und forderten ein umfassendes Einwanderungsgesetz, um die Zuwanderung von Fachkräften zu steuern. Sie setzten sich vehement für die Schaffung sicherer und legaler Fluchtwege ein, unter anderem durch Resettlement-Programme, humanitäre Visa und eine unbürokratische Familienzusammenführung. Integration wurde als gesamtgesellschaftliche Aufgabe verstanden, die durch einen "nationalen Flüchtlingspakt", eine Bildungsoffensive und einen erleichterten Arbeitsmarktzugang für Geflüchtete und Asylbewerber gestaltet werden sollte. Gleichzeitig forderten sie einen Abschiebestopp für Länder wie Afghanistan und kritisierten Verschärfungen im Asylrecht, die rechtsstaatliche Standards untergraben.

**Wichtige Aussagen**

• **Katrin Göring-Eckardt (Grüne/Bündnis 90)**:
  „Deutschland braucht pro Jahr 300 000 Einwanderer. Das sagen alle Experten übereinstimmend. Wir brauchen ein echtes Einwanderungsgesetz und kein Einwanderungsverhinderungsgesetz.“ (Material 2, 2015-02-05)

• **Luise Amtsberg (Grüne/Bündnis 90)**:
  „Meine Fraktion fordert angesichts der Sicherheitslage in Afghanistan einen Abschiebestopp für afghanische Staatsangehörige sowie das Einvernehmen des Bundesministeriums des Innern für die Erteilung einer Aufenthaltserlaubnis nach § 23 Absatz 1 des Aufenthaltsgesetzes.“ (Material 4, 2015-12-03)

• **Claudia Roth (Augsburg) (Grüne/Bündnis 90)**:
  Forderte „eine umfassende Seenotrettung im ganzen Mittelmeer“, „sichere, legale Fluchtwege nach Europa“, „humanitäre Visa“, eine „deutliche Aufstockung des Resettlement-Programms und eine unbürokratische Familienzusammenführung“ sowie „europäische Solidarität bei der Aufnahme von mehr Flüchtlingen“. (Material 10, 2015-05-07)

• **Kai Gehring (Grüne/Bündnis 90)**:
  „Bildung und Qualifizierung sind zentralste Schlüssel, Integration wirklich zu schaffen. [...] Es braucht eine breite Bildungsoffensive: frühkindlich, schulisch, beruflich und hochschulisch.“ (Material 7, 2015-11-05)

**Belege aus den Materialien**

- **Einwanderungsgesetz und Fachkräftezuwanderung**: Die Grünen forderten wiederholt ein modernes Einwanderungsgesetz, um Deutschland als Einwanderungsland zu gestalten und dem Fachkräftemangel entgegenzuwirken (Material 2, 6). Volker Beck sprach sich für eine "zirkuläre Migration" aus, um hochqualifizierten Arbeitskräften die Rückkehr nach Deutschland zu erleichtern (Material 3).

- **Integration als gesamtgesellschaftliche Aufgabe**: Katrin Göring-Eckardt forderte einen "nationalen Flüchtlingspakt" unter Einbeziehung aller gesellschaftlichen Akteure (Material 1). Kerstin Andreae schlug ein "Bündnis für Integration" vor, um die Herausforderung in eine Chance für Wirtschaft und Gesellschaft zu verwandeln (Material 9). Ein zentraler Baustein war die Integration durch Bildung, wofür Kai Gehring eine "breite Bildungsoffensive" und einen schnelleren Zugang zu BAföG und Stipendien für Flüchtlinge verlangte (Material 7, 11).

- **Arbeitsmarktintegration**: Volker Beck forderte die Möglichkeit eines "Statuswechsels", damit Asylbewerber, Geduldete, Studierende oder Auszubildende eine Arbeit aufnehmen können, wenn sie auf dem Arbeitsmarkt gebraucht werden (Material 3).

- **Legale und sichere Fluchtwege**: Um das Sterben im Mittelmeer zu beenden, forderten die Grünen die Schaffung legaler Zugangswege. Konkret wurden die Aufstockung des Syrien-Kontingents, mehr Personal in Botschaften zur Beschleunigung der Familienzusammenführung und ein höheres Resettlement-Kontingent genannt (Material 8). Claudia Roth ergänzte die Forderungen um humanitäre Visa und eine umfassende Seenotrettung (Material 10).

- **Abschiebung und Asylverfahren**: Luise Amtsberg forderte einen Abschiebestopp für afghanische Staatsangehörige aufgrund der dortigen Sicherheitslage (Material 4). Dr. Konstantin von Notz befürwortete zwar schnellere Asylverfahren, lehnte aber eine Absenkung rechtsstaatlicher Standards ab und kritisierte Teile des Asylpakets als "verfassungsrechtlich problematisch" (Material 14). Zudem wurde die mangelnde staatliche Fürsorge für unbegleitete minderjährige Flüchtlinge kritisiert (Material 5).

- **Ablehnung von Abschottung**: Die Grünen sprachen sich klar gegen die Errichtung von Zäunen an deutschen Grenzen aus und kritisierten solche Vorschläge als populistisch und rechtswidrig (Material 15).

**Quellen**
- Material 1: Redner: Katrin Göring-Eckardt (Grüne/Bündnis 90), 2015-09-09
- Material 2: Redner: Katrin Göring-Eckardt (Grüne/Bündnis 90), 2015-02-05
- Material 3: Redner: Volker Beck (Köln) (Grüne/Bündnis 90), 2015-02-05
- Material 4: Redner: Luise Amtsberg (Grüne/Bündnis 90), 2015-12-03
- Material 5: Redner: Beate Walter-Rosenheimer (Grüne/Bündnis 90), 2015-03-05
- Material 6: Redner: Kerstin Andreae (Grüne/Bündnis 90), 2015-01-29
- Material 7: Redner: Kai Gehring (Grüne/Bündnis 90), 2015-11-05
- Material 8: Redner: Luise Amtsberg (Grüne/Bündnis 90), 2015-04-22
- Material 9: Redner: Kerstin Andreae (Grüne/Bündnis 90), 2015-11-26
- Material 10: Redner: Claudia Roth (Augsburg) (Grüne/Bündnis 90), 2015-05-07
- Material 11: Redner: Kai Gehring (Grüne/Bündnis 90), 2015-05-21
- Material 12: Redner: Dr. Gerhard Schick (Grüne/Bündnis 90), 2015-07-17
- Material 13: Redner: Anja Hajduk (Grüne/Bündnis 90), 2015-11-05
- Material 14: Redner: Dr. Konstantin von Notz (Grüne/Bündnis 90), 2015-10-15
- Material 15: Redner: Beate Walter-Rosenheimer (Grüne/Bündnis 90), 2015-10-02

---

## 问题 4: 跨年多党派变化

**问题**: Wie haben sich die Diskussionen der verschiedenen Parteien im Deutschen Bundestag über die Familienzusammenführung von Flüchtlingen zwischen 2015 und 2018 entwickelt?

### 参数提取

```json
{
  "time_range": {
    "start_year": "2015",
    "end_year": "2018",
    "specific_years": [
      "2015",
      "2016",
      "2017",
      "2018"
    ],
    "time_expression": "zwischen 2015 und 2018"
  },
  "parties": [
    "ALL_PARTIES"
  ],
  "topics": [
    "Familienzusammenführung",
    "Flüchtlinge"
  ],
  "keywords": [
    "Diskussionen",
    "entwickelt"
  ]
}
```

### 检索信息

- **意图**: complex
- **问题类型**: 趋势分析
- **年份分布**: {}
- **检索文档数**: 18
- **ReRank后文档数**: 1

### 最终答案

**Zusammenfassung**
Die Diskussionen über die Familienzusammenführung von Flüchtlingen im Bundestag entwickelten sich zwischen 2016 und 2018 von einer Aussetzung hin zu einer Neuregelung mit Kontingenten. 2016 setzte die Große Koalition den Familiennachzug für subsidiär Schutzberechtigte für zwei Jahre aus, was die CDU/CSU mit begrenzten Aufnahmekapazitäten begründete. Während Grüne und Linke diese Regelung als unmenschlich kritisierten und ihre Aufhebung forderten, mündete die Debatte 2018 in einem Kompromiss, der den Rechtsanspruch abschaffte und durch ein monatliches Kontingent von 1.000 Personen ersetzte, was von der AfD als unzureichend und von den Grünen als weiterhin unzureichend humanitär kritisiert wurde.

**Wichtige Aussagen**

• **Thomas Strobl (CDU/CSU)**: „Wir schränken den Familiennachzug für subsidiär Schutzberechtigte im Übrigen nicht aus Hartherzigkeit ein, sondern aus der Einsicht in die Grenzen unserer Möglichkeiten.“ (19.02.2016)

• **Katja Dörner (BÜNDNIS 90/DIE GRÜNEN)**: „Wir sagen: Eltern gehören zu ihren Kindern. Familien gehören zusammen, auch und gerade, wenn sie vor Krieg, Terror und Unsicherheit fliehen mussten.“ (01.06.2017)

• **Dr. Stephan Harbarth (CDU/CSU)**: „Für CDU und für CSU ist Flüchtlingsschutz zunächst und vor allem Schutz auf Zeit, und der Familiennachzug muss sich dabei nach unseren Aufnahmemöglichkeiten richten.“ (19.01.2018)

• **Dr. Christian Wirth (AfD)**: „Die AfD beantragt den Wegfall des Anspruchs auf Nachzug der Familienangehörigen von subsidiär schutzberechtigten Migranten.“ (01.02.2018)

• **Stephan Mayer (CDU/CSU)**: „Wir schaffen ab dem 1. August 2018 eine Neuregelung, die ein monatliches Kontingent von 1 000 Personen für den Familiennachzug vorsieht.“ (01.02.2018)

• **Linda Teuteberg (FDP)**: „Familiennachzug findet statt, und zwar in erheblichem Umfang. [...] Als Angehörige von Menschen, die hier politisches Asyl erhalten haben, oder als Flüchtlinge, die nach der Genfer Flüchtlingskonvention anerkannt sind. Das ist gut so, und das ist ein enormer humanitärer Kraftakt, den dieses Land bereits leistet.“ (07.06.2018)

**Belege aus den Materialien**
- **2016: Aussetzung des Familiennachzugs für subsidiär Schutzberechtigte**: Die CDU/CSU begründete die im Rahmen der Asylrechtsreform beschlossene zweijährige Aussetzung des Familiennachzugs für subsidiär Schutzberechtigte mit der Notwendigkeit, die Zuwanderung zu steuern und die Aufnahmekapazitäten Deutschlands nicht zu überfordern. Redner wie Thomas Strobl (CDU/CSU) betonten am 19.02.2016, dass man die Zahlen nicht durch Familiennachzug „verdoppeln oder verdreifachen“ könne (Material 4). Andrea Lindholz (CDU/CSU) stellte am 10.11.2016 klar, dass es explizit um subsidiär Geschützte gehe, nicht um anerkannte Flüchtlinge nach der Genfer Konvention oder dem Grundgesetz (Material 5). Dr. Stephan Harbarth (CDU/CSU) wies am 22.11.2016 darauf hin, dass diese Aussetzung im März 2018 auslaufen und die alte Rechtslage wieder in Kraft treten würde (Material 1).

- **2017: Kritik und Forderung nach Wiederaufnahme**: Bündnis 90/Die Grünen und Die Linke kritisierten die Aussetzung scharf. Katja Dörner (Grüne) warf der Regierungskoalition am 01.06.2017 vor, sich vor einer Entscheidung zu „ducken“ und einen „unmenschlicher Umgang mit den Geflüchteten“ zu pflegen (Material 11). Sie argumentierte, dass Familien zusammengehörten und die bestehende Härtefallregelung bürokratisch und wirkungslos sei (Material 9).

- **2018: Neuregelung durch ein Kontingent**: Mit dem bevorstehenden Auslaufen der Aussetzung einigte sich die Große Koalition auf eine Neuregelung. Stephan Mayer (CDU/CSU) erläuterte am 01.02.2018, dass der individuelle Rechtsanspruch auf Familiennachzug für subsidiär Schutzberechtigte abgeschafft und ab dem 1. August 2018 durch ein monatliches Kontingent von 1.000 Personen sowie eine Härtefallregelung ersetzt werde (Material 8).

- **Positionen der Opposition zur Neuregelung 2018**: Die AfD lehnte diese Regelung als unzureichend ab und forderte die vollständige Abschaffung des Familiennachzugs für diese Gruppe. Dr. Christian Wirth (AfD) schlug am 01.02.2018 stattdessen Familienzusammenführungen in „Schutzzonen in Syrien“ vor (Material 2). Die FDP, vertreten durch Linda Teuteberg am 07.06.2018, betonte, dass der Familiennachzug für anerkannte Flüchtlinge nach der Genfer Konvention weiterhin in großem Umfang stattfinde und ein Grundrecht sei. Sie kritisierte, dass die Debatte von manchen fälschlicherweise so dargestellt werde, als ginge es um den Familiennachzug für alle Flüchtlinge (Material 3).

**Quellen**
- Material 1: Dr. Stephan Harbarth (CDU/CSU), 2016-11-22
- Material 2: Dr. Christian Wirth (AfD), 2018-02-01
- Material 3: Linda Teuteberg (FDP), 2018-06-07
- Material 4: Thomas Strobl (Heilbronn) (CDU/CSU), 2016-02-19
- Material 5: Andrea Lindholz (CDU/CSU), 2016-11-10
- Material 6: Swen Schulz (Spandau) (SPD), 2015-01-15
- Material 7: Dr. Stephan Harbarth (CDU/CSU), 2018-01-19
- Material 8: Stephan Mayer (Altötting) (CDU/CSU), 2018-02-01
- Material 9: Katja Dörner (Grüne/Bündnis 90), 2017-06-01
- Material 10: Luise Amtsberg (BÜNDNIS 90/DIE GRÜNEN), 2017-12-13
- Material 11: Katja Dörner (Grüne/Bündnis 90), 2017-06-01
- Material 12: Dr. Christian Wirth (AfD), 2018-02-01
- Material 13: Stephan Mayer (Altötting) (CDU/CSU), 2017-06-01
- Material 14: Kerstin Griese (SPD), 2017-02-16
- Material 15: Sylvia Pantel (CDU/CSU), 2016-09-08

---

## 问题 5: 跨年两党对比

**问题**: Bitte vergleichen Sie die Positionen der Unionsparteien und der Grünen zur Integrationspolitik zwischen 2015 und 2017.

### 参数提取

```json
{
  "time_range": {
    "start_year": "2015",
    "end_year": "2017",
    "specific_years": [
      "2015",
      "2016",
      "2017"
    ],
    "time_expression": "zwischen 2015 und 2017"
  },
  "parties": [
    "CDU/CSU",
    "Grüne/Bündnis 90"
  ],
  "topics": [
    "融合政策",
    "Integrationspolitik"
  ],
  "keywords": [
    "比较",
    "立场"
  ]
}
```

### 检索信息

- **意图**: complex
- **问题类型**: 对比类
- **年份分布**: {}
- **检索文档数**: 117
- **ReRank后文档数**: 9

### 子问题拆解

1. {'question': 'Was sind die Position und Hauptansichten von CDU/CSU 2015zu 融合政策, Integrationspolitik?', 'target_year': None, 'target_party': 'CDU/CSU', 'retrieval_strategy': 'multi_year'}
2. {'question': 'Was sind die Position und Hauptansichten von Grüne/Bündnis 90 2015zu 融合政策, Integrationspolitik?', 'target_year': None, 'target_party': 'Grüne/Bündnis 90', 'retrieval_strategy': 'multi_year'}
3. {'question': 'Was sind die Position und Hauptansichten von CDU/CSU 2016zu 融合政策, Integrationspolitik?', 'target_year': None, 'target_party': 'CDU/CSU', 'retrieval_strategy': 'multi_year'}
4. {'question': 'Was sind die Position und Hauptansichten von Grüne/Bündnis 90 2016zu 融合政策, Integrationspolitik?', 'target_year': None, 'target_party': 'Grüne/Bündnis 90', 'retrieval_strategy': 'multi_year'}
5. {'question': 'Was sind die Position und Hauptansichten von CDU/CSU 2017zu 融合政策, Integrationspolitik?', 'target_year': None, 'target_party': 'CDU/CSU', 'retrieval_strategy': 'multi_year'}
6. {'question': 'Was sind die Position und Hauptansichten von Grüne/Bündnis 90 2017zu 融合政策, Integrationspolitik?', 'target_year': None, 'target_party': 'Grüne/Bündnis 90', 'retrieval_strategy': 'multi_year'}
7. {'question': 'Was sind die Hauptunterschiede zwischen CDU/CSU und Grüne/Bündnis 90 2015zu 融合政策, Integrationspolitik?', 'target_year': None, 'target_party': 'CDU/CSU', 'retrieval_strategy': 'multi_year'}
8. {'question': 'Was sind die Hauptunterschiede zwischen CDU/CSU und Grüne/Bündnis 90 2016zu 融合政策, Integrationspolitik?', 'target_year': None, 'target_party': 'CDU/CSU', 'retrieval_strategy': 'multi_year'}
9. {'question': 'Was sind die Hauptunterschiede zwischen CDU/CSU und Grüne/Bündnis 90 2017zu 融合政策, Integrationspolitik?', 'target_year': None, 'target_party': 'CDU/CSU', 'retrieval_strategy': 'multi_year'}

### 最终答案

Basierend auf den bereitgestellten Materialien wird hier ein Vergleich der Positionen der Unionsparteien (CDU/CSU) und Bündnis 90/Die Grünen zur Integrationspolitik im Zeitraum 2015 bis 2017 erstellt.

**Überblick**
Der Vergleich der Positionen von CDU/CSU und Bündnis 90/Die Grünen zur Integrationspolitik zwischen 2015 und 2017 offenbart einen fundamentalen Dissens in der Herangehensweise. Während die Union auf einen Ansatz von "Ordnen, Steuern und Begrenzen" setzte, bei dem Integrationsleistungen an eine gute Bleibeperspektive und die Erfüllung von Pflichten geknüpft sind, plädierten die Grünen für eine offene, angebotsorientierte Politik, die allen Geflüchteten von Anfang an Zugang zu Bildung und Teilhabe ermöglichen soll.

**Positionen der einzelnen Akteure**

• **CDU/CSU**
  **Position:** Die Integrationspolitik der Union basierte auf dem Prinzip "Fordern und Fördern". Erfolgreiche Integration wurde als notwendig für den gesellschaftlichen Frieden und die Wettbewerbsfähigkeit Deutschlands angesehen, jedoch unter die Bedingung gestellt, dass die Zuwanderung gesteuert und begrenzt wird. Integrationsmaßnahmen sollten sich auf Personen mit guter Bleibeperspektive konzentrieren, während für alle anderen die Ausreisepflicht im Vordergrund stand.
  **Kernargumente:**
  - **Steuerung und Begrenzung:** Integration kann nur gelingen, wenn die Zahl der Zuwanderer reduziert und kontrolliert wird, um die Aufnahme- und Integrationskapazitäten des Landes nicht zu überfordern.
  - **Differenzierung und Verbindlichkeit:** Integrationsleistungen müssen gezielt für Schutzbedürftige mit Bleiberecht eingesetzt werden. Integration ist ein zweiseitiger Prozess ("Geben und Nehmen"), der die Anerkennung deutscher Gesetze und Werte verbindlich einfordert.
  **Zitat:** „Für uns in der CSU war von Anfang an klar und ist auch heute noch klar, dass der Dreiklang aus erstens Humanität, zweitens Begrenzung und drittens Integration gleichwertig gilt.“ – Gerda Hasselfeldt (CDU/CSU), 07.09.2016

• **Bündnis 90/Die Grünen**
  **Position:** Die Grünen sahen Integration als eine zentrale gesellschaftliche Aufgabe, die durch eine proaktive Investitions- und Bildungspolitik bewältigt werden muss. Sie forderten einen sofortigen und undifferenzierten Zugang zu Bildung, Sprachkursen und dem Arbeitsmarkt für alle Geflüchteten, unabhängig von Herkunft und Bleibeperspektive. Die Politik der Regierung wurde als von Misstrauen geprägt, bürokratisch und zu stark auf Abschottung fokussiert kritisiert.
  **Kernargumente:**
  - **Universeller Zugang zu Bildung und Arbeit:** Bildungspolitik wird als Integrationspolitik verstanden. Alle Geflüchteten sollen von Anfang an das Recht auf Bildung und Ausbildung haben, da dies der Schlüssel zu gesellschaftlicher Teilhabe ist.
  - **Angebotsorientierte Politik statt Sanktionen:** Statt auf administrative Hürden und Pflichten (wie die Wohnsitzauflage im Integrationsgesetz) zu setzen, fordern die Grünen Investitionen in Infrastruktur und ein modernes, potenzialorientiertes Einwanderungsgesetz.
  **Zitat:** „Statt über unsinnige und gesetzeswidrige Obergrenzen zu diskutieren, brauchen wir jetzt eine konsequente und sofortige Bildungsoffensive; denn Bildungspolitik ist Integrationspolitik.“ – Özcan Mutlu (Grüne/Bündnis 90), 29.01.2016

**Vergleichstabelle**

| Aspekt | CDU/CSU | Bündnis 90/Die Grünen |
| :--- | :--- | :--- |
| **Grundprinzip** | "Fordern und Fördern"; Integration ist an die Bedingung der Steuerung und Begrenzung der Zuwanderung geknüpft. | "Integration durch Teilhabe"; Integration ist eine gesellschaftliche Aufgabe, die durch Investitionen und offene Angebote für alle gelöst wird. |
| **Zielgruppe der Integration** | Konzentration auf Schutzbedürftige mit guter Bleibeperspektive. | Alle Geflüchteten von Anfang an, unabhängig von Herkunft und Bleibeperspektive. |
| **Schlüsselmaßnahmen** | Integrationsgesetz (mit Pflichten wie Wohnsitzauflage), Ausbau von Sprachkursen, klare Trennung von Asyl und Arbeitsmigration. | "Sofortige Bildungsoffensive", früher Zugang zu Arbeitsmarkt und Sprachkursen, modernes Einwanderungsgesetz. |
| **Obergrenze/Begrenzung** | Zentrale Forderung zur Sicherung der Integrationsfähigkeit. | Strikte Ablehnung als "unsinnig und gesetzeswidrig". |
| **Sichere Herkunftsländer** | Befürwortung der Einstufung (z.B. Balkanstaaten) zur Beschleunigung der Verfahren. | Ablehnung bzw. "Blockadehaltung" (laut CDU/CSU). |
| **Abschiebung/Rückführung** | Betonung der Ausreisepflicht für Personen ohne Bleiberecht. | Kritik an der Fokussierung der Regierung auf Abschiebungen statt auf Integration. |

**Gemeinsamkeiten**
- **Bedeutung der Integration:** Beide Parteien erkannten die Integration von Zuwanderern als eine zentrale und notwendige Aufgabe für die deutsche Gesellschaft an. Cemile Giousouf (CDU/CSU) nannte sie am 02.10.2015 ein "nationales Interesse", während die Grünen sie als Kern ihrer Politik definierten.
- **Schlüsselbereiche Sprache und Arbeit:** Beide Seiten identifizierten Sprachkenntnisse und die Integration in den Arbeitsmarkt als entscheidende Faktoren für eine gelingende Integration.
- **Fluchtursachenbekämpfung:** Beide Fraktionen nannten die Bekämpfung von Fluchtursachen als ein wichtiges Ziel, auch wenn die konkreten Ansätze sich unterschieden.

**Unterschiede**
- **Prinzip der Begrenzung vs. Prinzip der Offenheit:** Der fundamentalste Unterschied lag in der Haltung zur Begrenzung der Zuwanderung. Die CDU/CSU sah dies als zwingende Voraussetzung für Integration, während die Grünen Obergrenzen strikt ablehnten.
- **Selektive vs. Universelle Integrationsangebote:** Die CDU/CSU wollte Integrationsmaßnahmen gezielt auf Personen mit hoher Bleibeperspektive konzentrieren. Die Grünen forderten hingegen einen universellen Zugang für alle Geflüchteten von Beginn an, was Beate Walter-Rosenheimer (Grüne) am 09.06.2016 mit den Worten unterstrich: "Dieses Recht gilt für alle, auch für Geflüchtete, egal woher sie kommen."
- **Pflichtenorientierter vs. Angebotsorientierter Ansatz:** Die Union betonte mit dem Integrationsgesetz die Pflichten der Zuwanderer ("Fordern"). Die Grünen kritisierten dies als "administratives Monster" (Volker Beck, 03.06.2016) und forderten eine angebotsorientierte Politik, die auf Investitionen und den Abbau von Hürden setzt.
- **Haltung zu sicheren Herkunftsländern:** Die CDU/CSU warf den Grünen eine "Blockadehaltung" bei der Einstufung der Balkanstaaten als sichere Herkunftsländer vor (Kai Whittaker, 11.06.2015), was einen klaren politischen Konfliktpunkt darstellte.

**Zusammenfassung**
Die Positionen von CDU/CSU und Bündnis 90/Die Grünen zur Integrationspolitik zwischen 2015 und 2017 waren von gegensätzlichen politischen Philosophien geprägt. Die Union verfolgte einen pragmatischen, kontrollorientierten Ansatz, der auf Steuerung, Begrenzung und die Erfüllung von Pflichten setzte. Demgegenüber stand der idealistischere, rechtebasierte Ansatz der Grünen, der auf universelle Teilhabe, Investitionen in Bildung und eine offene Gesellschaft abzielte. Diese tiefgreifenden Unterschiede in den Grundprinzipien führten zu unvereinbaren Positionen bei konkreten Maßnahmen wie dem Integrationsgesetz, der Frage der Obergrenze und der Einstufung sicherer Herkunftsländer.

**Quellen**
- Alois Rainer (CDU/CSU), 2015-11-26
- Andrea Lindholz (CDU/CSU), 2015-11-12
- Andrea Lindholz (CDU/CSU), 2016-02-25
- Ansgar Heveling (CDU/CSU), 2017-11-22
- Barbara Woltmann (CDU/CSU), 2015-11-11
- Beate Walter-Rosenheimer (Grüne/Bündnis 90), 2016-06-09
- Brigitte Pothmer (Grüne/Bündnis 90), 2015-11-12
- Brigitte Pothmer (Grüne/Bündnis 90), 2016-03-17
- Cemile Giousouf (CDU/CSU), 2015-10-02
- Cemile Giousouf (CDU/CSU), 2016-02-25
- Dieter Janecek (Grüne/Bündnis 90), 2016-06-02
- Doris Wagner (Grüne/Bündnis 90), 2017-03-24
- Dr. Gerhard Schick (Grüne/Bündnis 90), 2015-07-17
- Dr. Konstantin von Notz (Grüne/Bündnis 90), 2016-02-19
- Dr. Stephan Harbarth (CDU/CSU), 2016-12-16
- Dr. Volker Ullrich (CDU/CSU), 2017-01-19
- Dr. Wolfgang Strengmann-Kuhn (Grüne/Bündnis 90), 2017-02-16
- Dr. Wolfgang Strengmann-Kuhn (Grüne/Bündnis 90), 2017-05-17
- Erika Steinbach (CDU/CSU), 2016-02-19
- Gerda Hasselfeldt (CDU/CSU), 2016-09-07
- Iris Ripsam (CDU/CSU), 2017-05-18
- Jutta Eckenbach (CDU/CSU), 2016-03-17
- Kai Gehring (Grüne/Bündnis 90), 2016-11-24
- Kai Whittaker (CDU/CSU), 2015-06-11
- Katrin Göring-Eckardt (Grüne/Bündnis 90), 2016-09-07
- Katrin Göring-Eckardt (Grüne/Bündnis 90), 2017-06-01
- Mark Helfrich (CDU/CSU), 2017-02-16
- Martin Patzelt (CDU/CSU), 2016-04-28
- Nina Warken (CDU/CSU), 2017-06-01
- Özcan Mutlu (Grüne/Bündnis 90), 2016-01-29
- Özcan Mutlu (Grüne/Bündnis 90), 2017-06-22
- Peter Meiwald (Grüne/Bündnis 90), 2015-11-25
- Stephan Mayer (Altötting) (CDU/CSU), 2015-02-05
- Stephan Mayer (Altötting) (CDU/CSU), 2017-11-22
- Uda Heller (CDU/CSU), 2016-01-29
- Uda Heller (CDU/CSU), 2016-06-09
- Ulrich Lange (CDU/CSU), 2017-03-24
- Ute Bertram (CDU/CSU), 2016-12-16
- Uwe Schummer (CDU/CSU), 2017-06-22
- Volker Beck (Köln) (Grüne/Bündnis 90), 2015-11-11
- Volker Beck (Köln) (Grüne/Bündnis 90), 2016-02-25
- Volker Beck (Köln) (Grüne/Bündnis 90), 2016-06-03

---

## 问题 6: 离散年份对比

**问题**: Wie haben sich die Positionen der CDU/CSU zur Migrationspolitik zwischen 2017 und 2019 im Vergleich verändert?

### 参数提取

```json
{
  "time_range": {
    "start_year": "2017",
    "end_year": "2019",
    "specific_years": [
      "2017",
      "2019"
    ],
    "time_expression": "zwischen 2017 und 2019 im Vergleich"
  },
  "parties": [
    "CDU/CSU"
  ],
  "topics": [
    "Migrationspolitik"
  ],
  "keywords": [
    "Positionen",
    "verändert",
    "Vergleich"
  ]
}
```

### 检索信息

- **意图**: complex
- **问题类型**: 变化类
- **年份分布**: {}
- **检索文档数**: 100
- **ReRank后文档数**: 2

### 子问题拆解

1. {'question': 'Was ist die Position von CDU/CSU zum Thema Migrationspolitik im Jahr 2017?', 'target_year': '2017', 'target_party': 'CDU/CSU', 'retrieval_strategy': 'single_year'}
2. {'question': 'Was ist die Position von CDU/CSU zum Thema Migrationspolitik im Jahr 2019?', 'target_year': '2019', 'target_party': 'CDU/CSU', 'retrieval_strategy': 'single_year'}

### 最终答案

Basierend auf den bereitgestellten Materialien lässt sich die Veränderung der Positionen der CDU/CSU zur Migrationspolitik zwischen 2017 und 2019 wie folgt analysieren:

**Überblick**
Die migrationspolitische Position der CDU/CSU zeigte zwischen 2017 und 2019 eine hohe Kontinuität in ihren Grundprinzipien, insbesondere bei der Steuerung und Begrenzung von Migration sowie der Trennung von Asyl und Arbeitsmigration. Die Entwicklung von 2017 zu 2019 ist vor allem durch eine Konkretisierung und legislative Umsetzung dieser Prinzipien gekennzeichnet. Der Fokus verschob sich von der Formulierung von Zielen hin zur Schaffung konkreter gesetzlicher Instrumente, was sich auch in einer geschärften Rhetorik unter dem Leitmotiv „Humanität und Ordnung“ widerspiegelt.

**Zeitliche Entwicklung**

• **2017**
  - **Position**: Die CDU/CSU befürwortet eine staatlich gesteuerte und begrenzte Migration. Im Zentrum steht die klare Trennung zwischen Asyl für Schutzbedürftige und einer bedarfsorientierten Zuwanderung von Fachkräften. Wichtige Forderungen sind die konsequente Durchsetzung der Ausreisepflicht, die Ablehnung pauschaler Abschiebestopps, die Ausweitung sicherer Herkunftsländer und die Bekämpfung von Fluchtursachen. Die Notwendigkeit eines Fachkräftezuwanderungsgesetzes wird formuliert, um Zuwanderung gezielt in den Arbeitsmarkt zu lenken.
  - **Zitat**: „Daher kann man die Migration nicht der individuellen Entscheidung der Migranten überlassen; sie muss von den Staaten gesteuert werden.“ (Ansgar Heveling, 2017-11-22)

• **2019**
  - **Position**: Die Politik der CDU/CSU wird unter dem Leitsatz „Humanität und Ordnung“ zusammengefasst. Dieser Ansatz wird durch ein Gesetzespaket konkretisiert: das Fachkräfteeinwanderungsgesetz zur Förderung erwünschter Zuwanderung und das „Geordnete-Rückkehr-Gesetz“ zur konsequenten Durchsetzung von Abschiebungen. Die Notwendigkeit von Rückführungen wird als essenziell für die Akzeptanz des Asylsystems in der Bevölkerung dargestellt. Die Forderung nach der Einstufung weiterer sicherer Herkunftsstaaten wird mit Nachdruck wiederholt und die Blockade durch andere Parteien scharf kritisiert.
  - **Zitat**: Thorsten Frei (CDU/CSU) beschreibt das Fachkräfteeinwanderungsgesetz und das Gesetz zur besseren Durchsetzung der Ausreisepflicht als „zwei Seiten einer Medaille“ einer in sich konsistenten Einwanderungspolitik (2019-05-09).

**Hauptveränderungen**

1.  **CDU/CSU**:
    *   **Von der Planung zur Umsetzung**: Während 2017 die Notwendigkeit eines Fachkräftezuwanderungsgesetzes betont wurde, wurde dieses 2019 als Teil eines umfassenden Gesetzespakets verabschiedet. Die Politik verlagerte sich von der Konzeption zur konkreten legislative Umsetzung.
    *   **Rhetorische Schärfung**: Die Einführung des Slogans „Humanität und Ordnung“ im Jahr 2019 dient dazu, die zwei Säulen der Politik – Schutzgewährung und konsequente Rückführung – als untrennbar und sich gegenseitig bedingend darzustellen. Die Notwendigkeit von Abschiebungen wird expliziter mit dem Erhalt der gesellschaftlichen Akzeptanz für das Asylrecht begründet.
    *   **Wendepunkt**: Der entscheidende Wendepunkt war die Verabschiedung des Migrationspakets 2019. Dieses Paket, insbesondere das Fachkräfteeinwanderungsgesetz und das „Geordnete-Rückkehr-Gesetz“, institutionalisierte die seit 2017 formulierten Ziele und schuf die rechtlichen Instrumente für deren Durchsetzung.

**Gemeinsamkeiten und Unterschiede**
- **Gemeinsamkeiten**: Über beide Jahre hinweg blieben die Kernforderungen der CDU/CSU konstant: die Steuerung und Begrenzung der Zuwanderung, die klare Trennung von Asyl und Arbeitsmigration, die konsequente Rückführung abgelehnter Asylbewerber, die Bekämpfung von Fluchtursachen und der Ruf nach einer europäischen Lösung.
- **Unterschiede**: Der Hauptunterschied liegt in der Konkretisierung und im Fokus. 2017 lag der Schwerpunkt auf der Begründung der Notwendigkeit von Steuerung und Begrenzung. 2019 verlagerte sich der Fokus auf die Umsetzung und Rechtfertigung konkreter, teils restriktiver Maßnahmen („Ordnung“), die als notwendige Ergänzung zur humanitären Schutzgewährung („Humanität“) dargestellt wurden. Die politische Auseinandersetzung, etwa um sichere Herkunftsstaaten, wurde konfrontativer geführt.

**Zusammenfassung**
Die Position der CDU/CSU zur Migrationspolitik hat sich zwischen 2017 und 2019 nicht grundlegend gewandelt, sondern in ihrer Ausgestaltung und ihrem Fokus weiterentwickelt. Die 2017 formulierten Prinzipien der Steuerung, Begrenzung und Trennung von Asyl und Arbeitsmigration wurden 2019 in ein kohärentes Gesetzespaket gegossen. Die Rhetorik wurde unter dem Leitmotiv „Humanität und Ordnung“ geschärft, um die Notwendigkeit von restriktiven Maßnahmen wie Abschiebungen als Voraussetzung für die Aufrechterhaltung eines funktionierenden und akzeptierten Asylsystems zu legitimieren.

**Quellen**
- Andrea Lindholz (CDU/CSU), 2017-04-27
- Andrea Lindholz (CDU/CSU), 2017-05-18
- Ansgar Heveling (CDU/CSU), 2017-11-22
- Antje Lezius (CDU/CSU), 2019-06-07
- Alexander Throm (CDU/CSU), 2019-01-18
- Alexander Throm (CDU/CSU), 2019-06-07
- Detlef Seif (CDU/CSU), 2019-02-14
- Dr. Astrid Freudenstein (CDU/CSU), 2017-02-16
- Dr. Reinhard Brandl (CDU/CSU), 2017-06-02
- Dr. Stephan Harbarth (CDU/CSU), 2017-03-23
- Gerda Hasselfeldt (CDU/CSU), 2017-06-29
- Josef Oster (CDU/CSU), 2019-01-18
- Jürgen Klimke (CDU/CSU), 2017-02-16
- Marc Biadacz (CDU/CSU), 2019-06-07
- Marian Wendt (CDU/CSU), 2019-02-14
- Mark Helfrich (CDU/CSU), 2017-02-16
- Michael Kuffer (CDU/CSU), 2019-02-14
- Michael Kuffer (CDU/CSU), 2019-10-18
- Nina Warken (CDU/CSU), 2017-03-23
- Nina Warken (CDU/CSU), 2019-05-09
- Stephan Mayer (Altötting) (CDU/CSU), 2017-06-01
- Stephan Mayer (Altötting) (CDU/CSU), 2017-11-22
- Thorsten Frei (CDU/CSU), 2019-05-09
- Thorsten Frei (CDU/CSU), 2019-06-07
- Ursula Groden-Kranich (CDU/CSU), 2017-01-20
- Volkmar Klein (CDU/CSU), 2019-04-12

---

## 问题 7: 单年单党派观点

**问题**: Welche wichtigen Ansichten und Vorschläge vertrat die AfD zur Flüchtlingspolitik im Jahr 2018?

### 参数提取

```json
{
  "time_range": {
    "start_year": "2018",
    "end_year": "2018",
    "specific_years": [
      "2018"
    ],
    "time_expression": "im Jahr 2018"
  },
  "parties": [
    "AfD"
  ],
  "topics": [
    "Flüchtlingspolitik"
  ],
  "keywords": [
    "Ansichten",
    "Vorschläge"
  ]
}
```

### 检索信息

- **意图**: simple
- **问题类型**: None
- **年份分布**: {}
- **检索文档数**: 50
- **ReRank后文档数**: 1

### 最终答案

**Zusammenfassung**
Basierend auf den vorliegenden Redeausschnitten vertrat die AfD im Jahr 2018 eine strikt ablehnende Haltung zur damaligen Flüchtlingspolitik. Zentrale Forderungen waren die Beendigung der als "illegal" bezeichneten Migration durch einen Asylstopp und effektive Grenzkontrollen, die vollständige Abschaffung des Familiennachzugs für subsidiär Schutzberechtigte sowie eine konsequente Rückführung und Abschiebung abgelehnter Asylbewerber. Zudem kritisierte die Partei die hohen Kosten für Flüchtlinge und Integration und schlug eine Umstellung von Geld- auf Sachleistungen vor, um den Migrationsdruck zu senken.

**Wichtige Aussagen**

• **Dr. Christian Wirth (AfD)**:
  „Die AfD beantragt den Wegfall des Anspruchs auf Nachzug der Familienangehörigen von subsidiär schutzberechtigten Migranten.“ (Rede vom 2018-02-01)

• **Tobias Matthias Peterka (AfD)**:
  „Die AfD steht weiterhin für sofortigen Asylstopp, Reduzierung der Fallzahlen und eine grundlegende Änderung dieses Anspruchssystems.“ (Rede vom 2018-04-19)

• **Dr. Bernd Baumann (AfD)**:
  „Frau Bundeskanzlerin, die Bürger haben ein Recht darauf, zu wissen: Wieso wird nicht abgeschoben? Wollen Sie nicht, oder können Sie nicht?“ (Rede vom 2018-12-12)

• **Ulrich Oehme (AfD)**:
  Schlägt eine „wirkliche Verringerung des Migrationsdrucks durch Rückkehr zu Sachleistungen für Asylsuchende“ vor. (Rede vom 2018-07-04)

**Belege aus den Materialien**
- **Beendigung der Zuwanderung und Grenzkontrollen**: Die AfD forderte die Beendigung der "illegalen Migration" (Marc Bernhard, 2018-11-20, Material 4) und einen "sofortigen Asylstopp" (Tobias Matthias Peterka, 2018-04-19, Material 5). Dr. Gottfried Curio betonte, es müsse geklärt werden, "wer überhaupt zum Grenzübertritt berechtigt ist" und kritisierte, dass die Unionsparteien einen AfD-Antrag zur verstärkten Grenzüberwachung abgelehnt hätten (2018-03-23, Material 13).

- **Familiennachzug**: Mehrere Redner forderten den vollständigen Wegfall des Familiennachzugs für subsidiär Schutzberechtigte. Dr. Christian Wirth (2018-02-01, Material 10) und Dr. Gottfried Curio (2018-01-18, Material 11) stellten entsprechende Anträge. Als Alternative wurde eine Familienzusammenführung in Schutzzonen in den Herkunftsregionen vorgeschlagen (Material 10).

- **Abschiebung und Rückführung**: Dr. Bernd Baumann kritisierte die sinkenden Abschiebezahlen als "politisches Totalversagen" und forderte Aufklärung, warum abgelehnte Asylbewerber nicht abgeschoben werden (2018-12-12, Material 8). Beatrix von Storch warf im Zusammenhang mit dem Fall Anis Amri die Frage auf: "Was muss man eigentlich tun, um aus Deutschland abgeschoben zu werden?" (2018-01-18, Material 12). Jan Ralf Nolte forderte eine "direkte Rückführung nach Afrika", um Schleppernetzwerke auszutrocknen (2018-03-22, Material 15).

- **Leistungen, Kosten und Integration**: Ulrich Oehme schlug vor, zu Sachleistungen für Asylsuchende zurückzukehren, um Anreize zu senken (2018-07-04, Material 3). Die Kosten der Flüchtlingspolitik wurden von Marc Bernhard (2018-11-20, Material 4) und Dr. Gottfried Curio (2018-11-29, Material 6) auf 50 Milliarden Euro pro Jahr beziffert und als zu hoch kritisiert. Ulrike Schielke-Ziesing bezeichnete Integrationsmaßnahmen als "unnötig" (2018-07-05, Material 2).

- **Internationale Politik und Abkommen**: Marc Bernhard forderte, den UN-Migrationspakt zu stoppen (2018-11-20, Material 4). Ulrich Oehme schlug vor, die Entwicklungshilfe für Staaten einzustellen, die sich nicht an Rücknahmevereinbarungen halten (2018-07-04, Material 3).

**Quellen**
- Material 1: Udo Theodor Hemmelgarn (AfD), 2018-10-19
- Material 2: Ulrike Schielke-Ziesing (AfD), 2018-07-05
- Material 3: Ulrich Oehme (AfD), 2018-07-04
- Material 4: Marc Bernhard (AfD), 2018-11-20
- Material 5: Tobias Matthias Peterka (AfD), 2018-04-19
- Material 6: Dr. Gottfried Curio (AfD), 2018-11-29
- Material 7: Beatrix von Storch (AfD), 2018-06-15
- Material 8: Dr. Bernd Baumann (AfD), 2018-12-12
- Material 9: Martin Hess (AfD), 2018-07-05
- Material 10: Dr. Christian Wirth (AfD), 2018-02-01
- Material 11: Dr. Gottfried Curio (AfD), 2018-01-18
- Material 12: Beatrix von Storch (AfD), 2018-01-18
- Material 13: Dr. Gottfried Curio (AfD), 2018-03-23
- Material 14: Peter Boehringer (AfD), 2018-11-20
- Material 15: Jan Ralf Nolte (AfD), 2018-03-22

---
