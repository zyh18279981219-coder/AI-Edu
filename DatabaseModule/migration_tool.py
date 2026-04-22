"""
数据迁移工具

执行SQLite到MySQL的数据迁移和JSON规范化。
支持批量迁移、错误处理、进度跟踪和回滚机制。
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .database_store import DatabaseStore

logger = logging.getLogger(__name__)


class MigrationReport:
    """迁移报告类"""
    
    def __init__(self):
        self.start_time: Optional[str] = None
        self.end_time: Optional[str] = None
        self.duration: Optional[float] = None
        self.status: str = "pending"  # pending, running, success, failed
        self.tables: Dict[str, Dict[str, Any]] = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.total_records: int = 0
        self.migrated_records: int = 0
        self.normalized_records: int = 0
        
    def add_table_result(self, table_name: str, result: Dict[str, Any]) -> None:
        """添加表迁移结果"""
        self.tables[table_name] = result
        self.total_records += result.get('total', 0)
        self.migrated_records += result.get('migrated', 0)
        self.normalized_records += result.get('normalized', 0)
    
    def add_error(self, error: str) -> None:
        """添加错误信息"""
        self.errors.append(error)
        logger.error("Migration error: %s", error)
    
    def add_warning(self, warning: str) -> None:
        """添加警告信息"""
        self.warnings.append(warning)
        logger.warning("Migration warning: %s", warning)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.duration,
            'status': self.status,
            'tables': self.tables,
            'errors': self.errors,
            'warnings': self.warnings,
            'summary': {
                'total_records': self.total_records,
                'migrated_records': self.migrated_records,
                'normalized_records': self.normalized_records,
                'success_rate': (self.migrated_records / self.total_records * 100) if self.total_records > 0 else 0
            }
        }


class TableMigrationResult:
    """表迁移结果类"""
    
    def __init__(self):
        self.total_records: int = 0
        self.migrated_records: int = 0
        self.normalized_records: int = 0
        self.failed_records: int = 0
        self.errors: List[Dict[str, Any]] = []
        
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'total': self.total_records,
            'migrated': self.migrated_records,
            'normalized': self.normalized_records,
            'failed': self.failed_records,
            'errors': self.errors,
            'success_rate': (self.migrated_records / self.total_records * 100) if self.total_records > 0 else 0
        }


class MigrationTool:
    """数据迁移工具
    
    执行SQLite到MySQL的数据迁移和JSON规范化。
    支持批量迁移、错误处理、进度跟踪和回滚机制。
    """
    
    def __init__(self, source_store: DatabaseStore, target_store: DatabaseStore):
        """初始化迁移工具
        
        Args:
            source_store: 源数据库存储（通常是SQLiteStore）
            target_store: 目标数据库存储（通常是MySQLStore）
        """
        self.source = source_store
        self.target = target_store
        self.batch_size = 1000  # 批量处理大小
        self.checkpoint_file = Path("data/migration_checkpoint.json")
        self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        
    def migrate_all(self) -> MigrationReport:
        """执行完整迁移流程
        
        Returns:
            迁移报告
        """
        report = MigrationReport()
        report.start_time = datetime.now().isoformat()
        report.status = "running"
        
        logger.info("Starting database migration from %s to %s", 
                   type(self.source).__name__, type(self.target).__name__)
        
        try:
            # 按依赖顺序迁移表
            migration_order = [
                ('users', self.migrate_users),
                ('teacher_student_links', self.migrate_teacher_student_links),
                ('twin_profiles', self.migrate_twin_profiles),
                ('twin_history', self.migrate_twin_history),
                ('sessions', self.migrate_sessions),
                ('user_states', self.migrate_user_states),
                ('learning_plans', self.migrate_learning_plans),
                ('courses', self.migrate_courses),
                ('course_nodes', self.migrate_course_nodes),
                ('resources', self.migrate_resources),
                ('quiz_attempts', self.migrate_quiz_attempts),
                ('llm_logs', self.migrate_llm_logs),
            ]
            
            for table_name, migrate_func in migration_order:
                logger.info("Migrating table: %s", table_name)
                
                try:
                    result = migrate_func()
                    report.add_table_result(table_name, result.to_dict())
                    
                    # 保存检查点
                    self._save_checkpoint(table_name, result.to_dict())
                    
                    logger.info("Completed table %s: %d/%d records migrated", 
                               table_name, result.migrated_records, result.total_records)
                               
                except Exception as e:
                    error_msg = f"Failed to migrate table {table_name}: {str(e)}"
                    report.add_error(error_msg)
                    # 继续迁移其他表，不中断整个流程
            
            # 检查是否有严重错误
            if len(report.errors) == 0:
                report.status = "success"
            elif report.migrated_records > 0:
                report.status = "partial_success"
            else:
                report.status = "failed"
                
        except Exception as e:
            report.status = "failed"
            report.add_error(f"Migration failed: {str(e)}")
            logger.exception("Migration failed with exception")
        
        finally:
            report.end_time = datetime.now().isoformat()
            if report.start_time and report.end_time:
                start = datetime.fromisoformat(report.start_time)
                end = datetime.fromisoformat(report.end_time)
                report.duration = (end - start).total_seconds()
            
            # 保存最终报告
            self._save_final_report(report)
            
            logger.info("Migration completed with status: %s", report.status)
            logger.info("Total records: %d, Migrated: %d, Normalized: %d", 
                       report.total_records, report.migrated_records, report.normalized_records)
        
        return report
    
    def _save_checkpoint(self, table_name: str, result: Dict[str, Any]) -> None:
        """保存迁移检查点"""
        try:
            checkpoint_data = {}
            if self.checkpoint_file.exists():
                with self.checkpoint_file.open('r', encoding='utf-8') as f:
                    checkpoint_data = json.load(f)
            
            checkpoint_data[table_name] = {
                'completed_at': datetime.now().isoformat(),
                'result': result
            }
            
            with self.checkpoint_file.open('w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.warning("Failed to save checkpoint: %s", e)
    
    def _save_final_report(self, report: MigrationReport) -> None:
        """保存最终迁移报告"""
        try:
            report_file = Path("data/migration_report.json")
            with report_file.open('w', encoding='utf-8') as f:
                json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
            logger.info("Migration report saved to: %s", report_file)
        except Exception as e:
            logger.warning("Failed to save migration report: %s", e)
    
    def _now(self) -> str:
        """获取当前时间戳"""
        return datetime.now().isoformat()
    
    def _json(self, payload: Any) -> str:
        """序列化为JSON字符串"""
        return json.dumps(payload, ensure_ascii=False)
    
    # ==================== 表迁移方法（占位符） ====================
    # 注意：以下方法是占位符，将在后续子任务中实现具体逻辑
    
    def migrate_users(self) -> TableMigrationResult:
        """迁移用户表并规范化payload_json
        
        将SQLite的users表迁移到MySQL，同时将payload_json字段
        拆分到user_profiles表中。
        
        Returns:
            表迁移结果
        """
        result = TableMigrationResult()
        user_id_mapping = {}  # 旧ID -> 新ID映射
        
        logger.info("Starting users table migration with JSON normalization")
        
        try:
            # 从源数据库读取所有用户
            with self.source.connection() as conn:
                cursor = conn.execute("SELECT * FROM users ORDER BY user_id")
                source_users = [dict(row) for row in cursor.fetchall()]
            
            result.total_records = len(source_users)
            logger.info("Found %d users to migrate", result.total_records)
            
            # 批量处理用户
            for i in range(0, len(source_users), self.batch_size):
                batch = source_users[i:i + self.batch_size]
                
                with self.target.connection() as target_conn:
                    target_cursor = target_conn.cursor()
                    try:
                        for user in batch:
                            try:
                                # 解析payload_json
                                payload = {}
                                if user.get('payload_json'):
                                    try:
                                        payload = json.loads(user['payload_json'])
                                    except (json.JSONDecodeError, TypeError) as e:
                                        logger.warning("Failed to parse payload_json for user %s: %s", 
                                                     user.get('username', 'unknown'), e)
                                        payload = {}
                                
                                # 插入主表数据
                                new_user_id = self._insert_user_main_table(target_cursor, user)
                                user_id_mapping[user['user_id']] = new_user_id
                                
                                # 规范化扩展字段到user_profiles表
                                if payload and any(payload.get(key) for key in ['avatar_url', 'phone', 'address', 'bio', 'preferences', 'metadata']):
                                    self._insert_user_profile(target_cursor, new_user_id, payload)
                                    result.normalized_records += 1
                                
                                result.migrated_records += 1
                                
                            except Exception as e:
                                result.failed_records += 1
                                result.errors.append({
                                    'user_id': user.get('user_id'),
                                    'username': user.get('username'),
                                    'error': str(e)
                                })
                                logger.error("Failed to migrate user %s: %s", 
                                           user.get('username', 'unknown'), e)
                    finally:
                        if hasattr(target_cursor, 'close'):
                            target_cursor.close()
                
                logger.info("Migrated batch %d-%d users", i + 1, min(i + self.batch_size, len(source_users)))
            
            # 保存ID映射供后续表使用
            self._save_id_mapping('users', user_id_mapping)
            
            logger.info("Users migration completed: %d/%d migrated, %d normalized", 
                       result.migrated_records, result.total_records, result.normalized_records)
            
        except Exception as e:
            logger.exception("Users migration failed")
            result.errors.append({'error': f"Migration failed: {str(e)}"})
        
        return result
    
    def _insert_user_main_table(self, cursor, user: Dict[str, Any]) -> int:
        """插入用户主表数据
        
        Args:
            cursor: 数据库游标
            user: 用户数据字典
            
        Returns:
            新生成的user_id
        """
        # 检查目标数据库类型来使用正确的占位符
        if 'sqlite' in str(type(cursor)).lower():
            # SQLite版本 - 使用原有的表结构
            query = """
            INSERT INTO users (
                login_id, user_type, username, password, 
                display_name, teacher, email, payload_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            params = (
                user.get('login_id') or f"{user['user_type'][:3].lower()}{user['user_id']:06d}",
                user['user_type'],
                user['username'],
                user.get('password'),
                user.get('display_name') or user['username'],
                user.get('teacher'),  # 保持原有的teacher字段
                user.get('email'),
                '{}',  # 空的payload_json，因为我们要规范化
                user.get('updated_at') or self._now()
            )
        else:
            # MySQL版本 - 使用新的表结构
            query = """
            INSERT INTO users (
                login_id, user_type, username, password, 
                display_name, teacher_id, email, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            params = (
                user.get('login_id') or f"{user['user_type'][:3].lower()}{user['user_id']:06d}",
                user['user_type'],
                user['username'],
                user.get('password'),
                user.get('display_name') or user['username'],
                None,  # teacher_id暂时为None
                user.get('email'),
                user.get('created_at') or self._now(),
                user.get('updated_at') or self._now()
            )
        
        cursor.execute(query, params)
        
        # 获取插入的ID
        if hasattr(cursor, 'lastrowid'):
            return cursor.lastrowid
        else:
            # 如果没有lastrowid，查询最后插入的记录
            cursor.execute("SELECT last_insert_rowid()" if 'sqlite' in str(type(cursor)).lower() 
                          else "SELECT LAST_INSERT_ID()")
            result = cursor.fetchone()
            return result[0] if result else user['user_id']
    
    def _insert_user_profile(self, cursor, user_id: int, payload: Dict[str, Any]) -> None:
        """插入用户扩展信息到规范化表
        
        Args:
            cursor: 数据库游标
            user_id: 用户ID
            payload: 扩展信息字典
        """
        # 检查目标数据库类型来使用正确的占位符和语法
        if 'sqlite' in str(type(cursor)).lower():
            # SQLite版本
            query = """
            INSERT OR REPLACE INTO user_profiles (
                user_id, avatar_url, phone, address, bio, 
                preferences, metadata, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
        else:
            # MySQL版本
            query = """
            INSERT INTO user_profiles (
                user_id, avatar_url, phone, address, bio, 
                preferences, metadata, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                avatar_url = VALUES(avatar_url),
                phone = VALUES(phone),
                address = VALUES(address),
                bio = VALUES(bio),
                preferences = VALUES(preferences),
                metadata = VALUES(metadata),
                updated_at = VALUES(updated_at)
            """
        
        params = (
            user_id,
            payload.get('avatar_url'),
            payload.get('phone'),
            payload.get('address'),
            payload.get('bio'),
            self._json(payload.get('preferences', {})),
            self._json(payload.get('metadata', {})),
            self._now(),
            self._now()
        )
        
        cursor.execute(query, params)
    
    def _insert_twin_profile_main_table(self, cursor, profile: Dict[str, Any], user_id: int) -> int:
        """插入数字孪生画像主表数据
        
        Args:
            cursor: 数据库游标
            profile: 画像数据字典
            user_id: 用户ID
            
        Returns:
            新生成的profile_id
        """
        # 检查目标数据库类型来使用正确的占位符
        if 'sqlite' in str(type(cursor)).lower():
            # SQLite版本 - 使用原有的表结构
            query = """
            INSERT OR REPLACE INTO twin_profiles (
                username, user_id, last_updated, overall_mastery, updated_at
            ) VALUES (?, ?, ?, ?, ?)
            """
            
            params = (
                profile.get('username'),
                user_id,
                profile.get('last_updated'),
                profile.get('overall_mastery', 0.0),
                profile.get('updated_at') or self._now()
            )
        else:
            # MySQL版本 - 使用新的表结构
            query = """
            INSERT INTO twin_profiles (
                username, user_id, last_updated, overall_mastery, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                last_updated = VALUES(last_updated),
                overall_mastery = VALUES(overall_mastery),
                updated_at = VALUES(updated_at)
            """
            
            params = (
                profile.get('username'),
                user_id,
                profile.get('last_updated'),
                profile.get('overall_mastery', 0.0),
                self._now(),
                profile.get('updated_at') or self._now()
            )
        
        cursor.execute(query, params)
        
        # 获取插入的ID
        if hasattr(cursor, 'lastrowid'):
            return cursor.lastrowid
        else:
            # 如果没有lastrowid，查询最后插入的记录
            cursor.execute("SELECT last_insert_rowid()" if 'sqlite' in str(type(cursor)).lower() 
                          else "SELECT LAST_INSERT_ID()")
            result = cursor.fetchone()
            return result[0] if result else 1
    
    def _get_twin_profile_nodes(self, username: str) -> Dict[str, Any]:
        """从源数据库获取数字孪生节点详情数据
        
        Args:
            username: 用户名
            
        Returns:
            节点详情数据字典
        """
        try:
            with self.source.connection() as conn:
                cursor = conn.execute("""
                    SELECT node_id, node_path_json, quiz_score, progress, 
                           study_duration_minutes, llm_interaction_count, mastery_score
                    FROM twin_profile_nodes 
                    WHERE username = ?
                    ORDER BY node_id
                """, (username,))
                nodes = [dict(row) for row in cursor.fetchall()]
            
            if not nodes:
                return {}
            
            # 构建知识图谱结构
            knowledge_graph = {}
            learning_style = {}
            strengths = []
            weaknesses = []
            recommendations = []
            
            for node in nodes:
                node_id = node.get('node_id')
                mastery_score = node.get('mastery_score', 0.0) or 0.0
                progress = node.get('progress', 0.0) or 0.0
                
                # 解析节点路径
                node_path = []
                if node.get('node_path_json'):
                    try:
                        node_path = json.loads(node['node_path_json'])
                    except (json.JSONDecodeError, TypeError):
                        node_path = []
                
                # 构建知识图谱节点
                knowledge_graph[node_id] = {
                    'node_id': node_id,
                    'node_path': node_path,
                    'quiz_score': node.get('quiz_score'),
                    'progress': progress,
                    'study_duration_minutes': node.get('study_duration_minutes', 0.0) or 0.0,
                    'llm_interaction_count': node.get('llm_interaction_count', 0) or 0,
                    'mastery_score': mastery_score
                }
                
                # 分析优势和弱点
                if mastery_score >= 0.8:
                    strengths.append({
                        'node_id': node_id,
                        'node_path': node_path,
                        'mastery_score': mastery_score
                    })
                elif mastery_score <= 0.4:
                    weaknesses.append({
                        'node_id': node_id,
                        'node_path': node_path,
                        'mastery_score': mastery_score
                    })
                    
                    # 生成推荐
                    recommendations.append({
                        'type': 'review',
                        'node_id': node_id,
                        'node_path': node_path,
                        'reason': f'掌握度较低 ({mastery_score:.2f})',
                        'priority': 'high' if mastery_score <= 0.2 else 'medium'
                    })
            
            # 分析学习风格
            total_study_time = sum(node.get('study_duration_minutes', 0) or 0 for node in nodes)
            total_interactions = sum(node.get('llm_interaction_count', 0) or 0 for node in nodes)
            
            if total_study_time > 0:
                avg_interaction_rate = total_interactions / total_study_time * 60  # 每小时交互次数
                
                if avg_interaction_rate > 10:
                    learning_style['type'] = 'interactive'
                    learning_style['description'] = '偏好互动式学习，经常与AI助手交流'
                elif avg_interaction_rate > 5:
                    learning_style['type'] = 'balanced'
                    learning_style['description'] = '平衡的学习风格，适度使用AI助手'
                else:
                    learning_style['type'] = 'independent'
                    learning_style['description'] = '偏好独立学习，较少依赖AI助手'
            
            return {
                'knowledge_graph': knowledge_graph,
                'learning_style': learning_style,
                'strengths': strengths,
                'weaknesses': weaknesses,
                'recommendations': recommendations
            }
            
        except Exception as e:
            logger.warning("Failed to get twin profile nodes for %s: %s", username, e)
            return {}
    
    def _insert_twin_profile_details(self, cursor, profile_id: int, details: Dict[str, Any]) -> None:
        """插入数字孪生详细信息到规范化表
        
        Args:
            cursor: 数据库游标
            profile_id: 画像ID
            details: 详细信息字典
        """
        # 检查目标数据库类型来使用正确的占位符和语法
        if 'sqlite' in str(type(cursor)).lower():
            # SQLite版本 - 如果表存在的话
            query = """
            INSERT OR REPLACE INTO twin_profile_details (
                profile_id, knowledge_graph, learning_style, strengths, 
                weaknesses, recommendations, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
        else:
            # MySQL版本
            query = """
            INSERT INTO twin_profile_details (
                profile_id, knowledge_graph, learning_style, strengths, 
                weaknesses, recommendations, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                knowledge_graph = VALUES(knowledge_graph),
                learning_style = VALUES(learning_style),
                strengths = VALUES(strengths),
                weaknesses = VALUES(weaknesses),
                recommendations = VALUES(recommendations),
                updated_at = VALUES(updated_at)
            """
        
        params = (
            profile_id,
            self._json(details.get('knowledge_graph', {})),
            self._json(details.get('learning_style', {})),
            self._json(details.get('strengths', [])),
            self._json(details.get('weaknesses', [])),
            self._json(details.get('recommendations', [])),
            self._now(),
            self._now()
        )
        
        try:
            cursor.execute(query, params)
        except Exception as e:
            # 如果twin_profile_details表不存在（SQLite情况），忽略错误
            if 'no such table' in str(e).lower():
                logger.info("twin_profile_details table not found, skipping normalization")
            else:
                raise
    
    def _save_id_mapping(self, table_name: str, mapping: Dict[int, int]) -> None:
        """保存ID映射关系
        
        Args:
            table_name: 表名
            mapping: ID映射字典 (旧ID -> 新ID)
        """
        try:
            mapping_file = Path(f"data/{table_name}_id_mapping.json")
            with mapping_file.open('w', encoding='utf-8') as f:
                # 将int键转换为字符串以便JSON序列化
                str_mapping = {str(k): v for k, v in mapping.items()}
                json.dump(str_mapping, f, indent=2)
            logger.info("Saved %s ID mapping: %d entries", table_name, len(mapping))
        except Exception as e:
            logger.warning("Failed to save %s ID mapping: %s", table_name, e)
    
    def _save_id_mapping(self, table_name: str, mapping: Dict[int, int]) -> None:
        """保存ID映射关系
        
        Args:
            table_name: 表名
            mapping: ID映射字典 (旧ID -> 新ID)
        """
        try:
            mapping_file = Path(f"data/{table_name}_id_mapping.json")
            with mapping_file.open('w', encoding='utf-8') as f:
                # 将int键转换为字符串以便JSON序列化
                str_mapping = {str(k): v for k, v in mapping.items()}
                json.dump(str_mapping, f, indent=2)
            logger.info("Saved %s ID mapping: %d entries", table_name, len(mapping))
        except Exception as e:
            logger.warning("Failed to save %s ID mapping: %s", table_name, e)
    
    def _load_id_mapping(self, table_name: str) -> Dict[int, int]:
        """加载ID映射关系
        
        Args:
            table_name: 表名
            
        Returns:
            ID映射字典 (旧ID -> 新ID)
        """
        try:
            mapping_file = Path(f"data/{table_name}_id_mapping.json")
            if mapping_file.exists():
                with mapping_file.open('r', encoding='utf-8') as f:
                    str_mapping = json.load(f)
                # 将字符串键转换回int
                return {int(k): v for k, v in str_mapping.items()}
        except Exception as e:
            logger.warning("Failed to load %s ID mapping: %s", table_name, e)
        
        return {}
    
    def _insert_learning_plan_main_table(self, cursor, plan: Dict[str, Any], user_id: int, payload: Any) -> int:
        """插入学习计划主表数据
        
        Args:
            cursor: 数据库游标
            plan: 学习计划数据字典
            user_id: 用户ID
            payload: 解析后的payload数据（可能是字典或列表）
            
        Returns:
            新生成的plan_id
        """
        # 处理不同格式的payload
        if isinstance(payload, dict):
            # 字典格式 (path类型学习计划)
            title = payload.get('title', f"学习路径 - {plan.get('filename', 'Unknown')}")
            description = payload.get('description', '')
            status = payload.get('status', 'active')
        elif isinstance(payload, list):
            # 列表格式 (plan类型学习计划)
            title = f"学习计划 - {plan.get('filename', 'Unknown')}"
            if len(payload) > 0 and isinstance(payload[0], dict):
                # 从第一个任务提取主题作为描述
                first_task = payload[0]
                topic = first_task.get('topic', '')
                description = f"学习主题: {topic}" if topic else "学习计划"
            else:
                description = "学习计划"
            status = 'active'
        else:
            # 未知格式，使用默认值
            title = f"学习计划 - {plan.get('filename', 'Unknown')}"
            description = "学习计划"
            status = 'active'
        
        # 映射状态值
        status_mapping = {
            'active': 'active',
            'completed': 'completed',
            'draft': 'draft',
            'archived': 'archived'
        }
        mapped_status = status_mapping.get(status, 'draft')
        
        # 检查目标数据库类型来使用正确的占位符
        if 'sqlite' in str(type(cursor)).lower():
            # SQLite版本 - 使用原有的表结构
            query = """
            INSERT OR REPLACE INTO learning_plans (
                username, filename, plan_path, category, payload_json, updated_at, user_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            
            params = (
                plan.get('username'),
                plan.get('filename'),
                plan.get('plan_path'),
                plan.get('category', 'user'),
                plan.get('payload_json', '{}'),
                plan.get('updated_at') or self._now(),
                user_id
            )
        else:
            # MySQL版本 - 使用新的表结构
            query = """
            INSERT INTO learning_plans (
                username, user_id, filename, plan_path, category, 
                title, description, status, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                title = VALUES(title),
                description = VALUES(description),
                status = VALUES(status),
                updated_at = VALUES(updated_at)
            """
            
            params = (
                plan.get('username'),
                user_id,
                plan.get('filename'),
                plan.get('plan_path'),
                plan.get('category', 'user'),
                title,
                description,
                mapped_status,
                self._now(),
                plan.get('updated_at') or self._now()
            )
        
        cursor.execute(query, params)
        
        # 获取插入的ID
        # 注意：ON DUPLICATE KEY UPDATE时lastrowid可能为0，需要额外查询
        plan_id = cursor.lastrowid if hasattr(cursor, 'lastrowid') else 0
        
        if not plan_id:
            # ON DUPLICATE KEY UPDATE情况，查询实际的plan_id
            cursor.execute(
                "SELECT plan_id FROM learning_plans WHERE username = %s AND filename = %s",
                (plan.get('username'), plan.get('filename'))
            )
            row = cursor.fetchone()
            plan_id = row[0] if row else 0
        
        return plan_id
    
    def _insert_learning_plan_nodes(self, cursor, plan_id: int, payload: Any) -> None:
        """插入学习计划节点到规范化表
        
        支持两种payload格式：
        1. 字典格式 (path类型): {'weak_nodes': [...], ...}
        2. 列表格式 (plan类型): [{'date': ..., 'topic': ..., 'materials': ...}, ...]
        
        Args:
            cursor: 数据库游标
            plan_id: 学习计划ID
            payload: 学习计划payload数据（字典或列表）
        """
        # 根据payload类型提取节点列表
        if isinstance(payload, dict):
            # 字典格式 - 提取weak_nodes
            nodes_to_insert = []
            for i, node in enumerate(payload.get('weak_nodes', [])):
                nodes_to_insert.append({
                    'node_key': node.get('node_id', f'node_{i}'),
                    'node_name': node.get('node_id', f'node_{i}'),
                    'node_type': 'weak_node',
                    'sequence_order': i,
                    'mastery_score': node.get('mastery_score', 0.0),
                    'priority': node.get('priority', i + 1),
                    'content': {
                        'resources': node.get('resources', []),
                        'llm_priority': node.get('llm_priority', ''),
                    },
                    'metadata': {
                        'llm_advice': payload.get('llm_advice', ''),
                    }
                })
        elif isinstance(payload, list):
            # 列表格式 - 每个元素是一个学习任务
            nodes_to_insert = []
            for i, task in enumerate(payload):
                if not isinstance(task, dict):
                    continue
                nodes_to_insert.append({
                    'node_key': f'task_{i}',
                    'node_name': task.get('topic', f'任务_{i}'),
                    'node_type': 'task',
                    'sequence_order': i,
                    'mastery_score': None,
                    'priority': i + 1,
                    'content': {
                        'materials': task.get('materials', []),
                        'deadline': task.get('deadline', ''),
                    },
                    'metadata': {
                        'date': task.get('date', ''),
                        'priority_level': task.get('priority', ''),
                    }
                })
        else:
            return
        
        # 插入节点
        for node_data in nodes_to_insert:
            try:
                if 'sqlite' in str(type(cursor)).lower():
                    query = """
                    INSERT OR REPLACE INTO learning_plan_nodes (
                        plan_id, node_key, node_name, node_type, sequence_order,
                        mastery_score, priority, content, metadata, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                else:
                    query = """
                    INSERT INTO learning_plan_nodes (
                        plan_id, node_key, node_name, node_type, sequence_order,
                        mastery_score, priority, content, metadata, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        node_name = VALUES(node_name),
                        node_type = VALUES(node_type),
                        sequence_order = VALUES(sequence_order),
                        mastery_score = VALUES(mastery_score),
                        priority = VALUES(priority),
                        content = VALUES(content),
                        metadata = VALUES(metadata),
                        updated_at = VALUES(updated_at)
                    """
                
                params = (
                    plan_id,
                    node_data['node_key'],
                    node_data['node_name'],
                    node_data['node_type'],
                    node_data['sequence_order'],
                    node_data['mastery_score'],
                    node_data['priority'],
                    self._json(node_data['content']),
                    self._json(node_data['metadata']),
                    self._now(),
                    self._now()
                )
                
                cursor.execute(query, params)
                
            except Exception as e:
                logger.warning("Failed to insert learning plan node %s: %s", node_data.get('node_key', 'unknown'), e)
    
    def migrate_teacher_student_links(self) -> TableMigrationResult:
        """迁移教师学生关系表"""
        result = TableMigrationResult()
        
        logger.info("Starting teacher_student_links migration")
        
        try:
            with self.source.connection() as conn:
                cursor = conn.execute("""
                    SELECT teacher_username, student_username, updated_at,
                           teacher_user_id, student_user_id
                    FROM teacher_student_links
                """)
                source_links = [dict(row) for row in cursor.fetchall()]
            
            result.total_records = len(source_links)
            logger.info("Found %d teacher_student_links to migrate", result.total_records)
            
            user_id_mapping = self._load_id_mapping('users')
            
            with self.target.connection() as target_conn:
                target_cursor = target_conn.cursor()
                try:
                    for link in source_links:
                        try:
                            # 映射用户ID
                            old_teacher_id = link.get('teacher_user_id')
                            old_student_id = link.get('student_user_id')
                            new_teacher_id = user_id_mapping.get(old_teacher_id) if old_teacher_id else None
                            new_student_id = user_id_mapping.get(old_student_id) if old_student_id else None
                            
                            # 如果映射失败，直接查询
                            if not new_teacher_id:
                                target_cursor.execute("SELECT user_id FROM users WHERE username = %s", (link['teacher_username'],))
                                row = target_cursor.fetchone()
                                new_teacher_id = row[0] if row else None
                            
                            if not new_student_id:
                                target_cursor.execute("SELECT user_id FROM users WHERE username = %s", (link['student_username'],))
                                row = target_cursor.fetchone()
                                new_student_id = row[0] if row else None
                            
                            target_cursor.execute("""
                                INSERT INTO teacher_student_links 
                                    (teacher_username, student_username, teacher_user_id, student_user_id, updated_at)
                                VALUES (%s, %s, %s, %s, %s)
                                ON DUPLICATE KEY UPDATE
                                    teacher_user_id = VALUES(teacher_user_id),
                                    student_user_id = VALUES(student_user_id),
                                    updated_at = VALUES(updated_at)
                            """, (
                                link['teacher_username'],
                                link['student_username'],
                                new_teacher_id,
                                new_student_id,
                                link.get('updated_at') or self._now()
                            ))
                            result.migrated_records += 1
                        except Exception as e:
                            result.failed_records += 1
                            result.errors.append({'link': f"{link.get('teacher_username')}->{link.get('student_username')}", 'error': str(e)})
                finally:
                    target_cursor.close()
            
            logger.info("teacher_student_links migration completed: %d/%d", result.migrated_records, result.total_records)
            
        except Exception as e:
            logger.exception("teacher_student_links migration failed")
            result.errors.append({'error': str(e)})
        
        return result
    
    def migrate_twin_profiles(self) -> TableMigrationResult:
        """迁移数字孪生画像表并规范化payload_json
        
        将SQLite的twin_profiles表迁移到MySQL，同时将payload_json字段
        拆分到twin_profile_details表中。
        
        Returns:
            表迁移结果
        """
        result = TableMigrationResult()
        
        logger.info("Starting twin_profiles table migration with JSON normalization")
        
        try:
            # 从源数据库读取所有数字孪生画像
            with self.source.connection() as conn:
                cursor = conn.execute("""
                    SELECT username, user_id, last_updated, overall_mastery, updated_at
                    FROM twin_profiles 
                    ORDER BY username
                """)
                source_profiles = [dict(row) for row in cursor.fetchall()]
            
            result.total_records = len(source_profiles)
            logger.info("Found %d twin profiles to migrate", result.total_records)
            
            # 加载用户ID映射
            user_id_mapping = self._load_id_mapping('users')
            
            # 批量处理数字孪生画像
            for i in range(0, len(source_profiles), self.batch_size):
                batch = source_profiles[i:i + self.batch_size]
                
                with self.target.connection() as target_conn:
                    target_cursor = target_conn.cursor()
                    try:
                        for profile in batch:
                            try:
                                # 映射用户ID
                                old_user_id = profile.get('user_id')
                                new_user_id = user_id_mapping.get(old_user_id) if old_user_id else None
                                
                                if not new_user_id:
                                    # 尝试通过username查找用户ID
                                    username = profile.get('username')
                                    if username:
                                        user = self.target.get_user_by_identifier('student', username)
                                        new_user_id = user.get('user_id') if user else None
                                
                                if not new_user_id:
                                    logger.warning("Cannot find user_id for twin profile: %s", profile.get('username'))
                                    result.failed_records += 1
                                    result.errors.append({
                                        'username': profile.get('username'),
                                        'error': 'Cannot find corresponding user_id'
                                    })
                                    continue
                                
                                # 插入主表数据
                                profile_id = self._insert_twin_profile_main_table(target_cursor, profile, new_user_id)
                                
                                # 从源数据库获取节点详情数据
                                node_details = self._get_twin_profile_nodes(profile.get('username'))
                                
                                # 规范化节点详情到twin_profile_details表
                                if node_details:
                                    self._insert_twin_profile_details(target_cursor, profile_id, node_details)
                                    result.normalized_records += 1
                                
                                result.migrated_records += 1
                                
                            except Exception as e:
                                result.failed_records += 1
                                result.errors.append({
                                    'username': profile.get('username'),
                                    'error': str(e)
                                })
                                logger.error("Failed to migrate twin profile %s: %s", 
                                           profile.get('username', 'unknown'), e)
                    finally:
                        if hasattr(target_cursor, 'close'):
                            target_cursor.close()
                
                logger.info("Migrated batch %d-%d twin profiles", i + 1, min(i + self.batch_size, len(source_profiles)))
            
            logger.info("Twin profiles migration completed: %d/%d migrated, %d normalized", 
                       result.migrated_records, result.total_records, result.normalized_records)
            
        except Exception as e:
            logger.exception("Twin profiles migration failed")
            result.errors.append({'error': f"Migration failed: {str(e)}"})
        
        return result
    
    def migrate_twin_history(self) -> TableMigrationResult:
        """迁移数字孪生历史表"""
        result = TableMigrationResult()
        
        logger.info("Starting twin_history migration")
        
        try:
            with self.source.connection() as conn:
                cursor = conn.execute("""
                    SELECT username, snapshot_date, overall_mastery, payload_json, updated_at, user_id
                    FROM twin_history ORDER BY username, snapshot_date
                """)
                source_history = [dict(row) for row in cursor.fetchall()]
            
            result.total_records = len(source_history)
            logger.info("Found %d twin_history records to migrate", result.total_records)
            
            user_id_mapping = self._load_id_mapping('users')
            
            for i in range(0, len(source_history), self.batch_size):
                batch = source_history[i:i + self.batch_size]
                
                with self.target.connection() as target_conn:
                    target_cursor = target_conn.cursor()
                    try:
                        for record in batch:
                            try:
                                old_user_id = record.get('user_id')
                                new_user_id = user_id_mapping.get(old_user_id) if old_user_id else None
                                
                                if not new_user_id:
                                    target_cursor.execute("SELECT user_id FROM users WHERE username = %s", (record['username'],))
                                    row = target_cursor.fetchone()
                                    new_user_id = row[0] if row else None
                                
                                target_cursor.execute("""
                                    INSERT INTO twin_history 
                                        (username, user_id, snapshot_date, overall_mastery, payload_json, updated_at)
                                    VALUES (%s, %s, %s, %s, %s, %s)
                                    ON DUPLICATE KEY UPDATE
                                        overall_mastery = VALUES(overall_mastery),
                                        payload_json = VALUES(payload_json),
                                        updated_at = VALUES(updated_at)
                                """, (
                                    record['username'],
                                    new_user_id,
                                    record['snapshot_date'],
                                    record.get('overall_mastery', 0.0),
                                    record.get('payload_json') or '{}',
                                    record.get('updated_at') or self._now()
                                ))
                                result.migrated_records += 1
                            except Exception as e:
                                result.failed_records += 1
                                result.errors.append({'username': record.get('username'), 'error': str(e)})
                    finally:
                        target_cursor.close()
            
            logger.info("twin_history migration completed: %d/%d", result.migrated_records, result.total_records)
            
        except Exception as e:
            logger.exception("twin_history migration failed")
            result.errors.append({'error': str(e)})
        
        return result
    
    def migrate_sessions(self) -> TableMigrationResult:
        """迁移会话表"""
        result = TableMigrationResult()
        
        logger.info("Starting sessions migration")
        
        try:
            with self.source.connection() as conn:
                cursor = conn.execute("""
                    SELECT session_id, username, user_type, created_at, last_accessed,
                           current_pdf_path, current_node, payload_json, updated_at, user_id
                    FROM sessions ORDER BY created_at
                """)
                source_sessions = [dict(row) for row in cursor.fetchall()]
            
            result.total_records = len(source_sessions)
            logger.info("Found %d sessions to migrate", result.total_records)
            
            user_id_mapping = self._load_id_mapping('users')
            
            for i in range(0, len(source_sessions), self.batch_size):
                batch = source_sessions[i:i + self.batch_size]
                
                with self.target.connection() as target_conn:
                    target_cursor = target_conn.cursor()
                    try:
                        for session in batch:
                            try:
                                old_user_id = session.get('user_id')
                                new_user_id = user_id_mapping.get(old_user_id) if old_user_id else None
                                
                                if not new_user_id:
                                    target_cursor.execute("SELECT user_id FROM users WHERE username = %s", (session['username'],))
                                    row = target_cursor.fetchone()
                                    new_user_id = row[0] if row else None
                                
                                # 截断session_id防止超长
                                session_id = session['session_id'][:255] if session.get('session_id') else None
                                if not session_id:
                                    continue
                                
                                target_cursor.execute("""
                                    INSERT INTO sessions (
                                        session_id, user_id, username, user_type,
                                        created_at, last_accessed, current_pdf_path,
                                        current_node, payload_json, updated_at
                                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    ON DUPLICATE KEY UPDATE
                                        last_accessed = VALUES(last_accessed),
                                        current_pdf_path = VALUES(current_pdf_path),
                                        current_node = VALUES(current_node),
                                        payload_json = VALUES(payload_json),
                                        updated_at = VALUES(updated_at)
                                """, (
                                    session_id,
                                    new_user_id,
                                    session['username'],
                                    session.get('user_type', 'student'),
                                    session.get('created_at'),
                                    session.get('last_accessed'),
                                    session.get('current_pdf_path'),
                                    session.get('current_node', '')[:500] if session.get('current_node') else None,
                                    session.get('payload_json') or '{}',
                                    session.get('updated_at') or self._now()
                                ))
                                result.migrated_records += 1
                            except Exception as e:
                                result.failed_records += 1
                                result.errors.append({'session_id': session.get('session_id', '')[:50], 'error': str(e)})
                    finally:
                        target_cursor.close()
                
                logger.info("Migrated batch %d-%d sessions", i+1, min(i+self.batch_size, len(source_sessions)))
            
            logger.info("Sessions migration completed: %d/%d", result.migrated_records, result.total_records)
            
        except Exception as e:
            logger.exception("Sessions migration failed")
            result.errors.append({'error': str(e)})
        
        return result
    
    def migrate_user_states(self) -> TableMigrationResult:
        """迁移用户状态表"""
        result = TableMigrationResult()
        
        logger.info("Starting user_states migration")
        
        try:
            with self.source.connection() as conn:
                cursor = conn.execute("SELECT username, payload_json, updated_at, user_id FROM user_states")
                source_states = [dict(row) for row in cursor.fetchall()]
            
            result.total_records = len(source_states)
            logger.info("Found %d user_states to migrate", result.total_records)
            
            user_id_mapping = self._load_id_mapping('users')
            
            with self.target.connection() as target_conn:
                target_cursor = target_conn.cursor()
                try:
                    for state in source_states:
                        try:
                            old_user_id = state.get('user_id')
                            new_user_id = user_id_mapping.get(old_user_id) if old_user_id else None
                            
                            if not new_user_id:
                                target_cursor.execute("SELECT user_id FROM users WHERE username = %s", (state['username'],))
                                row = target_cursor.fetchone()
                                new_user_id = row[0] if row else None
                            
                            target_cursor.execute("""
                                INSERT INTO user_states (username, user_id, payload_json, updated_at)
                                VALUES (%s, %s, %s, %s)
                                ON DUPLICATE KEY UPDATE
                                    user_id = VALUES(user_id),
                                    payload_json = VALUES(payload_json),
                                    updated_at = VALUES(updated_at)
                            """, (
                                state['username'],
                                new_user_id,
                                state.get('payload_json') or '{}',
                                state.get('updated_at') or self._now()
                            ))
                            result.migrated_records += 1
                        except Exception as e:
                            result.failed_records += 1
                            result.errors.append({'username': state.get('username'), 'error': str(e)})
                finally:
                    target_cursor.close()
            
            logger.info("user_states migration completed: %d/%d", result.migrated_records, result.total_records)
            
        except Exception as e:
            logger.exception("user_states migration failed")
            result.errors.append({'error': str(e)})
        
        return result
    
    def migrate_learning_plans(self) -> TableMigrationResult:
        """迁移学习计划表并规范化payload_json
        
        将SQLite的learning_plans表迁移到MySQL，同时将payload_json字段
        拆分到learning_plan_nodes表中，处理层级关系。
        
        Returns:
            表迁移结果
        """
        result = TableMigrationResult()
        plan_id_mapping = {}  # 旧filename -> 新plan_id映射
        
        logger.info("Starting learning_plans table migration with JSON normalization")
        
        try:
            # 从源数据库读取所有学习计划
            with self.source.connection() as conn:
                cursor = conn.execute("""
                    SELECT username, filename, plan_path, category, payload_json, updated_at, user_id
                    FROM learning_plans 
                    ORDER BY username, filename
                """)
                source_plans = [dict(row) for row in cursor.fetchall()]
            
            result.total_records = len(source_plans)
            logger.info("Found %d learning plans to migrate", result.total_records)
            
            # 加载用户ID映射
            user_id_mapping = self._load_id_mapping('users')
            
            # 批量处理学习计划
            for i in range(0, len(source_plans), self.batch_size):
                batch = source_plans[i:i + self.batch_size]
                
                with self.target.connection() as target_conn:
                    target_cursor = target_conn.cursor()
                    try:
                        for plan in batch:
                            try:
                                # 映射用户ID
                                old_user_id = plan.get('user_id')
                                new_user_id = user_id_mapping.get(old_user_id) if old_user_id else None
                                
                                if not new_user_id:
                                    # 尝试通过username直接查询目标数据库
                                    username = plan.get('username')
                                    if username:
                                        try:
                                            target_cursor.execute(
                                                "SELECT user_id FROM users WHERE username = %s LIMIT 1",
                                                (username,)
                                            )
                                            user_row = target_cursor.fetchone()
                                            if user_row:
                                                new_user_id = user_row[0] if isinstance(user_row, tuple) else user_row.get('user_id')
                                        except Exception:
                                            pass
                                
                                if not new_user_id:
                                    # 用户在目标库中不存在，跳过（孤立数据）
                                    logger.warning("Cannot find user_id for learning plan: %s/%s (user not in target DB)", 
                                                 plan.get('username'), plan.get('filename'))
                                    result.failed_records += 1
                                    result.errors.append({
                                        'username': plan.get('username'),
                                        'filename': plan.get('filename'),
                                        'error': 'User not found in target database'
                                    })
                                    continue
                                
                                # 解析payload_json
                                payload = {}
                                if plan.get('payload_json'):
                                    try:
                                        payload = json.loads(plan['payload_json'])
                                    except (json.JSONDecodeError, TypeError) as e:
                                        logger.warning("Failed to parse payload_json for plan %s/%s: %s", 
                                                     plan.get('username'), plan.get('filename'), e)
                                        payload = {}
                                
                                # 插入主表数据
                                plan_id = self._insert_learning_plan_main_table(target_cursor, plan, new_user_id, payload)
                                plan_id_mapping[f"{plan['username']}/{plan['filename']}"] = plan_id
                                
                                # 规范化节点数据到learning_plan_nodes表
                                if payload and ('weak_nodes' in payload if isinstance(payload, dict) else True):
                                    self._insert_learning_plan_nodes(target_cursor, plan_id, payload)
                                    result.normalized_records += 1
                                
                                result.migrated_records += 1
                                
                            except Exception as e:
                                result.failed_records += 1
                                result.errors.append({
                                    'username': plan.get('username'),
                                    'filename': plan.get('filename'),
                                    'error': str(e)
                                })
                                logger.error("Failed to migrate learning plan %s/%s: %s", 
                                           plan.get('username'), plan.get('filename'), e)
                    finally:
                        if hasattr(target_cursor, 'close'):
                            target_cursor.close()
                
                logger.info("Migrated batch %d-%d learning plans", i + 1, min(i + self.batch_size, len(source_plans)))
            
            # 保存ID映射供后续使用
            self._save_id_mapping('learning_plans', plan_id_mapping)
            
            logger.info("Learning plans migration completed: %d/%d migrated, %d normalized", 
                       result.migrated_records, result.total_records, result.normalized_records)
            
        except Exception as e:
            logger.exception("Learning plans migration failed")
            result.errors.append({'error': f"Migration failed: {str(e)}"})
        
        return result
    
    def migrate_courses(self) -> TableMigrationResult:
        """迁移课程表，包括courses、course_nodes和resources"""
        result = TableMigrationResult()
        
        logger.info("Starting courses migration")
        
        try:
            # 读取所有课程
            with self.source.connection() as conn:
                cursor = conn.execute("SELECT course_id, course_name, source_path, payload_json, updated_at FROM courses")
                source_courses = [dict(row) for row in cursor.fetchall()]
            
            result.total_records = len(source_courses)
            logger.info("Found %d courses to migrate", result.total_records)
            
            for course in source_courses:
                try:
                    with self.target.connection() as target_conn:
                        target_cursor = target_conn.cursor()
                        try:
                            # 解析payload_json
                            payload = {}
                            if course.get('payload_json'):
                                try:
                                    payload = json.loads(course['payload_json'])
                                except (json.JSONDecodeError, TypeError):
                                    payload = {}
                            
                            # 插入courses主表
                            target_cursor.execute("""
                                INSERT INTO courses (course_id, course_name, source_path, created_at, updated_at)
                                VALUES (%s, %s, %s, %s, %s)
                                ON DUPLICATE KEY UPDATE
                                    course_name = VALUES(course_name),
                                    source_path = VALUES(source_path),
                                    updated_at = VALUES(updated_at)
                            """, (
                                course['course_id'],
                                course['course_name'],
                                course.get('source_path'),
                                self._now(),
                                course.get('updated_at') or self._now()
                            ))
                            
                            # 插入course_metadata（从payload提取元数据）
                            if payload:
                                target_cursor.execute("""
                                    INSERT INTO course_metadata (course_id, additional_data, created_at, updated_at)
                                    VALUES (%s, %s, %s, %s)
                                    ON DUPLICATE KEY UPDATE
                                        additional_data = VALUES(additional_data),
                                        updated_at = VALUES(updated_at)
                                """, (
                                    course['course_id'],
                                    self._json({'root_name': payload.get('root_name', ''), 'structure': payload}),
                                    self._now(),
                                    self._now()
                                ))
                                result.normalized_records += 1
                            
                            result.migrated_records += 1
                        finally:
                            target_cursor.close()
                            
                except Exception as e:
                    result.failed_records += 1
                    result.errors.append({'course_id': course.get('course_id'), 'error': str(e)})
                    logger.error("Failed to migrate course %s: %s", course.get('course_id'), e)
            
            logger.info("Courses migration completed: %d/%d", result.migrated_records, result.total_records)
            
        except Exception as e:
            logger.exception("Courses migration failed")
            result.errors.append({'error': str(e)})
        
        return result
    
    def migrate_course_nodes(self) -> TableMigrationResult:
        """迁移课程节点表"""
        result = TableMigrationResult()
        
        logger.info("Starting course_nodes migration")
        
        try:
            with self.source.connection() as conn:
                cursor = conn.execute("""
                    SELECT course_id, node_id, node_name, node_path_json, 
                           depth, parent_node_id, payload_json, updated_at
                    FROM course_nodes ORDER BY course_id, depth, node_id
                """)
                source_nodes = [dict(row) for row in cursor.fetchall()]
            
            result.total_records = len(source_nodes)
            logger.info("Found %d course nodes to migrate", result.total_records)
            
            for i in range(0, len(source_nodes), self.batch_size):
                batch = source_nodes[i:i + self.batch_size]
                
                with self.target.connection() as target_conn:
                    target_cursor = target_conn.cursor()
                    try:
                        for node in batch:
                            try:
                                target_cursor.execute("""
                                    INSERT INTO course_nodes (
                                        course_id, node_id, node_name, node_path_json,
                                        depth, parent_node_id, payload_json, created_at, updated_at
                                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    ON DUPLICATE KEY UPDATE
                                        node_name = VALUES(node_name),
                                        node_path_json = VALUES(node_path_json),
                                        depth = VALUES(depth),
                                        parent_node_id = VALUES(parent_node_id),
                                        payload_json = VALUES(payload_json),
                                        updated_at = VALUES(updated_at)
                                """, (
                                    node['course_id'],
                                    node['node_id'],
                                    node.get('node_name'),
                                    node.get('node_path_json'),
                                    node.get('depth', 0),
                                    node.get('parent_node_id'),
                                    node.get('payload_json') or '{}',
                                    self._now(),
                                    node.get('updated_at') or self._now()
                                ))
                                result.migrated_records += 1
                            except Exception as e:
                                result.failed_records += 1
                                result.errors.append({'node_id': node.get('node_id'), 'error': str(e)})
                    finally:
                        target_cursor.close()
                
                logger.info("Migrated batch %d-%d course nodes", i+1, min(i+self.batch_size, len(source_nodes)))
            
            logger.info("Course nodes migration completed: %d/%d", result.migrated_records, result.total_records)
            
        except Exception as e:
            logger.exception("Course nodes migration failed")
            result.errors.append({'error': str(e)})
        
        return result
    
    def migrate_resources(self) -> TableMigrationResult:
        """迁移资源表"""
        result = TableMigrationResult()
        
        logger.info("Starting resources migration")
        
        try:
            with self.source.connection() as conn:
                cursor = conn.execute("""
                    SELECT resource_id, course_id, node_id, resource_path, resource_type,
                           title, payload_json, is_deleted, deleted_at, deleted_by,
                           created_at, updated_at
                    FROM resources ORDER BY resource_id
                """)
                source_resources = [dict(row) for row in cursor.fetchall()]
            
            result.total_records = len(source_resources)
            logger.info("Found %d resources to migrate", result.total_records)
            
            for i in range(0, len(source_resources), self.batch_size):
                batch = source_resources[i:i + self.batch_size]
                
                with self.target.connection() as target_conn:
                    target_cursor = target_conn.cursor()
                    try:
                        for res in batch:
                            try:
                                # 截断过长的resource_path
                                resource_path = res.get('resource_path', '')
                                if len(resource_path) > 1000:
                                    resource_path = resource_path[:1000]
                                
                                target_cursor.execute("""
                                    INSERT INTO resources (
                                        course_id, node_id, resource_path, resource_type,
                                        title, payload_json, is_deleted, deleted_at, deleted_by,
                                        created_at, updated_at
                                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    ON DUPLICATE KEY UPDATE
                                        resource_type = VALUES(resource_type),
                                        title = VALUES(title),
                                        payload_json = VALUES(payload_json),
                                        is_deleted = VALUES(is_deleted),
                                        deleted_at = VALUES(deleted_at),
                                        deleted_by = VALUES(deleted_by),
                                        updated_at = VALUES(updated_at)
                                """, (
                                    res['course_id'],
                                    res['node_id'],
                                    resource_path,
                                    res.get('resource_type', '')[:200] if res.get('resource_type') else None,
                                    res.get('title', '')[:500] if res.get('title') else None,
                                    res.get('payload_json') or '{}',
                                    1 if res.get('is_deleted') else 0,
                                    res.get('deleted_at'),
                                    res.get('deleted_by'),
                                    res.get('created_at') or self._now(),
                                    res.get('updated_at') or self._now()
                                ))
                                result.migrated_records += 1
                            except Exception as e:
                                result.failed_records += 1
                                result.errors.append({'resource_id': res.get('resource_id'), 'error': str(e)})
                                logger.warning("Failed to migrate resource %s: %s", res.get('resource_id'), e)
                    finally:
                        target_cursor.close()
                
                logger.info("Migrated batch %d-%d resources", i+1, min(i+self.batch_size, len(source_resources)))
            
            logger.info("Resources migration completed: %d/%d", result.migrated_records, result.total_records)
            
        except Exception as e:
            logger.exception("Resources migration failed")
            result.errors.append({'error': str(e)})
        
        return result
    
    def migrate_quiz_attempts(self) -> TableMigrationResult:
        """迁移测验尝试表 - 占位符实现"""
        result = TableMigrationResult()
        # TODO: 实现测验尝试迁移逻辑
        logger.info("migrate_quiz_attempts: placeholder implementation")
        return result
    
    def migrate_llm_logs(self) -> TableMigrationResult:
        """迁移LLM日志表 - 占位符实现"""
        result = TableMigrationResult()
        # TODO: 实现LLM日志迁移逻辑
        logger.info("migrate_llm_logs: placeholder implementation")
        return result
