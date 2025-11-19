# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a RAG-based intelligent Q&A system for German Parliament (Bundestag) speeches from 1949-2025. The system uses LangGraph for complex question workflow orchestration, BGE-M3 for local embeddings, and Pinecone as the vector database.

## Common Development Commands

### Environment Setup
```bash
# Activate virtual environment (already exists at venv/)
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies (if needed)
pip install -r requirements.txt

# Verify configuration
python -c "from src.config import settings; print(f'Embedding: {settings.embedding_mode}, Milvus: {settings.milvus_mode}')"
```

### Building Index
```bash
# Build vector index (processes sample data)
python build_index.py

# Migrate data to Pinecone (specific year)
python migrate_2015_optimal_config.py

# Batch migration (multiple years)
python batch_migrate_2015_2025.py
```

### Running the Application
```bash
# Interactive Q&A interface
python main.py

# Check Pinecone index status
python check_pinecone_status.py
```

### Testing
```bash
# Run all tests
pytest tests/

# Run specific test files
pytest tests/test_basic_integration.py
pytest tests/test_real_llm.py

# Test retrieval functionality
python test_retrieval.py

# Test workflow end-to-end
python tests/test_end_to_end_real.py
```

### Data Analysis
```bash
# Analyze metadata and generate statistics
python analyze_metadata.py

# Check 2019 data comprehensively
python test_2019_comprehensive.py
```

## Architecture Overview

### Core Technology Stack
- **LLM**: Gemini 2.5 Pro (via Evolink API proxy)
- **Embedding**: BGE-M3 (local, 1024-dim, GPU-accelerated)
- **Vector DB**: Pinecone (production), Milvus/Qdrant (alternatives)
- **Workflow**: LangGraph (Chain of Agents pattern)
- **Text Processing**: LangChain

### Key Design Patterns

#### 1. LangGraph CoA (Chain of Agents) Workflow
The system uses a multi-stage workflow to handle complex questions:

```
Intent Analysis → Classify → Extract → Decompose → Retrieve → ReRank → Summarize
                      ↓                                ↓
                   (simple)                        (no results)
                      ↓                                ↓
                  Extract                          Exception
```

**Node Responsibilities**:
- **IntentNode**: Validates question legality, determines complexity (simple/complex)
- **ClassifyNode**: Categorizes complex questions (comparison, change analysis, summary, trend, fact query)
- **ExtractNode**: Extracts parameters (year, party, speaker, topic)
- **DecomposeNode**: Breaks complex questions into sub-questions using templates
- **RetrieveNode**: Hybrid search (vector similarity + metadata filtering)
- **ReRankNode**: Re-ranks results using Cohere API
- **SummarizeNode**: Generates final answer from retrieved chunks
- **ExceptionNode**: Handles errors and "no results" cases

**Location**: `src/graph/workflow.py` and `src/graph/nodes/`

#### 2. Multi-Modal Embedding Support
The system supports multiple embedding modes via a unified interface:

```python
# src/llm/embeddings.py - Unified interface
# Automatically selects based on EMBEDDING_MODE in .env:
# - local: BGE-M3 (BAAI/bge-m3, 1024-dim, GPU-accelerated)
# - openai: text-embedding-3-small (1536-dim)
# - deepinfra: BGE-M3 via DeepInfra API (1024-dim)
# - vertex: Google Cloud text-embedding-004 (768-dim)
```

**Usage**:
```python
from src.llm.embeddings import GeminiEmbeddingClient
client = GeminiEmbeddingClient()  # Auto-detects mode from settings
vectors = client.embed_batch(texts, batch_size=800)
```

#### 3. Configuration Management
All configuration is centralized in `src/config/settings.py` using Pydantic:

```python
from src.config import settings

# Access configuration
settings.embedding_mode  # "local" | "openai" | "deepinfra" | "vertex"
settings.milvus_mode     # "lite" | "local" | "cloud"
settings.chunk_size      # Default: 4000 (optimized)
settings.chunk_overlap   # Default: 800 (optimized)
```

**Environment variables** are loaded from `.env` file (NOT committed to git).

#### 4. Vector Database Abstraction
The system supports multiple vector databases with consistent interfaces:

- **Pinecone** (current production): Direct API calls in migration scripts
- **Milvus**: `src/vectordb/client.py`, `src/vectordb/collection.py`, `src/vectordb/retriever.py`
- **Qdrant**: `src/vectordb/qdrant_client.py`, `src/vectordb/qdrant_retriever.py`

### Data Pipeline

#### Speech Processing Flow
```
JSON Files → DataLoader → TextSplitter → MetadataMapper → EmbeddingClient → VectorDB
(pp_*.json)  (loader.py)  (splitter.py)   (mapper.py)     (embeddings.py)   (Pinecone)
```

**Optimal Configuration**:
- Chunk size: 4000 characters
- Chunk overlap: 800 characters
- Batch size: 800 embeddings (16GB GPU)
- Performance: 300+ embeddings/second with GPU

#### Metadata Structure
Each chunk includes rich metadata for filtering:
```python
{
    "year": "2015",
    "month": "01",
    "day": "21",
    "session": "001",
    "speaker": "Dr. Merkel",
    "group": "CDU/CSU",               # German party name
    "group_chinese": "基民盟/基社盟",    # Chinese translation
    "lp": "18",                        # Legislative period
    "file": "pp_2015.json"
}
```

## Critical Implementation Details

### 1. GPU Acceleration for BGE-M3
The local BGE-M3 model automatically uses GPU if available:
```python
# src/llm/local_embeddings.py
# Model automatically detects and uses CUDA
# Check availability: python -c "import torch; print(torch.cuda.is_available())"
```

**Performance**:
- GPU (NVIDIA 4060TI 16GB): 300+ embeddings/sec
- CPU fallback: ~20-50 embeddings/sec

### 2. Proxy Configuration (WSL2 Environment)
The development environment runs in WSL2 and requires proxy for external API access:
```bash
# Proxy auto-configured in ~/.bashrc
export http_proxy="http://127.0.0.1:7890"
export https_proxy="http://127.0.0.1:7890"
```

**Verify**: `echo $http_proxy` should show the proxy URL.

**Reference**: See `GLOBAL_PROXY_SETUP_COMPLETE.md` for troubleshooting.

### 3. Migration State Management
Data migration scripts include checkpoint/resume support:

```python
# Migration scripts track progress in JSON files
# Example: batch_migration_progress.json
# To resume interrupted migration, simply re-run the script
```

**Current Status**:
- 2015-2020: Partially migrated to Pinecone
- 2021-2025: Not yet migrated
- 1949-2014: Pending

**Reference**: See `PROJECT_HANDOVER.md` section "数据迁移状态"

### 4. Bilingual Support (German/Chinese)
The system maintains both German and Chinese party names:
```python
# data/party_mapping.csv contains translations
# Automatically enriched via MetadataMapper
mapper = MetadataMapper()
enriched = mapper.batch_enrich_chunks(chunks)
```

### 5. Prompt Engineering
Prompts are organized by functionality:
- `src/llm/prompts.py`: Base prompts (intent, classify, extract, decompose)
- `src/llm/prompts_enhanced.py`: Enhanced versions with better error handling
- `src/llm/prompts_fallback.py`: Fallback strategies for edge cases
- `src/llm/prompts_summarize.py`: Specialized summarization prompts

**Pattern**: All prompts support both German and Chinese input/output.

## Important Files and Locations

### Configuration
- `.env`: Environment variables (API keys, modes) - **NEVER commit to git**
- `src/config/settings.py`: Centralized configuration via Pydantic
- `requirements.txt`: Python dependencies

### Data Files
- `data/pp_json_49-21/`: JSON speech files (pp_1949.json to pp_2025.json)
- `data/party_mapping.csv`: Party name translations (German ↔ Chinese)
- `data/map.csv`: Speaker-party mapping over time

### Core Modules
- `src/data_loader/`: Data loading, splitting, metadata enrichment
- `src/llm/`: LLM client, embedding clients (local, cloud, API)
- `src/vectordb/`: Vector database clients and retrievers
- `src/graph/`: LangGraph workflow and nodes
- `src/utils/logger.py`: Centralized logging with loguru

### Migration Scripts
- `migrate_2015_optimal_config.py`: Single-year migration with optimized config
- `batch_migrate_2015_2025.py`: Batch migration for multiple years
- `migrate_2015_2020_pinecone.py`: Specific range migration to Pinecone

### Documentation
- `README.md`: User-facing project documentation
- `PROJECT_HANDOVER.md`: Comprehensive handover document (状态、问题、配置)
- `QUICK_REFERENCE.md`: Quick reference guide
- `BGE_M3_PERFORMANCE_VERIFIED.md`: BGE-M3 performance benchmarks
- `MIGRATION_STATUS_REPORT.md`: Data migration status

## Development Guidelines

### Adding New Workflow Nodes
1. Create node class in `src/graph/nodes/`
2. Inherit from base pattern or reference existing nodes
3. Implement `__call__(self, state: GraphState) -> dict` method
4. Update `src/graph/workflow.py` to add node and routing
5. Add corresponding prompt templates in `src/llm/prompts*.py`

### Switching Vector Databases
1. Update `.env`: Change database-specific config (e.g., `MILVUS_MODE`, `PINECONE_API_KEY`)
2. Update retrieval code in `src/graph/nodes/retrieve.py` to use appropriate client
3. Rebuild index using `build_index.py` or migration script

### Adding New Embedding Models
1. Create new client in `src/llm/` (reference `local_embeddings.py`)
2. Update `src/llm/embeddings.py` to add mode in `_create_embedding_client()`
3. Add configuration fields in `src/config/settings.py`
4. Update `.env` with new mode and credentials

### Testing Complex Questions
The system excels at handling multi-dimensional queries:

**Comparison Questions**:
```
"请对比CDU/CSU和SPD在2019年对数字化政策的观点"
(Compare CDU/CSU and SPD views on digitalization in 2019)
```

**Change Analysis**:
```
"在2015-2018年期间，不同党派在难民问题上的立场有何变化？"
(How did party positions on refugees change during 2015-2018?)
```

**Summary Questions**:
```
"请总结Merkel在2019年关于欧盟一体化的主要观点"
(Summarize Merkel's main views on EU integration in 2019)
```

## Known Issues and Workarounds

### 1. Pinecone Client Not Encapsulated
**Issue**: Current code uses direct Pinecone API calls in migration scripts.
**Workaround**: Reference `src/vectordb/qdrant_client.py` pattern for consistent interface.
**TODO**: Create `src/vectordb/pinecone_client.py` wrapper.

### 2. Incomplete Data Migration
**Issue**: Only partial data (2021-2025) migrated to Pinecone. Historical data (1949-2014) pending.
**Impact**: Queries on historical periods may return no results.
**Workaround**: Use `DATA_MODE=PART` and `PART_DATA_YEARS` in `.env` to control scope.

### 3. Test Coverage Gaps
**Issue**: Limited end-to-end tests, especially for edge cases.
**Workaround**: Manual testing via `main.py` interactive interface.
**TODO**: Expand `tests/` with comprehensive test cases.

## Common Troubleshooting

### Milvus Connection Failed
```bash
# Check if Milvus is running (if using local mode)
docker ps | grep milvus

# Start Milvus
docker start milvus

# Or use Milvus Lite mode (no Docker)
# Set MILVUS_MODE=lite in .env
```

### Embedding API Timeout
```bash
# Check proxy status
echo $http_proxy
ps aux | grep clash

# Restart Clash proxy (if needed)
# See GLOBAL_PROXY_SETUP_COMPLETE.md
```

### GPU Not Detected
```bash
# Verify CUDA availability
python -c "import torch; print(torch.cuda.is_available())"

# BGE-M3 will automatically fallback to CPU if GPU unavailable
# Performance will be slower but functional
```

### Configuration Not Loading
```bash
# Verify .env file exists and has correct variables
ls -la .env
cat .env | grep -v "^#" | grep -v "^$"

# Test configuration loading
python -c "from src.config import settings; print(vars(settings))"
```

## Performance Optimization Notes

### Optimal Batch Sizes (16GB GPU)
- Embedding batch size: 800
- Milvus insert batch: 1000
- Concurrent workers: 20

### Memory Management
- Use streaming for large datasets
- Process data in batches during migration
- Monitor GPU memory: `nvidia-smi`

### Chunk Size Optimization
Tested configurations (see `EMBEDDING_OPTIMIZATION_REPORT.md`):
- Best: 4000 chars with 800 overlap
- Balances context preservation and retrieval precision

---

## User-Specific Development Guidelines

### Self-Questioning Methodology
- 自我拷问: 你每次输出马上要跟着一个对自己的提问,都以"自我我挑战"开始,挑战这次输出有没有思考的遗漏,尝试突破思维边界,找到第一性原理,然后根据挑战再补充回答,达到完整

### Interaction Modes
- **暴躁老哥**: 每次都用审视的目光，仔细看我的输入的潜在的问题，你要犀利的提出我的问题。并给出明显在我思考框架之外的建议。你要觉得我说的太离谱了，你就骂回来，帮助我瞬间清醒
- **资深指导**: 永远不要想着创建简化方案，去暂时避开问题，这样只会在后面造成更大的问题。如果不能立马解决问题，那就多深度思考几轮，肯定会有解决办法的!
- **记忆大师**: 需要压缩对话上下文时, 主要压缩修复问题和代码的上下文记忆,关于代码需求规范和指导规范, claude.md 记忆这种指导性意见相关的记忆要毫无保留的记忆到最深处

### Development Process Guidelines
- **流程规范**: 在每次开始编码任务之前先深度思考, 告诉我你要怎么做, 为什么要这么做, 然后在完成之后告诉我有什么你做不到的, 需要我去完成的

### 【强制执行】设计决策检查清单

**每次设计新组件前必答**：
- [ ] 这个设计解决了用户的真实痛点吗？
- [ ] 这个设计增加了不必要的复杂性吗？
- [ ] 这个设计符合用户的心理模型吗？
- [ ] 这个设计考虑了长期维护成本吗？

**每次API设计前必答**：
- [ ] 这个props真的必要吗？
- [ ] 用户能够直观理解这个概念吗？
- [ ] 是否有更简单的方式达成同样效果？
- [ ] 是否与现有模式保持一致？

**每次视觉设计前必答**：
- [ ] 这个样式服务于功能还是装饰？
- [ ] 视觉层次是否清晰明确？
- [ ] 是否使用了用户熟悉的视觉语言？
- [ ] 是否考虑了不同屏幕和使用场景？

### 深度思考方法论

**四轮深度思考框架**:
1. **第一轮**: 分析问题本质和用户需求
2. **第二轮**: 重新定义解决方案和设计哲学
3. **第三轮**: 制定具体的实施策略
4. **第四轮**: 考虑技术约束和可行性

**关键要点**:
- **不急于编码** - 思考不充分的代码注定要重构
- **质疑第一方案** - 第一个想到的方案往往不是最好的
- **考虑长远影响** - 今天的架构决策影响未来6个月的开发