# 🚀 快速参考卡片

## 📋 项目基本信息

- **项目名称**: 德国议会智能问答RAG系统
- **技术栈**: LangGraph + BGE-M3 + Pinecone + Gemini 2.5 Pro
- **数据范围**: 1949-2021年德国议会演讲记录（85个JSON文件，~1.9GB）
- **当前状态**: 开发中，部分功能已完成

## 🔑 关键配置

### API密钥位置
`.env` 文件（已添加到.gitignore）

### 核心模型
- **LLM**: Gemini 2.5 Pro (via Evolink API)
- **Embedding**: BGE-M3 本地 (1024维，GPU加速)
- **向量数据库**: Pinecone (`german-bge` 索引)

### 最佳配置参数
- **分块大小**: 4000字符
- **重叠大小**: 800字符
- **Embedding批次**: 800（16GB GPU）
- **处理速度**: 300+ vectors/秒

## 📊 数据状态

| 年份范围 | 状态 | 向量数量 |
|---------|------|---------|
| 2015-2020 | 🔄 部分完成 | ~400,000+ |
| 2021-2025 | ✅ 已完成 | 237,389 |
| 1949-2014 | ⏸️ 待处理 | - |

## 🚀 快速启动

```bash
# 1. 激活环境
source venv/bin/activate

# 2. 检查配置
python -c "from src.config import settings; print(settings.embedding_mode)"

# 3. 运行问答系统
python main.py
```

## 📁 关键文件

- **配置**: `src/config/settings.py`
- **主程序**: `main.py`
- **迁移脚本**: `migrate_2015_optimal_config.py`
- **文档**: `PROJECT_HANDOVER.md`

## ⚠️ 重要提醒

1. ⚠️ **API密钥**: 需要配置 `.env` 文件
2. ⚠️ **数据迁移**: 部分数据未完成迁移
3. ⚠️ **网络代理**: WSL2需要配置代理
4. ⚠️ **GPU推荐**: BGE-M3需要GPU加速（可选）

## 📞 详细文档

查看 `PROJECT_HANDOVER.md` 获取完整信息。







