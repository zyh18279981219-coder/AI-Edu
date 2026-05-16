"""
通知系统基础版

聚合作业、测验、学习计划等通知来源
"""

import logging
import os
from datetime import datetime, timedelta
from time import monotonic
from typing import List, Dict
from DatabaseModule.database_factory import DatabaseFactory

logger = logging.getLogger(__name__)


class NotificationService:
    _cache: dict[tuple[str, int], tuple[float, List[Dict]]] = {}
    _cache_ttl_seconds = float(os.getenv("NOTIFICATION_CACHE_SECONDS", "30"))

    """通知服务"""
    
    def __init__(self):
        self.store = DatabaseFactory.get_store()
    
    def get_recent_notifications(self, username: str, limit: int = 10) -> List[Dict]:
        """
        获取用户最近的通知
        
        聚合来源：
        1. 作业提交反馈
        2. 测验成绩
        3. 学习活动
        
        Returns:
            [
                {
                    "icon": "📝",
                    "title": "通知标题",
                    "time": "相对时间",
                    "timestamp": "ISO时间戳",
                    "type": "notification_type",
                    "link": "跳转链接"
                }
            ]
        """
        cache_key = (username, limit)
        cached = self._cache.get(cache_key)
        if cached and monotonic() - cached[0] < self._cache_ttl_seconds:
            return cached[1]

        notifications = []
        
        # 1. 获取作业提交通知
        homework_notifications = self._get_homework_notifications(username)
        notifications.extend(homework_notifications)
        
        # 2. 获取测验通知
        quiz_notifications = self._get_quiz_notifications(username)
        notifications.extend(quiz_notifications)
        
        # 3. 获取学习活动通知
        activity_notifications = self._get_activity_notifications(username)
        notifications.extend(activity_notifications)
        
        # 按时间排序
        notifications.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # 限制数量
        result = notifications[:limit]
        self._cache[cache_key] = (monotonic(), result)
        return result
    
    def _get_homework_notifications(self, username: str) -> List[Dict]:
        """获取作业相关通知"""
        notifications = []
        
        try:
            with self.store._lock, self.store.connection() as conn:
                cursor = conn.cursor()
                
                # 查询最近的作业提交（7天内）
                seven_days_ago = datetime.now() - timedelta(days=7)
                
                cursor.execute("""
                    SELECT 
                        hs.id,
                        hs.assignment_id,
                        hs.submitted_at,
                        hs.status,
                        hs.ai_score,
                        hs.teacher_score,
                        ha.title
                    FROM homework_submissions hs
                    LEFT JOIN homework_assignments ha ON hs.assignment_id = ha.id
                    WHERE hs.student_username = %s 
                    AND hs.submitted_at >= %s
                    ORDER BY hs.submitted_at DESC
                    LIMIT 5
                """, (username, seven_days_ago))
                
                rows = cursor.fetchall()
                cursor.close()
                
                for row in rows:
                    if isinstance(row, dict):
                        submission_id = row['id']
                        assignment_id = row['assignment_id']
                        submitted_at = row['submitted_at']
                        status = row['status']
                        ai_score = row['ai_score']
                        teacher_score = row['teacher_score']
                        title = row['title']
                    else:
                        submission_id = row[0]
                        assignment_id = row[1]
                        submitted_at = row[2]
                        status = row[3]
                        ai_score = row[4]
                        teacher_score = row[5]
                        title = row[6]
                    
                    # 转换时间
                    if isinstance(submitted_at, str):
                        submitted_at = datetime.fromisoformat(submitted_at.replace('Z', '+00:00'))
                    
                    # 根据状态生成通知
                    if status == 'graded' and teacher_score is not None:
                        notifications.append({
                            'icon': '🎉',
                            'title': f'作业已评分：{title}',
                            'time': self._format_relative_time(submitted_at),
                            'timestamp': submitted_at.isoformat(),
                            'type': 'homework_graded',
                            'link': f'/student/homework'
                        })
                    elif status == 'submitted' and ai_score is not None:
                        notifications.append({
                            'icon': '🤖',
                            'title': f'AI评分完成：{title}',
                            'time': self._format_relative_time(submitted_at),
                            'timestamp': submitted_at.isoformat(),
                            'type': 'homework_ai_graded',
                            'link': f'/student/homework'
                        })
                    else:
                        notifications.append({
                            'icon': '📝',
                            'title': f'作业已提交：{title}',
                            'time': self._format_relative_time(submitted_at),
                            'timestamp': submitted_at.isoformat(),
                            'type': 'homework_submitted',
                            'link': f'/student/homework'
                        })
                
        except Exception as e:
            logger.error(f"获取作业通知失败 {username}: {e}")
        
        return notifications
    
    def _get_quiz_notifications(self, username: str) -> List[Dict]:
        """获取测验相关通知"""
        notifications = []
        
        try:
            with self.store._lock, self.store.connection() as conn:
                cursor = conn.cursor()
                
                # 查询最近的测验记录（7天内）
                seven_days_ago = datetime.now() - timedelta(days=7)
                
                cursor.execute("""
                    SELECT 
                        attempt_id,
                        node_id,
                        score,
                        total,
                        passed,
                        created_at
                    FROM quiz_attempts
                    WHERE username = %s 
                    AND created_at >= %s
                    ORDER BY created_at DESC
                    LIMIT 5
                """, (username, seven_days_ago))
                
                rows = cursor.fetchall()
                cursor.close()
                
                for row in rows:
                    if isinstance(row, dict):
                        node_id = row['node_id']
                        score = row['score']
                        total = row['total']
                        passed = row['passed']
                        created_at = row['created_at']
                    else:
                        node_id = row[1]
                        score = row[2]
                        total = row[3]
                        passed = row[4]
                        created_at = row[5]
                    
                    # 转换时间
                    if isinstance(created_at, str):
                        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    
                    # 计算分数百分比
                    score_percent = int((score / total * 100)) if total > 0 else 0
                    
                    if passed:
                        notifications.append({
                            'icon': '✅',
                            'title': f'测验通过：{node_id} ({score_percent}分)',
                            'time': self._format_relative_time(created_at),
                            'timestamp': created_at.isoformat(),
                            'type': 'quiz_passed',
                            'link': f'/student/course-content?node={node_id}'
                        })
                    else:
                        notifications.append({
                            'icon': '📊',
                            'title': f'测验完成：{node_id} ({score_percent}分)',
                            'time': self._format_relative_time(created_at),
                            'timestamp': created_at.isoformat(),
                            'type': 'quiz_completed',
                            'link': f'/student/course-content?node={node_id}'
                        })
                
        except Exception as e:
            logger.error(f"获取测验通知失败 {username}: {e}")
        
        return notifications
    
    def _get_activity_notifications(self, username: str) -> List[Dict]:
        """获取学习活动通知"""
        notifications = []
        
        try:
            with self.store._lock, self.store.connection() as conn:
                cursor = conn.cursor()
                
                # 查询最近的学习活动（7天内，排除登录）
                seven_days_ago = datetime.now() - timedelta(days=7)
                
                cursor.execute("""
                    SELECT 
                        activity_type,
                        activity_details,
                        created_at
                    FROM user_activity_log
                    WHERE username = %s 
                    AND created_at >= %s
                    AND activity_type != 'login'
                    ORDER BY created_at DESC
                    LIMIT 3
                """, (username, seven_days_ago))
                
                rows = cursor.fetchall()
                cursor.close()
                
                for row in rows:
                    if isinstance(row, dict):
                        activity_type = row['activity_type']
                        activity_details = row['activity_details']
                        created_at = row['created_at']
                    else:
                        activity_type = row[0]
                        activity_details = row[1]
                        created_at = row[2]
                    
                    # 转换时间
                    if isinstance(created_at, str):
                        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    
                    # 根据活动类型生成通知
                    icon_map = {
                        'quiz': '📝',
                        'complete_node': '✅',
                        'submit_homework': '📤',
                        'chat': '💬',
                        'summary': '📄'
                    }
                    
                    title_map = {
                        'quiz': '完成测验',
                        'complete_node': '完成知识点学习',
                        'submit_homework': '提交作业',
                        'chat': 'AI助教对话',
                        'summary': '生成学习总结'
                    }
                    
                    notifications.append({
                        'icon': icon_map.get(activity_type, '📌'),
                        'title': title_map.get(activity_type, '学习活动'),
                        'time': self._format_relative_time(created_at),
                        'timestamp': created_at.isoformat(),
                        'type': f'activity_{activity_type}',
                        'link': '/student/home'
                    })
                
        except Exception as e:
            logger.error(f"获取活动通知失败 {username}: {e}")
        
        return notifications
    
    def _format_relative_time(self, dt: datetime) -> str:
        """格式化相对时间"""
        now = datetime.now()
        
        # 确保 dt 是 naive datetime（无时区信息）
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        
        delta = now - dt
        
        if delta.days > 30:
            return f'{delta.days // 30}个月前'
        elif delta.days > 0:
            return f'{delta.days}天前'
        elif delta.seconds >= 3600:
            return f'{delta.seconds // 3600}小时前'
        elif delta.seconds >= 60:
            return f'{delta.seconds // 60}分钟前'
        else:
            return '刚刚'
