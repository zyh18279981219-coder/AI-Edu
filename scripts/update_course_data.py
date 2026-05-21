#!/usr/bin/env python3
"""
更新课程数据，为只有视频的节点添加 PDF 路径
"""
import json
import shutil
from datetime import datetime

def update_node_resources(node):
    """递归更新节点资源"""
    modified = False
    
    # 处理当前节点
    if node.get('name') == '大数据生命周期':
        resource_path = node.get('resource_path', [])
        
        # 如果是列表且只有视频
        if isinstance(resource_path, list):
            has_pdf = any(not r.startswith('http') for r in resource_path if isinstance(r, str))
            if not has_pdf:
                # 添加 PDF 路径
                resource_path.insert(0, 'data/Book/1.PDF')
                node['resource_path'] = resource_path
                modified = True
                print(f'已为节点 "{node["name"]}" 添加 PDF: data/Book/1.PDF')
    
    # 递归处理子节点
    for child_key in ['children', 'grandchildren', 'great-grandchildren']:
        if child_key in node:
            for child in node[child_key]:
                if update_node_resources(child):
                    modified = True
    
    return modified

def main():
    course_file = 'data/course/big_data.json'
    
    # 备份原文件
    backup_file = f'data/course/big_data_before_pdf_update_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json.bak'
    shutil.copy(course_file, backup_file)
    print(f'已备份原文件到: {backup_file}')
    print()
    
    # 读取课程数据
    with open(course_file, 'r', encoding='utf-8') as f:
        course_data = json.load(f)
    
    # 更新节点
    print('更新课程数据...')
    modified = update_node_resources(course_data)
    
    if modified:
        # 保存更新后的数据
        with open(course_file, 'w', encoding='utf-8') as f:
            json.dump(course_data, f, ensure_ascii=False, indent=2)
        print()
        print('课程数据已更新')
    else:
        print()
        print('没有需要更新的节点')
    
    print()
    print('完成！')

if __name__ == '__main__':
    main()
