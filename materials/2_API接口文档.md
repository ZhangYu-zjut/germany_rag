# 德国议会RAG智能问答系统 - API接口文档

## 目录

- [概述](#概述)
- [快速开始](#快速开始)
- [Base URL](#base-url)
- [认证](#认证)
- [API端点](#api端点)
  - [健康检查](#1-健康检查)
  - [系统信息](#2-系统信息)
  - [标准问答](#3-标准问答)
  - [深度分析问答](#4-深度分析问答)
  - [示例问题](#5-示例问题)
  - [根路径](#6-根路径)
- [数据模型](#数据模型)
- [错误码说明](#错误码说明)
- [调用示例](#调用示例)
- [注意事项](#注意事项)
- [FAQ](#faq)

---

## 概述

德国议会RAG智能问答API是一个基于RAG（检索增强生成）技术的智能问答系统，专门用于查询和分析德国联邦议院（Bundestag）1949-2025年的议会演讲记录。

### 核心功能

| 功能 | 描述 |
|------|------|
| **多语言支持** | 支持中文和德文问题输入 |
| **智能分类** | 自动识别问题类型（事实查询/变化分析/对比分析） |
| **知识图谱扩展** | 深度模式下自动扩展相关查询 |
| **来源追溯** | 返回答案的原始文档来源 |

### 支持的问题类型

- **事实查询**: 某年某党派的具体立场
- **变化分析**: 跨年份的政策变化追踪
- **对比分析**: 多党派观点对比
- **趋势分析**: 政策演变趋势
- **发言人查询**: 特定议员的观点

### 数据覆盖范围

- **时间跨度**: 1949年 - 2025年
- **支持党派**: CDU/CSU, SPD, GRÜNE, FDP, DIE LINKE, AfD 等
- **数据量**: 110万+ 向量文档

---

## 快速开始

### 30秒快速测试

```bash
# 1. 检查服务是否正常
curl https://germanyrag-production.up.railway.app/api/v1/health

# 2. 发送一个简单问题
curl -X POST https://germanyrag-production.up.railway.app/api/v1/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "2019年CDU/CSU对难民政策的立场是什么？"}'
```

---

## Base URL

**生产环境**
```
https://germanyrag-production.up.railway.app
```

所有API端点都以此为基础路径。

---

## 认证

当前版本 API **无需认证**，可直接调用。

> 注意：生产环境建议添加API Key认证机制。

---

## API端点

### 1. 健康检查

检查API服务是否正常运行。

**请求**

```
GET /api/v1/health
```

**curl 示例**

```bash
curl https://germanyrag-production.up.railway.app/api/v1/health
```

**响应**

```json
{
  "status": "healthy",
  "workflow_ready": true,
  "timestamp": "2025-12-28T07:00:00.000000"
}
```

**响应字段说明**

| 字段 | 类型 | 描述 |
|------|------|------|
| `status` | string | 服务状态: `healthy` / `initializing` |
| `workflow_ready` | boolean | 工作流是否就绪 |
| `timestamp` | string | 检查时间 (ISO 8601格式) |

**状态码**

| 状态码 | 描述 |
|--------|------|
| 200 | 服务正常 |
| 500 | 服务异常 |

---

### 2. 系统信息

获取系统配置和版本信息。

**请求**

```
GET /api/v1/info
```

**curl 示例**

```bash
curl https://germanyrag-production.up.railway.app/api/v1/info
```

**响应**

```json
{
  "service_name": "德国议会RAG智能问答系统",
  "version": "1.0.0",
  "embedding_mode": "deepinfra",
  "llm_model": "gemini-2.5-pro",
  "vector_db": "Pinecone",
  "production_mode": true,
  "supported_languages": ["中文", "德文"]
}
```

**响应字段说明**

| 字段 | 类型 | 描述 |
|------|------|------|
| `service_name` | string | 服务名称 |
| `version` | string | API版本号 |
| `embedding_mode` | string | Embedding模式 |
| `llm_model` | string | 使用的LLM模型 |
| `vector_db` | string | 向量数据库类型 |
| `production_mode` | boolean | 是否为生产模式 |
| `supported_languages` | array | 支持的语言列表 |

---

### 3. 标准问答

**核心接口** - 发送问题并获取答案。

**请求**

```
POST /api/v1/ask
Content-Type: application/json
```

**curl 示例**

```bash
# 简单问题（标准模式）
curl -X POST https://germanyrag-production.up.railway.app/api/v1/ask -H "Content-Type: application/json" -d '{"question": "2019年CDU/CSU对难民政策的立场是什么？", "deep_thinking": false}'

# 复杂问题（启用深度分析）
curl -X POST https://germanyrag-production.up.railway.app/api/v1/ask -H "Content-Type: application/json" -d '{"question": "请对比2015-2018年各党派在移民问题上的立场变化", "deep_thinking": true}'
```

**请求体**

```json
{
  "question": "2019年CDU/CSU对难民政策的立场是什么？",
  "deep_thinking": false
}
```

**请求参数说明**

| 参数 | 类型 | 必需 | 默认值 | 描述 |
|------|------|------|--------|------|
| `question` | string | 是 | - | 用户问题，支持中文和德文，长度1-2000字符 |
| `deep_thinking` | boolean | 否 | false | 是否启用深度分析模式 |

**响应**

```json
{
  "success": true,
  "question": "2019年CDU/CSU对难民政策的立场是什么？",
  "answer": "根据2019年德国联邦议院的演讲记录，CDU/CSU在难民政策上的主要立场包括...",
  "intent": "simple",
  "question_type": "事实查询",
  "parameters": {
    "time_range": {
      "start_year": "2019",
      "end_year": "2019",
      "specific_years": ["2019"]
    },
    "parties": ["CDU/CSU"],
    "topics": ["难民政策"]
  },
  "sub_questions": null,
  "sub_answers": null,
  "sources_count": 15,
  "sources": [
    {
      "text": "文档片段内容...",
      "year": "2019",
      "speaker": "Dr. Angela Merkel",
      "party": "CDU/CSU",
      "score": 0.8542
    }
  ],
  "deep_thinking_mode": false,
  "reasoning_steps": null,
  "kg_expansion_info": {
    "use_kg": true,
    "expansion_level": "tag",
    "score": 2,
    "reasons": ["主题匹配知识图谱: Flüchtlingspolitik"],
    "expansion_query_count": 5
  },
  "processing_time_ms": 45230,
  "error": null
}
```

**响应字段说明**

| 字段 | 类型 | 描述 |
|------|------|------|
| `success` | boolean | 请求是否成功处理 |
| `question` | string | 原始问题 |
| `answer` | string | **最终答案**（德文格式，包含引用） |
| `intent` | string | 问题意图: `simple` / `complex` |
| `question_type` | string \| null | 问题类型: `事实查询` / `变化分析` / `对比分析` / `趋势分析`（简单问题可能为null） |
| `parameters` | object | 从问题中提取的参数 |
| `sub_questions` | array | 拆解后的子问题（复杂问题时有值） |
| `sub_answers` | array | 子问题答案列表 |
| `sources_count` | integer | 参考来源总数 |
| `sources` | array | 部分参考来源（最多5个） |
| `deep_thinking_mode` | boolean | 是否为深度分析模式 |
| `reasoning_steps` | array | 推理步骤（深度模式时有值） |
| `kg_expansion_info` | object | 知识图谱扩展信息 |
| `processing_time_ms` | integer | 处理耗时（毫秒） |
| `error` | string | 错误信息（失败时有值） |

**parameters 对象结构**

```json
{
  "time_range": {
    "start_year": "2015",
    "end_year": "2019",
    "specific_years": ["2015", "2016", "2017", "2018", "2019"],
    "time_expression": "2015-2019年"
  },
  "parties": ["CDU/CSU", "SPD"],
  "speakers": ["Merkel"],
  "topics": ["难民政策", "移民"],
  "keywords": ["立场", "变化"]
}
```

**sources 数组元素结构**

```json
{
  "text": "文档内容片段（最多500字符）",
  "year": "2019",
  "speaker": "发言人姓名",
  "party": "党派名称",
  "score": 0.8542
}
```

**kg_expansion_info 对象结构**

```json
{
  "use_kg": true,
  "expansion_level": "tag",
  "score": 99,
  "reasons": ["深度分析模式强制启用"],
  "topics": ["Flüchtlingspolitik"],
  "matched_topics": ["Flüchtlingspolitik"],
  "dimensions": ["Abschiebung", "Aufnahme", "Asylverfahren"],
  "selected_tags": ["Syrien", "Afghanistan", "Türkei"],
  "expansion_query_count": 23,
  "expansion_queries": ["CDU/CSU Syrien Flüchtlinge 2019", "..."]
}
```

| 字段 | 类型 | 描述 |
|------|------|------|
| `use_kg` | boolean | 是否使用知识图谱扩展 |
| `expansion_level` | string | 扩展级别: `tag` / `dimension` / `topic` |
| `score` | integer | 扩展评分 |
| `reasons` | array | 触发原因列表 |
| `topics` | array | 匹配的知识图谱主题 |
| `matched_topics` | array | 实际匹配到的主题 |
| `dimensions` | array | 扩展的维度 |
| `selected_tags` | array | 选中的标签 |
| `expansion_query_count` | integer | 扩展查询数量 |
| `expansion_queries` | array | 扩展查询列表（前5个） |

---

### 4. 深度分析问答

强制启用深度分析模式的问答接口。

**请求**

```
POST /api/v1/ask/deep
Content-Type: application/json
```

**curl 示例**

> ⚠️ **重要**：deep接口处理时间较长（10-20分钟），必须设置超时参数，否则会报 `Error in the HTTP2 framing layer` 错误。

```bash
# 推荐写法：使用 --max-time 1800（30分钟超时）和 --http1.1（更稳定）
curl --http1.1 --max-time 1800 -X POST https://germanyrag-production.up.railway.app/api/v1/ask/deep -H "Content-Type: application/json" -d '{"question": "请对比2015-2018年各党派在难民家庭团聚问题上的立场变化"}'

# 多党派对比分析
curl --http1.1 --max-time 1800 -X POST https://germanyrag-production.up.railway.app/api/v1/ask/deep -H "Content-Type: application/json" -d '{"question": "2017年德国联邦议会中各党派对专业人才移民制度改革分别持什么立场？"}'

# 趋势分析（德语问题）
curl --http1.1 --max-time 1800 -X POST https://germanyrag-production.up.railway.app/api/v1/ask/deep -H "Content-Type: application/json" -d '{"question": "Wie haben sich die Diskussionen über Klimaschutz zwischen 2019 und 2021 entwickelt?"}'
```

**请求体**

```json
{
  "question": "请对比2015-2018年各党派在难民家庭团聚问题上的立场变化"
}
```

> 注意：此接口会自动将 `deep_thinking` 设为 `true`，无需手动指定。

**响应**

与标准问答接口相同，但会包含更详细的 `reasoning_steps` 和 `kg_expansion_info`。

**适用场景**

- 复杂的多年份变化分析
- 多党派立场对比
- 需要详细推理过程的问题

**处理时间**

- 预计耗时：**10-20分钟**
- 建议设置较长的超时时间（如1800秒/30分钟）

---

### 5. 示例问题

获取各类问题的示例。

**请求**

```
GET /api/v1/examples
```

**curl 示例**

```bash
curl https://germanyrag-production.up.railway.app/api/v1/examples
```

**响应**

```json
{
  "examples": {
    "simple_queries": [
      "2019年CDU/CSU对难民政策的立场是什么？",
      "Merkel在2017年关于欧盟一体化说了什么？",
      "2018年AfD在移民问题上的主要观点是什么？"
    ],
    "complex_queries": [
      "请对比2015-2018年各党派在难民家庭团聚问题上的立场变化",
      "2017年德国联邦议会中各党派对专业人才移民制度改革分别持什么立场？",
      "请概述2015年以来德国基民盟对难民政策的立场发生了哪些主要变化"
    ],
    "german_queries": [
      "Welche Positionen vertraten die verschiedenen Parteien im Deutschen Bundestag 2017 zur Reform des Fachkräfteeinwanderungsgesetzes?",
      "Was waren die Hauptpositionen und Forderungen der Grünen zur Migrationsfrage im Deutschen Bundestag 2015?"
    ]
  },
  "supported_parties": ["CDU/CSU", "SPD", "GRÜNE", "FDP", "DIE LINKE", "AfD"],
  "data_range": "1949-2025"
}
```

---

### 6. 根路径

获取API基本信息和文档链接。

**请求**

```
GET /
```

**curl 示例**

```bash
curl https://germanyrag-production.up.railway.app/
```

**响应**

```json
{
  "service": "德国议会RAG智能问答API",
  "version": "1.0.0",
  "docs": "/docs",
  "health": "/api/v1/health"
}
```

---

## 数据模型

### QuestionRequest（请求模型）

```typescript
interface QuestionRequest {
  question: string;      // 必需，1-2000字符
  deep_thinking?: boolean; // 可选，默认false
}
```

### AnswerResponse（响应模型）

```typescript
interface AnswerResponse {
  success: boolean;
  question: string;
  answer: string;
  intent?: "simple" | "complex";
  question_type?: string;
  parameters?: {
    time_range?: {
      start_year: string;
      end_year: string;
      specific_years: string[];
      time_expression?: string;
    };
    parties?: string[];
    speakers?: string[];
    topics?: string[];
    keywords?: string[];
  };
  sub_questions?: any[];
  sub_answers?: SubAnswer[];
  sources_count: number;
  sources?: SourceDocument[];
  deep_thinking_mode: boolean;
  reasoning_steps?: string[];
  kg_expansion_info?: {
    use_kg: boolean;
    expansion_level: string;
    score: number;
    reasons: string[];
    topics?: string[];
    matched_topics?: string[];
    dimensions?: string[];
    selected_tags?: string[];
    expansion_query_count?: number;
    expansion_queries?: string[];
  };
  processing_time_ms: number;
  error?: string;
}

interface SourceDocument {
  text: string;
  year?: string;
  speaker?: string;
  party?: string;
  score?: number;
}

interface SubAnswer {
  question: string;
  answer: string;
  sources_count: number;
}
```

---

## 错误码说明

### HTTP状态码

| 状态码 | 含义 | 描述 |
|--------|------|------|
| 200 | OK | 请求成功 |
| 400 | Bad Request | 请求参数错误 |
| 422 | Unprocessable Entity | 请求体验证失败 |
| 500 | Internal Server Error | 服务器内部错误 |
| 503 | Service Unavailable | 服务正在初始化 |

### 业务错误

当 `success: false` 时，`error` 字段会包含错误信息：

| 错误信息 | 原因 | 解决方案 |
|----------|------|----------|
| `服务正在初始化，请稍后重试` | 服务刚启动，工作流未就绪 | 等待10-30秒后重试 |
| `处理问题时发生错误` | 内部处理异常 | 检查问题格式，重试 |
| `insufficient_user_quota` | LLM API配额不足 | 联系管理员充值 |
| `工作流未初始化` | 服务异常 | 重启服务 |

### 验证错误示例

```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "question"],
      "msg": "String should have at least 1 character",
      "input": "",
      "ctx": {"min_length": 1}
    }
  ]
}
```

---

## 调用示例

### cURL

```bash
# 健康检查
curl https://germanyrag-production.up.railway.app/api/v1/health

# 系统信息
curl https://germanyrag-production.up.railway.app/api/v1/info

# 简单问题
curl -X POST "https://germanyrag-production.up.railway.app/api/v1/ask" -H "Content-Type: application/json" -d '{"question": "2019年CDU/CSU对难民政策的立场是什么？", "deep_thinking": false}'

# 深度分析
curl -X POST "https://germanyrag-production.up.railway.app/api/v1/ask/deep" -H "Content-Type: application/json" -d '{"question": "请对比2015-2018年各党派在移民问题上的立场变化"}'

# 示例问题
curl https://germanyrag-production.up.railway.app/api/v1/examples
```

### Python

```python
import requests

API_URL = "https://germanyrag-production.up.railway.app"

def ask_question(question: str, deep_thinking: bool = False) -> dict:
    """发送问题到API"""
    response = requests.post(
        f"{API_URL}/api/v1/ask",
        json={
            "question": question,
            "deep_thinking": deep_thinking
        },
        timeout=300  # 5分钟超时
    )
    response.raise_for_status()
    return response.json()

# 使用示例
result = ask_question("2019年CDU/CSU对难民政策的立场是什么？")

if result["success"]:
    print("答案:", result["answer"])
    print("处理时间:", result["processing_time_ms"], "ms")
    print("来源数量:", result["sources_count"])
else:
    print("错误:", result["error"])
```

### JavaScript / Node.js

```javascript
const API_URL = "https://germanyrag-production.up.railway.app";

async function askQuestion(question, deepThinking = false) {
  const response = await fetch(`${API_URL}/api/v1/ask`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      question: question,
      deep_thinking: deepThinking,
    }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return await response.json();
}

// 使用示例
askQuestion("2019年CDU/CSU对难民政策的立场是什么？")
  .then((result) => {
    if (result.success) {
      console.log("答案:", result.answer);
    } else {
      console.error("错误:", result.error);
    }
  })
  .catch((error) => console.error("请求失败:", error));
```

### Java

```java
import java.net.http.*;
import java.net.URI;

public class BundestagApiClient {
    private static final String API_URL = "https://germanyrag-production.up.railway.app";
    private final HttpClient client = HttpClient.newHttpClient();

    public String askQuestion(String question) throws Exception {
        String requestBody = String.format(
            "{\"question\": \"%s\", \"deep_thinking\": false}",
            question.replace("\"", "\\\"")
        );

        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create(API_URL + "/api/v1/ask"))
            .header("Content-Type", "application/json")
            .POST(HttpRequest.BodyPublishers.ofString(requestBody))
            .timeout(java.time.Duration.ofMinutes(5))
            .build();

        HttpResponse<String> response = client.send(
            request,
            HttpResponse.BodyHandlers.ofString()
        );

        return response.body();
    }
}
```

---

## 注意事项

### 1. 超时设置

| 问题类型 | 预计处理时间 | 建议超时 |
|----------|--------------|----------|
| 简单问题 | 1-3分钟 | 300秒 |
| 复杂问题 | 3-8分钟 | 600秒 |
| 深度分析 | 10-20分钟 | 1800秒 |

### 2. 问题格式建议

**推荐格式**：
- 明确指定年份：`2019年...`
- 明确指定党派：`CDU/CSU...`
- 使用德文党派名称效果更好

**示例**：
```
✅ "2019年CDU/CSU对难民政策的立场是什么？"
✅ "Welche Position vertrat die CDU/CSU 2019 zur Flüchtlingspolitik?"
❌ "难民政策怎么样？"（过于模糊）
```

### 3. 并发限制

- 建议单用户并发请求数：**1-2个**
- 系统最大并发处理：**4个请求**

### 4. 答案语言

- 无论问题使用中文还是德文，**答案统一使用德文**输出
- 答案中会包含原始演讲引用（Quellen）

### 5. 数据时效性

- 数据范围：1949-2025年
- 部分年份数据可能不完整（尤其是较早年份）

---

## FAQ

### Q1: 为什么处理时间这么长？

A: 系统需要执行多个步骤：
1. 意图识别和参数提取
2. 向量检索（可能触发知识图谱扩展，生成20+个查询）
3. 结果重排序
4. LLM生成答案

深度分析问题需要10-20分钟。

### Q2: 如何判断服务是否正常？

A: 调用健康检查接口：
```bash
curl https://germanyrag-production.up.railway.app/api/v1/health
```

`workflow_ready: true` 表示服务就绪。

### Q3: 支持哪些党派？

A: 主要支持：
- CDU/CSU（基民盟/基社盟）
- SPD（社民党）
- GRÜNE（绿党）
- FDP（自民党）
- DIE LINKE（左翼党）
- AfD（德国选择党）

### Q4: 可以查询特定议员吗？

A: 可以，在问题中指定议员姓名即可：
```
"Merkel在2017年关于欧盟一体化说了什么？"
```

### Q5: 如何获得更详细的分析？

A: 使用深度分析接口 `/api/v1/ask/deep`，或设置 `deep_thinking: true`。

### Q6: 调用deep接口报错 `Error in the HTTP2 framing layer`？

A: 这是因为deep接口处理时间较长（10-20分钟），默认超时设置不够。解决方案：

```bash
# 添加超时参数和使用HTTP/1.1（30分钟超时）
curl --http1.1 --max-time 1800 -X POST https://germanyrag-production.up.railway.app/api/v1/ask/deep -H "Content-Type: application/json" -d '{"question": "你的问题"}'
```

---

## 交互式文档

访问以下地址查看Swagger UI交互式文档：

```
https://germanyrag-production.up.railway.app/docs
```

或 ReDoc 格式文档：

```
https://germanyrag-production.up.railway.app/redoc
```

---

## 更新日志

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| 1.0.0 | 2025-12-28 | 初始版本发布 |

---

## 技术支持

- **API文档**: `/docs`
- **项目仓库**: GitHub
- **问题反馈**: 提交Issue
