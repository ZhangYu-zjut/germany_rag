# 使用指南

## 快速开始

### 1. 运行主分析脚本

```bash
python analyze_metadata.py
```

这将：
- 解析 `data/pp_json_49-21/` 目录下的所有JSON文件
- 生成三个输出文件：
  - `group.csv` - 党派映射表
  - `map.csv` - 议员-党派映射表
  - `summary_report.txt` - 详细统计报告

### 2. 探索数据

```bash
python explore_data.py
```

这将显示：
- 党派分布分析
- 议员党派变动情况
- 主要党派的时间线
- 知名政治家的查询示例

## 生成文件说明

### group.csv (党派映射表)
包含53个不同党派的德语-中文对照表

**主要内容：**
```csv
德语名称,中文名称,出现次数,备注
CDU/CSU,基民盟/基社盟,123903,
SPD,社民党,117196,
FDP,自民党,50415,
...
```

### map.csv (议员-党派动态映射表)
包含35,861条记录，记录9,291位议员的党派归属

**主要内容：**
```csv
议员姓名,年份,所属党派,备注
Dr. Angela Merkel,2005,CDU/CSU,
Helmut Schmidt,1974,SPD,
...
```

### summary_report.txt (统计报告)
包含完整的数据分析，包括：
- 53个党派的详细统计
- 9,291位发言人的排名
- 1949-2021年每年的党派分布
- 议员党派变动情况分析

## 数据统计概览

### 基本统计
- **时间跨度**: 1949-2021年（73年）
- **JSON文件**: 73个
- **总记录数**: 809,157条
- **党派数量**: 53个
- **发言人数**: 9,291位

### 主要党派分布
| 党派 | 记录数 | 占比 |
|------|--------|------|
| 无党派/未标注 | 443,291 | 54.78% |
| CDU/CSU | 123,903 | 15.31% |
| SPD | 117,196 | 14.48% |
| FDP | 50,415 | 6.23% |
| 绿党(各种) | 34,595 | 4.28% |
| DIE LINKE | 15,932 | 1.97% |

### 发言次数Top 5
1. Vizepräsident Westphal - 17,182次
2. Vizepräsident Dr. Jaeger - 17,026次
3. Vizepräsident Dr. Schmitt-Vockenhausen - 15,807次
4. Vizepräsidentin Petra Pau - 15,404次
5. Vizepräsident Dr. Schmid - 14,440次

## 常见问题

### Q1: 为什么有这么多None值？
A: None通常代表：
- 议会主席/副主席的程序性发言
- 未标注党派的发言
- 独立议员或无党派人士

### Q2: 如何查找特定议员的信息？
A: 使用explore_data.py脚本的选项4，或者直接在map.csv中搜索议员姓名

### Q3: 党派名称为什么有多种写法？
A: 德国政党在不同时期可能有不同的正式名称，例如：
- 绿党: GRÜNE, DIE GRÜNEN, Grüne/Bündnis 90, BÜNDNIS 90/DIE GRÜNEN
- 左翼党: PDS, PDS/Linke Liste, DIE LINKE

### Q4: 如何处理党派变动？
A: map.csv中会标注"该年属于多个党派"，表示议员在该年发生了党派变更

## 高级用法

### 查询特定年份的党派分布
```python
import csv

year = "2021"
with open('map.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    data = [row for row in reader if row['年份'] == year]
    
parties = set(row['所属党派'] for row in data)
print(f"{year}年活跃党派: {parties}")
```

### 统计某党派的议员数量变化
```python
import csv
from collections import defaultdict

party = "SPD"
year_speakers = defaultdict(set)

with open('map.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['所属党派'] == party:
            year_speakers[row['年份']].add(row['议员姓名'])

for year in sorted(year_speakers.keys()):
    print(f"{year}: {len(year_speakers[year])} 位议员")
```

### 找出所有有党派变动的议员
```python
import csv
from collections import defaultdict

speaker_parties = defaultdict(set)

with open('map.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        speaker = row['议员姓名']
        party = row['所属党派']
        if party != 'None':
            speaker_parties[speaker].add(party)

# 找出有变动的议员
changed = {s: p for s, p in speaker_parties.items() if len(p) > 1}
print(f"共有 {len(changed)} 位议员有党派变动")
```

## 数据可视化建议

### 1. 党派势力演变图
使用matplotlib绘制1949-2021年各党派发言次数的时间序列图

### 2. 议员流动桑基图
展示议员在不同党派之间的流动情况

### 3. 词云图
分析不同党派的高频发言主题

### 4. 网络关系图
构建议员互动网络和党派联盟关系

## 扩展方向

1. **爬取官方数据**: 从Bundestag官网爬取更完整的议员档案
2. **文本分析**: 对speech内容进行NLP分析
3. **情感分析**: 分析不同党派的发言情感倾向
4. **主题建模**: 使用LDA等方法提取议题主题
5. **预测模型**: 建立党派支持率预测模型

## 注意事项

1. CSV文件使用UTF-8-BOM编码，可在Excel中直接打开
2. 议员姓名可能包含特殊字符和职位标注
3. 同名议员通过地区或其他标识符区分
4. 部分历史党派已不存在或已合并

## 脚本维护

如需添加新的党派翻译，请修改 `analyze_metadata.py` 中的 `create_group_mapping()` 函数。

## 许可和引用

本项目基于德国联邦议院公开数据进行分析，仅供学术研究使用。
如需引用，请注明数据来源和分析工具。
