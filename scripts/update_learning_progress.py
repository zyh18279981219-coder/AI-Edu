"""
更新学习进度数据 - 为首页学习定位添加测试数据
"""
import sqlite3
import json
from datetime import datetime

def update_learning_progress():
    """更新课程节点的完成标记"""
    conn = sqlite3.connect('data/app.db')
    cursor = conn.cursor()
    
    # 获取课程数据
    cursor.execute("SELECT course_id, payload_json FROM courses WHERE course_id='course_big_data'")
    row = cursor.fetchone()
    
    if not row:
        print("❌ 未找到课程数据")
        return
    
    course_id, payload_json = row
    graph_data = json.loads(payload_json)
    
    print(f"📚 正在更新课程: {course_id}")
    print(f"📊 章节数量: {len(graph_data.get('children', []))}")
    
    # 统计信息
    updated_count = 0
    
    # 遍历所有章节
    for chapter_idx, chapter in enumerate(graph_data.get('children', [])):
        chapter_name = chapter.get('name', '')
        print(f"\n📖 章节 {chapter_idx + 1}: {chapter_name}")
        
        # 第一章：标记前3个小节的知识点为已完成
        if chapter_idx == 0:
            for section_idx, section in enumerate(chapter.get('grandchildren', [])):
                section_name = section.get('name', '')
                print(f"  📄 小节 {section_idx + 1}: {section_name}")
                
                # 第一个小节：全部完成
                if section_idx == 0:
                    for point_idx, point in enumerate(section.get('great-grandchildren', [])):
                        point['flag'] = '1'
                        updated_count += 1
                        print(f"    ✅ 知识点 {point_idx + 1}: {point.get('name', '')} - 已完成")
                
                # 第二个小节：全部完成
                elif section_idx == 1:
                    for point_idx, point in enumerate(section.get('great-grandchildren', [])):
                        point['flag'] = '1'
                        updated_count += 1
                        print(f"    ✅ 知识点 {point_idx + 1}: {point.get('name', '')} - 已完成")
                
                # 第三个小节：完成前2个知识点
                elif section_idx == 2:
                    for point_idx, point in enumerate(section.get('great-grandchildren', [])[:2]):
                        point['flag'] = '1'
                        updated_count += 1
                        print(f"    ✅ 知识点 {point_idx + 1}: {point.get('name', '')} - 已完成")
                    
                    # 剩余知识点标记为未完成
                    for point_idx, point in enumerate(section.get('great-grandchildren', [])[2:], start=2):
                        point['flag'] = '0'
                        print(f"    ⭕ 知识点 {point_idx + 1}: {point.get('name', '')} - 未完成")
                
                # 第四个小节及之后：全部未完成
                else:
                    for point_idx, point in enumerate(section.get('great-grandchildren', [])):
                        point['flag'] = '0'
                        print(f"    ⭕ 知识点 {point_idx + 1}: {point.get('name', '')} - 未完成")
    
    # 更新数据库
    updated_payload = json.dumps(graph_data, ensure_ascii=False)
    updated_at = datetime.now().isoformat()
    
    cursor.execute(
        "UPDATE courses SET payload_json = ?, updated_at = ? WHERE course_id = ?",
        (updated_payload, updated_at, course_id)
    )
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ 更新完成！共标记 {updated_count} 个知识点为已完成")
    print(f"📅 更新时间: {updated_at}")
    print("\n💡 现在刷新首页，应该可以看到学习定位数据了！")

if __name__ == '__main__':
    update_learning_progress()
