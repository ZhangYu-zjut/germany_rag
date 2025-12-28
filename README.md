# 德国议会RAG智能问答系统

基于 RAG (Retrieval-Augmented Generation) 技术的德国联邦议院演讲记录智能问答系统，支持 1949-2025 年的议会演讲数据。

## 项目概述

本系统使用 LangGraph 实现复杂问题的多阶段处理工作流，结合知识图谱扩展技术，能够回答关于德国议会演讲的各类问题，包括事实查询、变化分析、多党派对比等。

### 核心特性

- **多语言支持**: 支持中文和德文问题输入
- **复杂问题处理**: 支持跨年份、跨党派的复杂分析
- **知识图谱扩展**: 智能扩展查询维度，提高召回率
- **深度分析模式**: 强制启用知识图谱，生成更详细的分析报告

## 技术栈

| 组件 | 技术选型 |
|------|----------|
| **LLM** | Gemini 2.5 Pro/Flash (via Evolink API) |
| **Embedding** | BGE-M3 (DeepInfra API, 1024维) |
| **向量数据库** | Pinecone (110万+ 向量) |
| **工作流引擎** | LangGraph |
| **Web框架** | FastAPI (API) / Streamlit (UI) |
| **部署平台** | Railway |

## 项目结构

```
rag_germant/
├── src/                          # 核心源代码
│   ├── config/                   # 配置管理
│   │   └── settings.py           # Pydantic配置
│   ├── data_loader/              # 数据加载
│   │   ├── loader.py             # JSON数据加载
│   │   ├── splitter.py           # 文本分块
│   │   └── mapper.py             # 元数据映射
│   ├── graph/                    # LangGraph工作流
│   │   ├── workflow.py           # 主工作流定义
│   │   ├── state.py              # 状态定义
│   │   ├── knowledge_graph.py    # 知识图谱管理器
│   │   ├── templates/            # 问题拆解模板
│   │   └── nodes/                # 工作流节点
│   │       ├── intent_enhanced.py      # 意图分析
│   │       ├── extract_enhanced.py     # 参数提取
│   │       ├── decompose_enhanced.py   # 问题拆解
│   │       ├── retrieve_pinecone.py    # 向量检索
│   │       ├── rerank.py               # 重排序
│   │       └── summarize_incremental_v2.py  # 两阶段总结
│   ├── llm/                      # LLM相关
│   │   ├── client.py             # LLM客户端(带速率限制)
│   │   ├── embeddings.py         # Embedding客户端
│   │   └── prompts*.py           # 提示词模板
│   ├── vectordb/                 # 向量数据库
│   │   └── pinecone_retriever.py # Pinecone检索器
│   └── utils/                    # 工具函数
│       └── logger.py             # 日志配置
├── data/                         # 数据文件
│   ├── knowledge_graph.json      # 知识图谱(德文)
│   ├── knowledge_graph_chinese.json   # 知识图谱(中文)
│   ├── knowledge_graph_extended.json  # 扩展知识图谱
│   ├── party_mapping.csv         # 党派名称映射
│   └── pp_json_49-21/            # 演讲数据(1949-2021)
├── materials/                    # 交付材料
│   ├── 1_七个问题测试结果_Q1-Q7_完整/  # 7个测试问题结果
│   ├── 2_API接口文档.md          # API文档
│   ├── 3_UI界面使用说明.md       # UI使用说明
│   ├── 4_项目整体测试报告.md     # 测试报告
│   └── 5_100个QA样本评估报告.md  # 评估报告
├── pages/                        # Streamlit页面
│   └── knowledge_graph_editor.py # 知识图谱编辑器
├── api_server.py                 # FastAPI服务入口
├── streamlit_app.py              # Streamlit UI入口
├── main.py                       # 命令行交互入口
├── build_index.py                # 构建向量索引
└── requirements.txt              # 依赖
```

## 工作流架构

```
用户问题
    │
    ▼
┌─────────────────┐
│   IntentNode    │  意图分析 + 合法性检查
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
 simple    complex
    │         │
    ▼         ▼
┌────────┐ ┌─────────────┐
│Extract │ │  Classify   │  问题分类
└────┬───┘ └──────┬──────┘
     │            │
     │     ┌──────┴──────┐
     │     │   Extract   │  参数提取
     │     └──────┬──────┘
     │            │
     │     ┌──────┴──────┐
     │     │  Decompose  │  问题拆解(+知识图谱扩展)
     │     └──────┬──────┘
     │            │
     └──────┬─────┘
            │
     ┌──────┴──────┐
     │  Retrieve   │  Pinecone向量检索
     └──────┬──────┘
            │
     ┌──────┴──────┐
     │   ReRank    │  Cohere重排序
     └──────┬──────┘
            │
     ┌──────┴──────┐
     │ Summarize   │  两阶段总结生成答案
     └──────┬──────┘
            │
            ▼
        最终答案
```

## 知识图谱

知识图谱用于扩展查询维度，解决特定领域问题的召回失败问题。

### 文件位置

| 文件 | 说明 |
|------|------|
| `data/knowledge_graph.json` | 主知识图谱(德文标签) |
| `data/knowledge_graph_chinese.json` | 中文版知识图谱 |
| `data/knowledge_graph_extended.json` | 扩展版知识图谱 |
| `src/graph/knowledge_graph.py` | 知识图谱管理器 |
| `pages/knowledge_graph_editor.py` | 知识图谱编辑器(Streamlit) |

### 结构

```
topics (主题)
  └── dimensions (维度)
        └── tags (标签)
              └── keywords (关键词)
```

示例:
```json
{
  "Flüchtlingspolitik": {
    "dimensions": {
      "Länder": {
        "tags": {
          "Syrien": {
            "keywords": ["Syrien", "syrisch", "Assad"],
            "weight": 1.0
          }
        }
      }
    }
  }
}
```

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repo_url>
cd rag_germant

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件:

```bash
# LLM API (Evolink代理)
OPENAI_API_KEY=your_evolink_api_key
THIRD_PARTY_BASE_URL=https://api.evolink.ai/v1
THIRD_PARTY_MODEL_NAME=gemini-2.5-flash

# Embedding API (DeepInfra)
EMBEDDING_MODE=deepinfra
DEEPINFRA_EMBEDDING_API_KEY=your_deepinfra_key
DEEPINFRA_EMBEDDING_BASE_URL=https://api.deepinfra.com/v1/openai

# Pinecone
PINECONE_VECTOR_DATABASE_API_KEY=your_pinecone_key
PINECONE_HOST=your_pinecone_host

# Cohere ReRank (可选)
COHERE_API_KEY=your_cohere_key

# 系统配置
PRODUCTION_MODE=true
```

### 3. 运行方式

#### 命令行交互
```bash
python main.py
```

#### API服务
```bash
python api_server.py --host 0.0.0.0 --port 8000
# 访问: http://localhost:8000/docs
```

#### Streamlit UI
```bash
streamlit run streamlit_app.py
# 访问: http://localhost:8501
```

## API接口

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/ask` | POST | 标准问答 |
| `/api/v1/ask/deep` | POST | 深度分析模式 |
| `/api/v1/health` | GET | 健康检查 |
| `/api/v1/info` | GET | 系统信息 |
| `/api/v1/examples` | GET | 示例问题 |

### 请求示例

```bash
curl -X POST "https://germanyrag-production.up.railway.app/api/v1/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "2019年CDU/CSU对难民政策的立场是什么？"}'
```

### 响应示例

```json
{
  "success": true,
  "question": "2019年CDU/CSU对难民政策的立场是什么？",
  "answer": "Als Expertin für die deutsche Bundespolitik...",
  "intent": "simple",
  "sources_count": 45,
  "processing_time_ms": 58600
}
```

## 性能指标

| 指标 | 数值 |
|------|------|
| 向量数据量 | 1,109,456 |
| 标准问题响应时间 | 1-3分钟 |
| 深度分析响应时间 | 10-20分钟 |
| 事实准确性 | 91.5% |
| 语义相似度 | 86.2% |
| 完整度 | 80.4% |

## 线上部署

- **API地址**: https://germanyrag-production.up.railway.app
- **API文档**: https://germanyrag-production.up.railway.app/docs

## 支持的问题类型

| 类型 | 示例 |
|------|------|
| **事实查询** | "2019年CDU/CSU对难民政策的立场是什么？" |
| **变化分析** | "2015-2018年各党派在难民问题上的立场变化" |
| **对比分析** | "对比CDU/CSU和SPD在2019年的气候政策观点" |
| **趋势分析** | "德国能源政策的演变趋势" |
| **人物查询** | "Merkel在2017年关于欧盟一体化说了什么？" |

## 数据说明

### 数据范围
- 1949-2025年德国联邦议院演讲记录
- 约110万个文本块

### 元数据字段
```python
{
    "year": "2019",           # 年份
    "month": "03",            # 月份
    "speaker": "Dr. Merkel",  # 发言人
    "group": "CDU/CSU",       # 党派(德文)
    "group_chinese": "基民盟/基社盟",  # 党派(中文)
    "lp": "19",               # 立法期
}
```

## 维护说明

### 添加知识图谱标签

1. 编辑 `data/knowledge_graph_extended.json`
2. 或使用 Streamlit 知识图谱编辑器

### 更新LLM模型

修改 `.env` 中的 `THIRD_PARTY_MODEL_NAME`

### 速率限制

LLM客户端内置速率限制(1.5秒/请求)和自动重试机制，防止API限流。

## License

Private - All Rights Reserved

---

**更新时间**: 2025-12-28
