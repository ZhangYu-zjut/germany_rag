# 德国议会RAG智能问答系统 - Streamlit UI 使用指南

## 📋 概述

这是一个基于Streamlit构建的交互式Web界面，用于演示德国议会RAG智能问答系统的能力。

---

## 🌐 在线访问（推荐）

系统已部署在 Railway 云平台，可直接在线使用：

| 服务 | 链接 | 说明 |
|------|------|------|
| **UI界面** | https://miraculous-patience-production-c8e2.up.railway.app | Streamlit前端界面 |
| **API服务** | https://germanyrag-production.up.railway.app | FastAPI后端API |
| **API文档** | https://germanyrag-production.up.railway.app/docs | Swagger交互式文档 |

### 使用步骤

1. 打开 [UI界面链接](https://miraculous-patience-production-c8e2.up.railway.app)
2. 在输入框输入问题（支持德语和中文）
3. 可选：开启右侧"🧠 深度分析"模式获取更全面结果
4. 点击"🚀 提交问题"
5. 等待1-3分钟获取答案

### 注意事项

- **标准模式**: 预计1-3分钟返回结果
- **深度分析模式**: 预计10-20分钟，启用知识图谱扩展，生成更详细的分析
- 时间显示为北京时间（UTC+8）

---

## 🚀 本地启动（开发模式）

### 1. 确保环境准备就绪

```bash
# 激活虚拟环境
source venv/bin/activate

# 确保streamlit已安装（如未安装）
pip install streamlit>=1.28.0
```

### 2. 启动UI应用

```bash
# 方式1：使用streamlit命令（推荐）
streamlit run streamlit_app.py

# 方式2：直接执行（如果遇到权限问题，先执行 chmod +x streamlit_app.py）
./streamlit_app.py
```

### 3. 访问Web界面

启动后，浏览器会自动打开，或手动访问：
- **本地地址**: http://localhost:8501
- **网络地址**: http://192.168.x.x:8501（可供局域网内其他设备访问）

## 🎯 功能特性

### 核心功能

1. **智能问答界面**
   - 支持德语和中文输入
   - 实时显示处理进度（5个步骤）
   - 3分钟左右得到完整答案

2. **结构化答案展示**
   - 主答案：完整的德语回答
   - 详细信息（可展开查看）：
     - 处理时间、检索文档数、覆盖年份
     - 提取的查询参数（年份、党派、发言人等）
     - 子问题分解（如有）
     - 年份分布柱状图
     - 检索来源示例（前5个）

3. **对话历史管理**
   - 自动保存每次问答
   - 时间戳记录
   - 一键清除历史

4. **示例问题**
   - 侧边栏提供4个示例问题
   - 点击即可快速测试

### UI组件

#### 侧边栏 (Sidebar)
- **系统信息**: 数据范围、检索方式、LLM型号、向量数据库
- **示例问题**: 4个预设问题，点击即用
- **清除历史**: 重置对话记录
- **系统状态**: 显示workflow是否已初始化

#### 主界面
- **标题区**: 系统名称（中德双语）
- **对话历史**: 问答记录，带时间戳
- **输入区**: 文本框 + 提交按钮
- **页脚**: 版权和技术栈信息

## 📊 使用示例

### 示例1：单年份查询
```
问题: 2015年基民盟对难民政策的立场是什么？
系统处理流程:
  1. 分析问题意图 → complex
  2. 提取参数 → year: 2015, party: CDU/CSU, topic: 难民政策
  3. 分解子问题 → 生成10+个子问题
  4. 检索文档 → 使用Query Expansion检索
  5. 生成答案 → 德语完整答案
```

### 示例2：多年份对比
```
问题: Wie haben sich die Diskussionen über Klimaschutz zwischen 2019 und 2021 entwickelt?
系统处理流程:
  1. 意图: complex
  2. 参数: years: 2019-2021, topic: Klimaschutz
  3. 子问题: 30+个（覆盖2019、2020、2021各年）
  4. 检索: 多年份分层检索
  5. 答案: 展示变化趋势
```

## ⚙️ 系统配置

### 环境变量（.env）
UI应用会自动加载以下配置：
```bash
# LLM配置
GEMINI_API_KEY=your_api_key
LLM_BASE_URL=your_llm_proxy_url

# Pinecone配置
PINECONE_VECTOR_DATABASE_API_KEY=your_pinecone_key

# Embedding配置（本地BGE-M3）
EMBEDDING_MODE=local  # 支持: local, openai, vertex, deepinfra
```

### 性能参数
- **Query Expansion**: 每个子问题扩展5个变体
- **检索Top-K**: 50
- **多年份策略**: 启用（每年最多5个文档）
- **并发Retrieval**: 禁用（本地BGE-M3线程安全问题）

## 🔧 故障排除

### 问题1: 启动失败
```bash
# 错误: ModuleNotFoundError: No module named 'streamlit'
# 解决: 安装streamlit
pip install streamlit>=1.28.0
```

### 问题2: 初始化失败
```bash
# 错误: "系统初始化失败，请检查配置"
# 可能原因:
#   1. .env文件缺失或配置错误
#   2. Pinecone API密钥无效
#   3. BGE-M3模型未下载
# 解决:
#   1. 检查 .env 文件是否存在
#   2. 验证 PINECONE_VECTOR_DATABASE_API_KEY
#   3. 运行 python test_langgraph_complete.py 测试基础功能
```

### 问题3: 处理超时
```bash
# 问题: 处理时间超过5分钟
# 原因: 并发Query Expansion可能未启用
# 解决: 检查 src/graph/nodes/query_expansion.py
#       确保 enable_concurrent=True
```

### 问题4: 答案质量问题
```bash
# 问题: 答案不准确或缺失年份
# 检查:
#   1. max_sub_questions 是否 >= 40
#   2. Query Expansion 是否正常工作
#   3. 查看"详细信息"中的年份分布
```

## 📈 性能指标

| 指标 | 目标 | 当前状态 |
|------|------|---------|
| 单问题处理时间 | <3分钟 | ~3.1分钟 |
| Recall召回率 | >80% | 80% (12/15) |
| 年份覆盖率（2019-2024） | 100% | 100% |
| 并发Query Expansion | 启用 | ✅ 启用 |
| 并发Retrieval | 启用 | ⏸️ 暂时禁用 |

## 🎨 UI设计说明

### 设计理念
- **简洁专业**: 不过度设计，专注核心功能
- **透明可见**: 展示系统思考过程
- **体验友好**: 清晰的进度提示

### 颜色方案
- **主色**: #1f77b4（蓝色） - 代表专业、可信
- **辅色**: #4caf50（绿色） - 代表成功、答案
- **警告**: #f44336（红色） - 代表错误
- **信息**: #ff9800（橙色） - 代表元数据

### 交互流程
```
用户输入问题
  ↓
点击"提交问题"
  ↓
st.status显示5步处理进度
  ↓
显示答案（带时间戳）
  ↓
可展开查看详细信息
```

## 📝 开发说明

### 文件结构
```
streamlit_app.py           # 主应用文件
├── initialize_session_state()  # 初始化会话状态
├── load_workflow()             # 加载LangGraph工作流
├── process_question()          # 处理用户问题
├── display_chat_history()      # 显示对话历史
└── main()                      # 主函数
```

### 扩展开发
如需添加新功能：
1. **新页面**: 使用 `st.sidebar.selectbox()` 添加页面切换
2. **新图表**: 使用 `st.line_chart()`, `st.area_chart()` 等
3. **导出功能**: 使用 `st.download_button()` 导出答案为PDF/Markdown
4. **用户反馈**: 添加 `st.feedback()` 收集用户评价

## 🚧 已知限制

1. **处理时间**: 单问题约3分钟（受LLM调用和检索速度限制）
2. **并发限制**: 本地BGE-M3不支持并发Retrieval（云端API可解决）
3. **历史记录**: 仅保存在session_state，刷新页面会丢失
4. **多用户**: Streamlit默认单实例，多用户共享session

## 🔮 未来优化方向

1. **性能优化**
   - 启用Retrieval并发（迁移到云端Embedding API）
   - 缓存常见问题答案
   - 异步处理，支持进度条

2. **功能增强**
   - 持久化对话历史（数据库存储）
   - 答案导出功能（PDF、Markdown）
   - 用户反馈机制
   - 多语言界面切换

3. **部署优化**
   - Docker容器化
   - 云端部署（GCP Cloud Run）
   - 负载均衡和多实例

## 📞 联系支持

如遇问题，请检查：
1. 日志文件（Streamlit会显示详细错误）
2. `src/utils/logger.py` 的日志输出
3. 运行 `python test_langgraph_complete.py` 验证基础功能

---

**© 2025 德国议会RAG智能问答系统**
**Powered by LangGraph + Gemini 2.5 Pro + Pinecone + Streamlit**
