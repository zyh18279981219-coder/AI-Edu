#!/usr/bin/env python3
"""
审计课程知识点与 PDF 资源
"""
import json
import os
from pathlib import Path
from collections import defaultdict

def collect_nodes(node, parent_path='', results=None):
    """递归收集所有节点及其资源"""
    if results is None:
        results = {
            'nodes': [],
            'pdf_paths': set(),
            'video_paths': set()
        }
    
    name = node.get('name', '')
    resource_path = node.get('resource_path', '')
    
    # 处理 resource_path
    pdf_list = []
    video_list = []
    
    if isinstance(resource_path, str) and resource_path:
        if resource_path.startswith('http'):
            video_list.append(resource_path)
        else:
            pdf_list.append(resource_path)
    elif isinstance(resource_path, list):
        for r in resource_path:
            if isinstance(r, str):
                if r.startswith('http'):
                    video_list.append(r)
                else:
                    pdf_list.append(r)
    
    # 记录节点信息
    node_info = {
        'name': name,
        'path': f'{parent_path}/{name}' if parent_path else name,
        'pdfs': pdf_list,
        'videos': video_list,
        'has_resources': bool(pdf_list or video_list)
    }
    results['nodes'].append(node_info)
    
    if pdf_list:
        results['pdf_paths'].update(pdf_list)
    if video_list:
        results['video_paths'].update(video_list)
    
    # 递归处理子节点
    for child_key in ['children', 'grandchildren', 'great-grandchildren']:
        if child_key in node:
            for child in node[child_key]:
                collect_nodes(child, f'{parent_path}/{name}' if parent_path else name, results)
    
    return results

def main():
    # 读取课程数据
    course_file = 'data/course/big_data.json'
    with open(course_file, 'r', encoding='utf-8') as f:
        course_data = json.load(f)
    
    # 收集所有节点
    results = collect_nodes(course_data)
    
    print('=' * 80)
    print('课程资源审计报告')
    print('=' * 80)
    print()
    
    # 统计总体情况
    total_nodes = len(results['nodes'])
    nodes_with_resources = sum(1 for n in results['nodes'] if n['has_resources'])
    nodes_without_resources = total_nodes - nodes_with_resources
    
    print(f'总节点数: {total_nodes}')
    print(f'有资源的节点: {nodes_with_resources}')
    print(f'无资源的节点: {nodes_without_resources}')
    print(f'唯一 PDF 路径数: {len(results["pdf_paths"])}')
    print(f'唯一视频路径数: {len(results["video_paths"])}')
    print()
    
    # 检查 PDF 文件存在性
    existing_pdfs = []
    missing_pdfs = []
    
    for pdf_path in sorted(results['pdf_paths']):
        if os.path.exists(pdf_path):
            existing_pdfs.append(pdf_path)
        else:
            missing_pdfs.append(pdf_path)
    
    print('-' * 80)
    print('PDF 文件状态')
    print('-' * 80)
    print(f'存在的 PDF: {len(existing_pdfs)}')
    print(f'缺失的 PDF: {len(missing_pdfs)}')
    print()
    
    if missing_pdfs:
        print('缺失的 PDF 文件列表:')
        for pdf in missing_pdfs:
            print(f'  - {pdf}')
        print()
    
    # 统计节点与 PDF 的关系
    print('-' * 80)
    print('节点与 PDF 关系')
    print('-' * 80)
    
    nodes_with_pdf = [n for n in results['nodes'] if n['pdfs']]
    nodes_with_multiple_pdfs = [n for n in nodes_with_pdf if len(n['pdfs']) > 1]
    nodes_with_only_video = [n for n in results['nodes'] if n['videos'] and not n['pdfs']]
    nodes_with_both = [n for n in results['nodes'] if n['pdfs'] and n['videos']]
    
    print(f'有 PDF 的节点: {len(nodes_with_pdf)}')
    print(f'有多个 PDF 的节点: {len(nodes_with_multiple_pdfs)}')
    print(f'只有视频的节点: {len(nodes_with_only_video)}')
    print(f'同时有 PDF 和视频的节点: {len(nodes_with_both)}')
    print()
    
    if nodes_with_multiple_pdfs:
        print('有多个 PDF 的节点:')
        for node in nodes_with_multiple_pdfs[:10]:
            print(f'  - {node["name"]}: {len(node["pdfs"])} 个 PDF')
        if len(nodes_with_multiple_pdfs) > 10:
            print(f'  ... 还有 {len(nodes_with_multiple_pdfs) - 10} 个')
        print()
    
    # 找出需要生成 PDF 的节点
    print('-' * 80)
    print('需要处理的节点')
    print('-' * 80)
    
    # 1. 完全没有 PDF 的可学习节点（有视频但没 PDF）
    need_pdf_nodes = []
    for node in results['nodes']:
        if not node['pdfs'] and node['videos']:
            need_pdf_nodes.append(node)
    
    print(f'只有视频需要补充 PDF 的节点: {len(need_pdf_nodes)}')
    if need_pdf_nodes:
        for node in need_pdf_nodes[:10]:
            print(f'  - {node["name"]}')
        if len(need_pdf_nodes) > 10:
            print(f'  ... 还有 {len(need_pdf_nodes) - 10} 个')
    print()
    
    # 2. PDF 路径存在但文件缺失的节点
    nodes_with_missing_pdf = []
    for node in results['nodes']:
        for pdf in node['pdfs']:
            if pdf in missing_pdfs:
                nodes_with_missing_pdf.append((node, pdf))
                break
    
    print(f'PDF 路径存在但文件缺失的节点: {len(nodes_with_missing_pdf)}')
    if nodes_with_missing_pdf:
        for node, pdf in nodes_with_missing_pdf[:10]:
            print(f'  - {node["name"]}: {pdf}')
        if len(nodes_with_missing_pdf) > 10:
            print(f'  ... 还有 {len(nodes_with_missing_pdf) - 10} 个')
    print()
    
    # 保存详细报告
    report = {
        'summary': {
            'total_nodes': total_nodes,
            'nodes_with_resources': nodes_with_resources,
            'nodes_without_resources': nodes_without_resources,
            'total_pdf_paths': len(results['pdf_paths']),
            'existing_pdfs': len(existing_pdfs),
            'missing_pdfs': len(missing_pdfs),
            'nodes_with_multiple_pdfs': len(nodes_with_multiple_pdfs)
        },
        'missing_pdfs': missing_pdfs,
        'nodes_with_missing_pdf': [
            {'name': node['name'], 'path': node['path'], 'pdf': pdf}
            for node, pdf in nodes_with_missing_pdf
        ],
        'nodes_need_pdf': [
            {'name': node['name'], 'path': node['path']}
            for node in need_pdf_nodes
        ],
        'nodes_with_multiple_pdfs': [
            {'name': node['name'], 'path': node['path'], 'pdfs': node['pdfs']}
            for node in nodes_with_multiple_pdfs
        ]
    }
    
    with open('data/pdf_audit_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print('详细报告已保存到: data/pdf_audit_report.json')
    print()

if __name__ == '__main__':
    main()
