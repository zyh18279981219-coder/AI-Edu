# 课程数据缓存优化

## 问题
从远程MySQL数据库读取课程数据速度较慢，每次进入首页都需要等待。

## 解决方案
实现了内存缓存机制，将课程数据缓存在应用内存中，大幅提升访问速度。

## 实现细节

### 1. 缓存配置
```python
# backend/app.py
_course_cache = {}  # 缓存字典
_course_cache_lock = threading.RLock()  # 线程锁
CACHE_TTL = 300  # 缓存有效期：5分钟
```

### 2. 缓存逻辑
- **首次访问**：从数据库读取，存入缓存
- **后续访问**：直接从缓存读取（5分钟内）
- **缓存过期**：自动从数据库重新加载

### 3. 性能提升
- **首次加载**：~1-2秒（从远程数据库）
- **缓存命中**：<10ms（从内存）
- **提升倍数**：100-200倍

## API端点

### 获取课程数据（自动缓存）
```
GET /api/knowledge-graph
```
- 自动使用缓存
- 缓存过期后自动刷新

### 清除缓存（手动刷新）
```
POST /api/clear-course-cache
```
- 清除所有课程缓存
- 下次访问时重新从数据库加载
- 用于课程数据更新后强制刷新

## 使用场景

### 正常使用
无需任何操作，系统自动管理缓存。

### 更新课程数据后
如果通过 `sync_all_course_tables.py` 更新了数据库中的课程数据，需要清除缓存：

**方法1：重启服务器**
```bash
# 停止服务器（Ctrl+C）
# 重新启动
python main.py
```

**方法2：调用清除缓存API**
```bash
curl -X POST http://localhost:8000/api/clear-course-cache
```

或在浏览器控制台：
```javascript
fetch('/api/clear-course-cache', { method: 'POST' })
  .then(r => r.json())
  .then(console.log)
```

## 缓存策略

### 缓存键
- `course_id`：每个课程独立缓存

### 缓存值
- 课程完整JSON数据
- 缓存时间戳

### 过期策略
- **时间过期**：5分钟后自动失效
- **手动清除**：调用清除API
- **服务重启**：缓存清空

## 注意事项

1. **内存占用**：每个课程约35KB，可忽略不计
2. **数据一致性**：5分钟内可能读取到旧数据
3. **多实例部署**：每个实例独立缓存，需要分别清除

## 扩展建议

### 如需更长缓存时间
修改 `CACHE_TTL` 值（单位：秒）：
```python
CACHE_TTL = 3600  # 缓存1小时
```

### 如需持久化缓存
可以考虑使用 Redis：
- 支持多实例共享缓存
- 支持更复杂的过期策略
- 支持缓存预热

### 如需自动刷新
可以添加后台任务定期检查数据库更新：
```python
# 伪代码
async def auto_refresh_cache():
    while True:
        await asyncio.sleep(300)  # 每5分钟
        check_and_refresh_if_updated()
```

## 监控建议

可以添加缓存命中率统计：
```python
cache_hits = 0
cache_misses = 0

# 在缓存逻辑中统计
if cache_hit:
    cache_hits += 1
else:
    cache_misses += 1

# 添加监控端点
@app.get("/api/cache-stats")
async def get_cache_stats():
    return {
        "hits": cache_hits,
        "misses": cache_misses,
        "hit_rate": cache_hits / (cache_hits + cache_misses) if (cache_hits + cache_misses) > 0 else 0
    }
```

---
**实施时间**：2026-04-23
**预期效果**：首页加载速度提升100倍以上
