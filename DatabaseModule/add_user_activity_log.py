"""
添加用户活动日志表，用于记录连续学习天数

运行方式：
python -m DatabaseModule.add_user_activity_log
"""

import logging
from DatabaseModule.database_factory import DatabaseFactory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def add_user_activity_log_table():
    """添加用户活动日志表"""
    store = DatabaseFactory.get_store()
    
    with store._lock, store.connection() as conn:
        cursor = conn.cursor()
        
        try:
            # 创建用户活动日志表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_activity_log (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    username VARCHAR(100) NOT NULL,
                    activity_date DATE NOT NULL,
                    activity_type VARCHAR(50) NOT NULL,
                    activity_details TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_username_date (username, activity_date),
                    INDEX idx_activity_date (activity_date),
                    UNIQUE KEY unique_user_date_type (username, activity_date, activity_type)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            conn.commit()
            logger.info("✅ 用户活动日志表创建成功")
            
            # 检查表是否存在
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = 'user_activity_log'
            """)
            result = cursor.fetchone()
            count = result['count'] if isinstance(result, dict) else result[0]
            if count > 0:
                logger.info("✅ 表验证成功：user_activity_log 已存在")
            else:
                logger.warning("⚠️ 表验证失败：user_activity_log 不存在")
                
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ 创建表失败: {e}")
            raise
        finally:
            cursor.close()


if __name__ == "__main__":
    logger.info("开始添加用户活动日志表...")
    add_user_activity_log_table()
    logger.info("完成！")
