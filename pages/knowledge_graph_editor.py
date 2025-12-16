#!/usr/bin/env python3
"""
知识图谱编辑页面 - Streamlit UI
支持查看、编辑、添加和删除知识图谱中的主题、维度和标签
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

import streamlit as st

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# 知识图谱文件路径
KG_FILE = project_root / "data" / "knowledge_graph_extended.json"
KG_BACKUP_DIR = project_root / "data" / "kg_backups"

# 页面配置
st.set_page_config(
    page_title="知识图谱编辑器",
    page_icon="🔗",
    layout="wide"
)


def load_knowledge_graph():
    """加载知识图谱"""
    if KG_FILE.exists():
        with open(KG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"_metadata": {}, "topics": {}, "dimensions": {}, "tags": {}}


def save_knowledge_graph(kg_data):
    """保存知识图谱"""
    # 创建备份
    KG_BACKUP_DIR.mkdir(exist_ok=True)
    backup_file = KG_BACKUP_DIR / f"kg_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    if KG_FILE.exists():
        with open(KG_FILE, 'r', encoding='utf-8') as f:
            old_data = f.read()
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(old_data)

    # 更新元数据
    kg_data["_metadata"]["updated"] = datetime.now().isoformat()
    kg_data["_metadata"]["topics_count"] = len(kg_data.get("topics", {}))

    # 保存
    with open(KG_FILE, 'w', encoding='utf-8') as f:
        json.dump(kg_data, f, ensure_ascii=False, indent=2)

    return backup_file


def main():
    st.title("🔗 知识图谱编辑器")
    st.markdown("管理德国议会演讲检索知识图谱（主题 → 维度 → 标签）")

    # 加载知识图谱
    if 'kg_data' not in st.session_state:
        st.session_state.kg_data = load_knowledge_graph()

    kg_data = st.session_state.kg_data

    # 侧边栏 - 统计信息
    with st.sidebar:
        st.header("📊 统计信息")
        st.metric("主题数", len(kg_data.get("topics", {})))
        st.metric("维度数", len(kg_data.get("dimensions", {})))
        st.metric("标签数", len(kg_data.get("tags", {})))

        st.markdown("---")

        # 保存按钮
        if st.button("💾 保存更改", type="primary"):
            backup = save_knowledge_graph(kg_data)
            st.success(f"✅ 已保存！备份: {backup.name}")

        # 重新加载按钮
        if st.button("🔄 重新加载"):
            st.session_state.kg_data = load_knowledge_graph()
            st.rerun()

        st.markdown("---")
        st.markdown("**文件路径:**")
        st.caption(str(KG_FILE))

    # 主要内容区域 - 三个标签页
    tab1, tab2, tab3, tab4 = st.tabs(["📁 主题管理", "📂 维度管理", "🏷️ 标签管理", "📋 JSON预览"])

    # ========== 主题管理 ==========
    with tab1:
        st.header("📁 主题管理 (Topics)")

        topics = kg_data.get("topics", {})

        # 添加新主题
        with st.expander("➕ 添加新主题", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                new_topic_name = st.text_input("主题名称 (德语)", key="new_topic_name", placeholder="例如: Wirtschaftspolitik")
            with col2:
                new_topic_desc = st.text_input("描述 (中文)", key="new_topic_desc", placeholder="例如: 经济政策")

            new_topic_keywords = st.text_input("关键词 (逗号分隔)", key="new_topic_keywords", placeholder="例如: Wirtschaft, Ökonomie, 经济")
            new_topic_dims = st.text_input("关联维度 (逗号分隔)", key="new_topic_dims", placeholder="例如: Steuerpolitik, Haushaltspolitik")

            if st.button("添加主题"):
                if new_topic_name and new_topic_name not in topics:
                    topics[new_topic_name] = {
                        "description": new_topic_desc,
                        "keywords": [k.strip() for k in new_topic_keywords.split(",") if k.strip()],
                        "dimensions": [d.strip() for d in new_topic_dims.split(",") if d.strip()]
                    }
                    kg_data["topics"] = topics
                    st.success(f"✅ 已添加主题: {new_topic_name}")
                    st.rerun()
                elif new_topic_name in topics:
                    st.error("❌ 主题已存在")

        # 显示现有主题
        st.markdown("### 现有主题")
        for topic_name, topic_data in topics.items():
            with st.expander(f"**{topic_name}** - {topic_data.get('description', '')}", expanded=False):
                col1, col2 = st.columns([3, 1])

                with col1:
                    # 编辑描述
                    new_desc = st.text_input(
                        "描述",
                        value=topic_data.get("description", ""),
                        key=f"topic_desc_{topic_name}"
                    )
                    if new_desc != topic_data.get("description", ""):
                        topic_data["description"] = new_desc

                    # 编辑关键词
                    keywords_str = ", ".join(topic_data.get("keywords", []))
                    new_keywords = st.text_input(
                        "关键词",
                        value=keywords_str,
                        key=f"topic_keywords_{topic_name}"
                    )
                    topic_data["keywords"] = [k.strip() for k in new_keywords.split(",") if k.strip()]

                    # 编辑关联维度
                    dims_str = ", ".join(topic_data.get("dimensions", []))
                    new_dims = st.text_input(
                        "关联维度",
                        value=dims_str,
                        key=f"topic_dims_{topic_name}"
                    )
                    topic_data["dimensions"] = [d.strip() for d in new_dims.split(",") if d.strip()]

                with col2:
                    st.markdown("<br/>", unsafe_allow_html=True)
                    if st.button("🗑️ 删除", key=f"del_topic_{topic_name}"):
                        del topics[topic_name]
                        st.rerun()

    # ========== 维度管理 ==========
    with tab2:
        st.header("📂 维度管理 (Dimensions)")

        dimensions = kg_data.get("dimensions", {})

        # 添加新维度
        with st.expander("➕ 添加新维度", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                new_dim_name = st.text_input("维度名称 (德语)", key="new_dim_name")
            with col2:
                new_dim_desc = st.text_input("描述 (中文)", key="new_dim_desc")

            new_dim_keywords = st.text_input("关键词 (逗号分隔)", key="new_dim_keywords")
            new_dim_topics = st.text_input("所属主题 (逗号分隔)", key="new_dim_topics")
            new_dim_tags = st.text_input("包含标签 (逗号分隔)", key="new_dim_tags")

            if st.button("添加维度"):
                if new_dim_name and new_dim_name not in dimensions:
                    dimensions[new_dim_name] = {
                        "description": new_dim_desc,
                        "keywords": [k.strip() for k in new_dim_keywords.split(",") if k.strip()],
                        "parent_topics": [t.strip() for t in new_dim_topics.split(",") if t.strip()],
                        "tags": [t.strip() for t in new_dim_tags.split(",") if t.strip()]
                    }
                    kg_data["dimensions"] = dimensions
                    st.success(f"✅ 已添加维度: {new_dim_name}")
                    st.rerun()

        # 显示现有维度
        st.markdown("### 现有维度")

        # 按主题分组显示
        topic_dims = {}
        for dim_name, dim_data in dimensions.items():
            for topic in dim_data.get("parent_topics", ["未分类"]):
                if topic not in topic_dims:
                    topic_dims[topic] = []
                topic_dims[topic].append((dim_name, dim_data))

        for topic, dims_list in sorted(topic_dims.items()):
            st.markdown(f"#### 🏷️ {topic}")
            for dim_name, dim_data in dims_list:
                with st.expander(f"**{dim_name}** - {dim_data.get('description', '')}", expanded=False):
                    col1, col2 = st.columns([3, 1])

                    with col1:
                        new_desc = st.text_input(
                            "描述",
                            value=dim_data.get("description", ""),
                            key=f"dim_desc_{dim_name}"
                        )
                        dim_data["description"] = new_desc

                        keywords_str = ", ".join(dim_data.get("keywords", []))
                        new_keywords = st.text_input(
                            "关键词",
                            value=keywords_str,
                            key=f"dim_keywords_{dim_name}"
                        )
                        dim_data["keywords"] = [k.strip() for k in new_keywords.split(",") if k.strip()]

                        topics_str = ", ".join(dim_data.get("parent_topics", []))
                        new_topics = st.text_input(
                            "所属主题",
                            value=topics_str,
                            key=f"dim_topics_{dim_name}"
                        )
                        dim_data["parent_topics"] = [t.strip() for t in new_topics.split(",") if t.strip()]

                        tags_str = ", ".join(dim_data.get("tags", []))
                        new_tags = st.text_input(
                            "包含标签",
                            value=tags_str,
                            key=f"dim_tags_{dim_name}"
                        )
                        dim_data["tags"] = [t.strip() for t in new_tags.split(",") if t.strip()]

                    with col2:
                        st.markdown("<br/>", unsafe_allow_html=True)
                        if st.button("🗑️ 删除", key=f"del_dim_{dim_name}"):
                            del dimensions[dim_name]
                            st.rerun()

    # ========== 标签管理 ==========
    with tab3:
        st.header("🏷️ 标签管理 (Tags)")

        tags = kg_data.get("tags", {})

        # 添加新标签
        with st.expander("➕ 添加新标签", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                new_tag_name = st.text_input("标签名称", key="new_tag_name")
            with col2:
                new_tag_desc = st.text_input("描述 (中文)", key="new_tag_desc")

            new_tag_keywords = st.text_input("关键词 (逗号分隔)", key="new_tag_keywords")
            new_tag_dims = st.text_input("所属维度 (逗号分隔)", key="new_tag_dims")
            new_tag_years = st.text_input("触发年份 (逗号分隔)", key="new_tag_years", placeholder="例如: 2015, 2016, 2017")
            new_tag_parties = st.text_input("相关党派 (逗号分隔)", key="new_tag_parties", placeholder="例如: CDU/CSU, SPD, Grüne")
            new_tag_queries = st.text_area("扩展查询模板 (每行一个)", key="new_tag_queries", placeholder="{party} 关键词 {year}")

            if st.button("添加标签"):
                if new_tag_name and new_tag_name not in tags:
                    tags[new_tag_name] = {
                        "description": new_tag_desc,
                        "keywords": [k.strip() for k in new_tag_keywords.split(",") if k.strip()],
                        "parent_dimensions": [d.strip() for d in new_tag_dims.split(",") if d.strip()],
                        "trigger_conditions": {
                            "years": [int(y.strip()) for y in new_tag_years.split(",") if y.strip().isdigit()],
                            "parties": [p.strip() for p in new_tag_parties.split(",") if p.strip()],
                            "keywords": []
                        },
                        "weight": 1.0,
                        "expansion_queries": [q.strip() for q in new_tag_queries.split("\n") if q.strip()]
                    }
                    kg_data["tags"] = tags
                    st.success(f"✅ 已添加标签: {new_tag_name}")
                    st.rerun()

        # 显示现有标签
        st.markdown("### 现有标签")

        # 搜索过滤
        search_term = st.text_input("🔍 搜索标签", key="tag_search")

        filtered_tags = {k: v for k, v in tags.items() if search_term.lower() in k.lower() or search_term.lower() in v.get("description", "").lower()}

        st.caption(f"显示 {len(filtered_tags)}/{len(tags)} 个标签")

        for tag_name, tag_data in sorted(filtered_tags.items()):
            with st.expander(f"**{tag_name}** - {tag_data.get('description', '')}", expanded=False):
                col1, col2 = st.columns([4, 1])

                with col1:
                    new_desc = st.text_input(
                        "描述",
                        value=tag_data.get("description", ""),
                        key=f"tag_desc_{tag_name}"
                    )
                    tag_data["description"] = new_desc

                    keywords_str = ", ".join(tag_data.get("keywords", []))
                    new_keywords = st.text_input(
                        "关键词",
                        value=keywords_str,
                        key=f"tag_keywords_{tag_name}"
                    )
                    tag_data["keywords"] = [k.strip() for k in new_keywords.split(",") if k.strip()]

                    dims_str = ", ".join(tag_data.get("parent_dimensions", []))
                    new_dims = st.text_input(
                        "所属维度",
                        value=dims_str,
                        key=f"tag_dims_{tag_name}"
                    )
                    tag_data["parent_dimensions"] = [d.strip() for d in new_dims.split(",") if d.strip()]

                    # 触发条件
                    st.markdown("**触发条件:**")
                    trigger = tag_data.get("trigger_conditions", {})

                    years_str = ", ".join(str(y) for y in trigger.get("years", []))
                    new_years = st.text_input(
                        "触发年份",
                        value=years_str,
                        key=f"tag_years_{tag_name}"
                    )
                    trigger["years"] = [int(y.strip()) for y in new_years.split(",") if y.strip().isdigit()]

                    parties_str = ", ".join(trigger.get("parties", []))
                    new_parties = st.text_input(
                        "相关党派",
                        value=parties_str,
                        key=f"tag_parties_{tag_name}"
                    )
                    trigger["parties"] = [p.strip() for p in new_parties.split(",") if p.strip()]

                    tag_data["trigger_conditions"] = trigger

                    # 权重
                    new_weight = st.slider(
                        "权重",
                        min_value=0.5,
                        max_value=3.0,
                        value=float(tag_data.get("weight", 1.0)),
                        step=0.1,
                        key=f"tag_weight_{tag_name}"
                    )
                    tag_data["weight"] = new_weight

                    # 扩展查询
                    queries_str = "\n".join(tag_data.get("expansion_queries", []))
                    new_queries = st.text_area(
                        "扩展查询模板",
                        value=queries_str,
                        key=f"tag_queries_{tag_name}",
                        height=100
                    )
                    tag_data["expansion_queries"] = [q.strip() for q in new_queries.split("\n") if q.strip()]

                with col2:
                    st.markdown("<br/><br/>", unsafe_allow_html=True)
                    if st.button("🗑️ 删除", key=f"del_tag_{tag_name}"):
                        del tags[tag_name]
                        st.rerun()

    # ========== JSON预览 ==========
    with tab4:
        st.header("📋 JSON 预览")

        col1, col2 = st.columns([1, 1])

        with col1:
            if st.button("📥 导出JSON"):
                json_str = json.dumps(kg_data, ensure_ascii=False, indent=2)
                st.download_button(
                    label="下载 knowledge_graph.json",
                    data=json_str,
                    file_name="knowledge_graph_export.json",
                    mime="application/json"
                )

        with col2:
            uploaded_file = st.file_uploader("📤 导入JSON", type=["json"])
            if uploaded_file:
                try:
                    imported_data = json.load(uploaded_file)
                    if st.button("确认导入"):
                        st.session_state.kg_data = imported_data
                        st.success("✅ 导入成功！")
                        st.rerun()
                except Exception as e:
                    st.error(f"导入失败: {e}")

        st.markdown("---")
        st.json(kg_data)


if __name__ == "__main__":
    main()
