"""
学习连续天数服务

记录和计算用户的连续学习天数
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, Optional
from DatabaseModule.database_factory import DatabaseFactory

logger = logging.getLogger(__name__)


class LearningStreakService:
    """学习连续天数服务"""
    
    def __init__(self):
        self.store = DatabaseFactory.get_store()
    
    def log_activity(self, username: str, activity_type: str, activity_details: str = None) -> bool:
        """
        记录用户学习活动
        
        Args:
            username: 用户名
            activity_type: 活动类型 (login, complete_node, submit_homework, quiz, chat, etc.)
            activity_details: 活动详情（可选）
        
        Returns:
            是否记录成功
        """
        try:
            today = date.today()
            
            with self.store._lock, self.store.connection() as conn:
                cursor = conn.cursor()
                
                # 使用 INSERT IGNORE 避免重复记录同一天的同类型活动
                cursor.execute("""
                    INSERT IGNORE INTO user_activity_log 
                    (username, activity_date, activity_type, activity_details, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                """, (username, today, activity_type, activity_details, datetime.now()))
                
                conn.commit()
                cursor.close()
                return True
                
        except Exception as e:
            logger.error(f"记录学习活动失败 {username}: {e}")
            return False
    
    def get_streak(self, username: str) -> Dict:
        """
        获取用户的学习连续天数
        
        Returns:
            {
                "current_streak": 当前连续天数,
                "longest_streak": 历史最长连续天数,
                "last_activity_date": 最后活动日期,
                "total_days": 总学习天数
            }
        """
        try:
            with self.store._lock, self.store.connection() as conn:
                cursor = conn.cursor()
                
                # 获取所有学习日期（去重）
                cursor.execute("""
                    SELECT DISTINCT activity_date 
                    FROM user_activity_log 
                    WHERE username = %s 
                    ORDER BY activity_date DESC
                """, (username,))
                
                rows = cursor.fetchall()
                cursor.close()
                
                if not rows:
                    return {
                        "current_streak": 0,
                        "longest_streak": 0,
                        "last_activity_date": None,
                        "total_days": 0
                    }
                
                # 提取日期列表
                dates = []
                for row in rows:
                    if isinstance(row, dict):
                        dates.append(row['activity_date'])
                    else:
                        dates.append(row[0])
                
                # 转换为 date 对象
                dates = [d if isinstance(d, date) else datetime.strptime(str(d), '%Y-%m-%d').date() for d in dates]
                dates.sort(reverse=True)
                
                total_days = len(dates)
                last_activity_date = dates[0].isoformat() if dates else None
                
                # 计算当前连续天数
                current_streak = self._calculate_current_streak(dates)
                
                # 计算历史最长连续天数
                longest_streak = self._calculate_longest_streak(dates)
                
                return {
                    "current_streak": current_streak,
                    "longest_streak": longest_streak,
                    "last_activity_date": last_activity_date,
                    "total_days": total_days
                }
                
        except Exception as e:
            logger.error(f"获取学习连续天数失败 {username}: {e}")
            return {
                "current_streak": 0,
                "longest_streak": 0,
                "last_activity_date": None,
                "total_days": 0
            }
    
    def _calculate_current_streak(self, dates: list) -> int:
        """计算当前连续天数"""
        if not dates:
            return 0
        
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        # 如果最后活动日期不是今天或昨天，连续天数为 0
        if dates[0] != today and dates[0] != yesterday:
            return 0
        
        # 从最近的日期开始计算连续天数
        streak = 0
        expected_date = dates[0]
        
        for activity_date in dates:
            if activity_date == expected_date:
                streak += 1
                expected_date = activity_date - timedelta(days=1)
            else:
                break
        
        return streak
    
    def _calculate_longest_streak(self, dates: list) -> int:
        """计算历史最长连续天数"""
        if not dates:
            return 0
        
        max_streak = 1
        current_streak = 1
        
        for i in range(1, len(dates)):
            # 检查是否连续
            if dates[i-1] - dates[i] == timedelta(days=1):
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 1
        
        return max_streak
    
    def get_activity_summary(self, username: str, days: int = 30) -> Dict:
        """
        获取用户最近 N 天的活动摘要
        
        Returns:
            {
                "total_activities": 总活动次数,
                "activity_by_type": {活动类型: 次数},
                "active_days": 活跃天数
            }
        """
        try:
            start_date = date.today() - timedelta(days=days)
            
            with self.store._lock, self.store.connection() as conn:
                cursor = conn.cursor()
                
                # 获取活动统计
                cursor.execute("""
                    SELECT 
                        activity_type,
                        COUNT(*) as count,
                        COUNT(DISTINCT activity_date) as active_days
                    FROM user_activity_log 
                    WHERE username = %s AND activity_date >= %s
                    GROUP BY activity_type
                """, (username, start_date))
                
                rows = cursor.fetchall()
                cursor.close()
                
                activity_by_type = {}
                total_activities = 0
                active_days_set = set()
                
                for row in rows:
                    if isinstance(row, dict):
                        activity_type = row['activity_type']
                        count = row['count']
                        active_days = row['active_days']
                    else:
                        activity_type = row[0]
                        count = row[1]
                        active_days = row[2]
                    
                    activity_by_type[activity_type] = count
                    total_activities += count
                
                # 获取总活跃天数
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(DISTINCT activity_date) as active_days
                    FROM user_activity_log 
                    WHERE username = %s AND activity_date >= %s
                """, (username, start_date))
                
                result = cursor.fetchone()
                cursor.close()
                
                if isinstance(result, dict):
                    active_days = result['active_days']
                else:
                    active_days = result[0] if result else 0
                
                return {
                    "total_activities": total_activities,
                    "activity_by_type": activity_by_type,
                    "active_days": active_days
                }
                
        except Exception as e:
            logger.error(f"获取活动摘要失败 {username}: {e}")
            return {
                "total_activities": 0,
                "activity_by_type": {},
                "active_days": 0
            }
