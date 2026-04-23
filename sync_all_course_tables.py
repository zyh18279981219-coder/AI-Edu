"""
完整同步所有课程相关表：course_metadata, course_nodes, resources
"""
import pymysql
import json
from datetime import datetime

DB_CONFIG = {
    'host': '123.56.144.178',
    'port': 3306,
    'user': 'zyh',
    'password': '123456',
    'database': 'ai_education',
    'charset': 'utf8mb4',
    'connect_timeout': 10
}

def sync_all_tables():
    print("=" * 80)
    print("完整同步课程数据到所有相关表")
    print("=" * 80)
    
    # 读取本地JSON
    print("\n1. 读取本地课程JSON...")
    with open('data/course/big_data_true.json', 'r', encoding='utf-8') as f:
        course_data = json.load(f)
    print("   ✓ 成功读取 big_data_true.json")
    
    # 连接数据库
    print("\n2. 连接数据库...")
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    print("   ✓ 连接成功")
    
    try:
        course_id = 'course_big_data'
        
        # 步骤1: 更新 course_metadata
        print("\n3. 更新 course_metadata 表...")
        metadata_payload = {
            'root_name': course_data.get('name', '大数据分析'),
            'structure': course_data
        }
        
        cursor.execute("""
            UPDATE course_metadata 
            SET additional_data = %s, updated_at = CURRENT_TIMESTAMP 
            WHERE course_id = %s
            ORDER BY metadata_id DESC LIMIT 1
        """, (json.dumps(metadata_payload, ensure_ascii=False), course_id))
        print(f"   ✓ 更新了 {cursor.rowcount} 条记录")
        
        # 步骤2: 清空并重建 course_nodes 表
        print("\n4. 重建 course_nodes 表...")
        cursor.execute("DELETE FROM course_nodes WHERE course_id = %s", (course_id,))
        print(f"   ✓ 删除了 {cursor.rowcount} 条旧记录")
        
        nodes_inserted = 0
        
        def insert_node(node_id, node_name, node_path, depth, parent_id, payload):
            nonlocal nodes_inserted
            # 使用完整路径作为唯一node_id，避免重名冲突
            unique_node_id = '->'.join(node_path)
            cursor.execute("""
                INSERT INTO course_nodes 
                (course_id, node_id, node_name, node_path_json, depth, parent_node_id, payload_json, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (
                course_id,
                unique_node_id,
                node_name,
                json.dumps(node_path, ensure_ascii=False),
                depth,
                parent_id,
                json.dumps(payload, ensure_ascii=False)
            ))
            nodes_inserted += 1
        
        # 插入章节、小节、知识点
        for chapter in course_data.get('children', []):
            chapter_name = chapter.get('name')
            chapter_path = [chapter_name]
            chapter_id = '->'.join(chapter_path)
            insert_node(chapter_id, chapter_name, chapter_path, 0, None, chapter)
            
            for section in chapter.get('grandchildren', []):
                section_name = section.get('name')
                section_path = [chapter_name, section_name]
                section_id = '->'.join(section_path)
                insert_node(section_id, section_name, section_path, 1, chapter_id, section)
                
                for kp in section.get('great-grandchildren', []):
                    kp_name = kp.get('name')
                    kp_path = [chapter_name, section_name, kp_name]
                    kp_id = '->'.join(kp_path)
                    insert_node(kp_id, kp_name, kp_path, 2, section_id, kp)
        
        print(f"   ✓ 插入了 {nodes_inserted} 个节点")
        
        # 步骤3: 清空并重建 resources 表
        print("\n5. 重建 resources 表...")
        cursor.execute("DELETE FROM resources WHERE course_id = %s", (course_id,))
        print(f"   ✓ 删除了 {cursor.rowcount} 条旧记录")
        
        resources_inserted = 0
        
        def insert_resources(node_id, resources_list):
            nonlocal resources_inserted
            if not resources_list:
                return
            
            if isinstance(resources_list, str):
                resources_list = [resources_list] if resources_list.strip() else []
            
            for resource_path in resources_list:
                if not resource_path or not str(resource_path).strip():
                    continue
                
                resource_path = str(resource_path).strip()
                
                # 判断资源类型
                if resource_path.startswith('http://') or resource_path.startswith('https://'):
                    if '.m3u8' in resource_path:
                        resource_type = 'm3u8'
                    else:
                        resource_type = 'video'
                elif resource_path.lower().endswith('.pdf'):
                    resource_type = 'pdf'
                else:
                    resource_type = 'unknown'
                
                cursor.execute("""
                    INSERT INTO resources 
                    (course_id, node_id, resource_path, resource_type, payload_json, is_deleted, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (
                    course_id,
                    node_id,
                    resource_path,
                    resource_type,
                    json.dumps({'path': resource_path, 'type': resource_type}, ensure_ascii=False)
                ))
                resources_inserted += 1
        
        # 插入所有资源
        for chapter in course_data.get('children', []):
            chapter_name = chapter.get('name')
            chapter_id = chapter_name  # 使用简单名称作为node_id
            insert_resources(chapter_id, chapter.get('resource_path', []))
            
            for section in chapter.get('grandchildren', []):
                section_name = section.get('name')
                section_id = f"{chapter_name}->{section_name}"
                insert_resources(section_id, section.get('resource_path', []))
                
                for kp in section.get('great-grandchildren', []):
                    kp_name = kp.get('name')
                    kp_id = f"{chapter_name}->{section_name}->{kp_name}"
                    insert_resources(kp_id, kp.get('resource_path', []))
        
        print(f"   ✓ 插入了 {resources_inserted} 个资源")
        
        # 提交事务
        print("\n6. 提交事务...")
        conn.commit()
        print("   ✓ 所有更改已保存")
        
        # 验证
        print("\n7. 验证数据...")
        cursor.execute("SELECT COUNT(*) FROM course_nodes WHERE course_id = %s", (course_id,))
        nodes_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM resources WHERE course_id = %s AND is_deleted = 0", (course_id,))
        resources_count = cursor.fetchone()[0]
        
        print(f"   ✓ course_nodes: {nodes_count} 条")
        print(f"   ✓ resources: {resources_count} 条")
        
        print("\n" + "=" * 80)
        print("✓ 所有课程表同步完成！")
        print("=" * 80)
        
    except Exception as e:
        conn.rollback()
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    print("\n⚠️  此操作将完全重建 course_nodes 和 resources 表")
    response = input("确认继续? (yes/no): ")
    
    if response.lower() in ['yes', 'y']:
        sync_all_tables()
    else:
        print("操作已取消")
