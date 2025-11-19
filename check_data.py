import csv
import json

# 检查map.csv中的数据
print("检查map.csv中的数据:")
print("="*80)

with open('map.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    
    # 查找Dr. Althammer
    althammer_rows = [row for row in reader if 'Althammer' in row['议员姓名']]
    print(f"\nDr. Althammer共{len(althammer_rows)}条记录")
    print("1983年的记录:")
    for row in althammer_rows:
        if row['年份'] == '1983':
            print(f"  {row['议员姓名']:30s} - {row['年份']}: {row['所属党派']}")

# 重新打开文件查找Schily
with open('map.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    schily_rows = [row for row in reader if 'Schily' in row['议员姓名'] or '„' in row['议员姓名']]
    print(f"\nSchily相关记录共{len(schily_rows)}条")
    print("所有Schily记录:")
    for row in schily_rows:
        print(f"  '{row['议员姓名']}' - {row['年份']}: {row['所属党派']}")

# 检查JSON原始数据
print("\n\n检查pp_1983.json中的原始数据:")
print("="*80)

with open('data/pp_json_49-21/pp_1983.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    
    # 查找Dr. Althammer (1983年)
    althammer_items = [item for item in data['transcript'] 
                      if 'metadata' in item 
                      and 'Althammer' in item['metadata'].get('speaker', '')
                      and item['metadata'].get('year', '') == '1983']
    print(f"\nDr. Althammer在1983年JSON中共{len(althammer_items)}条")
    if althammer_items:
        meta = althammer_items[0]['metadata']
        print(f"  speaker: '{meta['speaker']}'  group: '{meta['group']}'  year: {meta['year']}")
    
    # 查找Schily (1983年)
    schily_items = [item for item in data['transcript']
                   if 'metadata' in item 
                   and item['metadata'].get('year', '') == '1983'
                   and ('Schily' in item['metadata'].get('speaker', '') or '„' in item['metadata'].get('speaker', ''))]
    print(f"\nSchily在1983年JSON中共{len(schily_items)}条")
    
    # 显示所有不同的Schily speaker名称
    schily_names = set()
    for item in schily_items:
        schily_names.add(item['metadata']['speaker'])
    
    print("不同的Schily姓名写法:")
    for name in sorted(schily_names):
        # 获取该名称的group
        items_with_name = [item for item in schily_items if item['metadata']['speaker'] == name]
        if items_with_name:
            group = items_with_name[0]['metadata']['group']
            print(f"  '{name}' -> group: '{group}' (共{len(items_with_name)}条)")
