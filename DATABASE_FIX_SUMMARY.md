# 数据库读取问题修复总结

## 问题描述
前端通过 `/api/knowledge-graph` 接口从数据库读取课程数据时，资源映射一直不正确。

## 根本原因
`DatabaseModule/mysql_store.py` 中的 `get_course_payload()` 方法存在SQL查询缺陷：

```python
# 问题代码
cursor.execute(
    "SELECT additional_data FROM course_metadata WHERE course_id = %s LIMIT 1",
    (course_id,)
)
```

当数据库中存在多条 `course_metadata` 记录时（metadata_id 1, 2, 3），`LIMIT 1` 没有配合 `ORDER BY` 使用，导致可能返回旧的记录而不是最新的记录。

## 修复方案

### 1. 修复 SQL 查询（已完成）
在 `DatabaseModule/mysql_store.py` 的 `get_course_payload()` 方法中添加 `ORDER BY metadata_id DESC`：

```python
# 修复后的代码
cursor.execute(
    "SELECT additional_data FROM course_metadata WHERE course_id = %s ORDER BY metadata_id DESC LIMIT 1",
    (course_id,)
)
```

**文件**: `DatabaseModule/mysql_store.py` (第1390行)

### 2. 同步最新课程数据（已完成）
将 `big_data_true.json` 的数据同步到数据库的 `course_metadata` 表：

```bash
python run_sync_auto.py
```

这确保了数据库中的 `additional_data` 字段包含完整的课程结构和资源信息。

### 3. 恢复 API 端点使用数据库（已完成）
将 `/api/knowledge-graph` 端点从临时的直接读取JSON改回使用数据库：

```python
# backend/app.py (第1353-1365行)
@app.get("/api/knowledge-graph")
async def get_knowledge_graph(session_id: Optional[str] = Cookie(None)):
    """Return knowledge graph payload (从数据库读取)."""
    try:
        session = get_current_user(session_id)
        course_id, graph_data = _load_course_graph_entity_only(session)
        if not graph_data:
            raise HTTPException(status_code=404, detail="Knowledge graph not found")
        logging.info(f"从数据库加载课程数据: course_id={course_id}")
        return graph_data
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"加载课程数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load knowledge graph: {str(e)}")
```

## 验证结果

### 数据库数据验证
- ✅ 数据库中有3条 `course_metadata` 记录（metadata_id: 1, 2, 3）
- ✅ 最新记录（metadata_id=3）包含完整的课程数据
- ✅ `additional_data` 字段大小: 37312 bytes
- ✅ 课程ID: `course_big_data`

### 资源统计验证
从数据库读取的课程数据包含：
- **PDF文档**: 47个
- **视频资源**: 48个
- **总计**: 95个资源

这与 `big_data_true.json` 中的资源数量完全一致。

## 相关文件

### 修改的文件
1. `DatabaseModule/mysql_store.py` - 添加 ORDER BY 子句
2. `backend/app.py` - 恢复使用数据库读取

### 测试脚本
1. `test_database_endpoint.py` - 测试数据库读取功能
2. `run_sync_auto.py` - 自动同步课程数据到数据库
3. `count_json_resources.py` - 统计JSON文件中的资源数量
4. `debug_get_course_payload.py` - 调试 get_course_payload 方法

## 注意事项

1. **course_id 命名**: 数据库中使用 `course_big_data`，而不是 `big_data`
2. **资源字段名**: JSON结构使用 `resource_path` 而不是 `resources`
3. **JSON结构层级**: 
   - `children` (章节)
   - `grandchildren` (小节)
   - `great-grandchildren` (知识点)

## 后续建议

1. 考虑在 `course_metadata` 表中添加唯一约束，避免同一 `course_id` 有多条记录
2. 或者在应用层面确保只保留最新的记录
3. 添加数据库迁移脚本，自动清理旧记录

## 测试步骤

1. 启动后端服务
2. 学生登录系统
3. 进入课程内容页面
4. 点击任意知识点
5. 验证资源列表显示正确的PDF和视频资源

---
**修复完成时间**: 2026-04-23
**修复人员**: Kiro AI Assistant
