"""
数据库存储抽象层

提供统一的 MySQL 数据访问接口。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Any, Dict, Iterable, List, Optional


class DatabaseStore(ABC):
    """数据库存储抽象基类
    
    定义统一的数据库访问接口。当前 zyh 分支只保留 MySQL 实现。
    """

    # ==================== 连接管理 ====================
    
    @abstractmethod
    @contextmanager
    def connection(self):
        """获取数据库连接的上下文管理器
        
        使用示例:
            with store.connection() as conn:
                # 执行数据库操作
                pass
        
        Yields:
            数据库连接对象
        """
        pass

    # ==================== 用户管理 ====================
    
    @abstractmethod
    def list_users(self, user_type: str) -> List[Dict[str, Any]]:
        """列出指定类型的所有用户
        
        Args:
            user_type: 用户类型 ('student', 'teacher', 'admin')
            
        Returns:
            用户信息列表
        """
        pass

    @abstractmethod
    def get_user(self, user_type: str, username: str) -> Optional[Dict[str, Any]]:
        """根据用户类型和用户名获取用户信息
        
        Args:
            user_type: 用户类型
            username: 用户名
            
        Returns:
            用户信息字典，不存在则返回None
        """
        pass

    @abstractmethod
    def get_user_by_identifier(self, user_type: str, identifier: str) -> Optional[Dict[str, Any]]:
        """根据标识符获取用户信息
        
        标识符可以是: login_id, user_id, username
        
        Args:
            user_type: 用户类型
            identifier: 用户标识符
            
        Returns:
            用户信息字典，不存在则返回None
        """
        pass

    @abstractmethod
    def get_user_by_user_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """根据user_id获取用户信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户信息字典，不存在则返回None
        """
        pass

    @abstractmethod
    def resolve_user_identity(self, user_type: str, identifier: str) -> Dict[str, Any]:
        """解析用户身份信息
        
        Args:
            user_type: 用户类型
            identifier: 用户标识符
            
        Returns:
            包含username, user_id, login_id的字典
        """
        pass

    @abstractmethod
    def replace_users(self, user_type: str, users: Iterable[Dict[str, Any]]) -> None:
        """替换指定类型的所有用户
        
        Args:
            user_type: 用户类型
            users: 用户信息列表
        """
        pass

    # ==================== 教师-学生关系 ====================
    
    @abstractmethod
    def list_teacher_students(self, teacher_identifier: str) -> List[Dict[str, Any]]:
        """列出教师的所有学生
        
        Args:
            teacher_identifier: 教师标识符
            
        Returns:
            学生信息列表
        """
        pass

    # ==================== 数字孪生画像 ====================
    
    @abstractmethod
    def save_twin_profile(self, username: str, payload: Dict[str, Any]) -> None:
        """保存数字孪生画像
        
        Args:
            username: 用户名
            payload: 画像数据
        """
        pass

    @abstractmethod
    def get_twin_profile(self, username: str) -> Optional[Dict[str, Any]]:
        """获取数字孪生画像
        
        Args:
            username: 用户名
            
        Returns:
            画像数据，不存在则返回None
        """
        pass

    @abstractmethod
    def list_twin_profiles(self) -> List[Dict[str, Any]]:
        """列出所有数字孪生画像
        
        Returns:
            画像数据列表
        """
        pass

    @abstractmethod
    def save_twin_history(self, username: str, snapshot_date: str, payload: Dict[str, Any]) -> None:
        """保存数字孪生历史快照
        
        Args:
            username: 用户名
            snapshot_date: 快照日期
            payload: 快照数据
        """
        pass

    @abstractmethod
    def get_twin_history(self, username: str) -> List[Dict[str, Any]]:
        """获取数字孪生历史记录
        
        Args:
            username: 用户名
            
        Returns:
            历史快照列表
        """
        pass

    # ==================== 会话管理 ====================
    
    @abstractmethod
    def save_session(self, session_id: str, payload: Dict[str, Any]) -> None:
        """保存会话信息
        
        Args:
            session_id: 会话ID
            payload: 会话数据
        """
        pass

    @abstractmethod
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话信息
        
        Args:
            session_id: 会话ID
            
        Returns:
            会话数据，不存在则返回None
        """
        pass

    @abstractmethod
    def delete_session(self, session_id: str) -> None:
        """删除会话
        
        Args:
            session_id: 会话ID
        """
        pass

    @abstractmethod
    def list_sessions(self) -> List[Dict[str, Any]]:
        """列出所有会话
        
        Returns:
            会话数据列表
        """
        pass

    @abstractmethod
    def list_sessions_for_user(
        self, 
        user_type: str, 
        user_identifier: str, 
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """列出用户的会话
        
        Args:
            user_type: 用户类型
            user_identifier: 用户标识符
            limit: 返回数量限制
            
        Returns:
            会话数据列表
        """
        pass

    # ==================== 用户状态 ====================
    
    @abstractmethod
    def save_user_state(self, username: str, payload: Dict[str, Any]) -> None:
        """保存用户状态
        
        Args:
            username: 用户名
            payload: 状态数据
        """
        pass

    @abstractmethod
    def get_user_state(self, username: str) -> Optional[Dict[str, Any]]:
        """获取用户状态
        
        Args:
            username: 用户名
            
        Returns:
            状态数据，不存在则返回None
        """
        pass

    # ==================== LLM日志 ====================
    
    @abstractmethod
    def append_llm_log(self, payload: Dict[str, Any]) -> None:
        """追加LLM日志
        
        Args:
            payload: 日志数据
        """
        pass

    @abstractmethod
    def replace_llm_logs(self, logs: Iterable[Dict[str, Any]]) -> None:
        """替换所有LLM日志
        
        Args:
            logs: 日志数据列表
        """
        pass

    @abstractmethod
    def list_llm_logs(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """列出LLM日志
        
        Args:
            limit: 返回数量限制
            
        Returns:
            日志数据列表
        """
        pass

    @abstractmethod
    def list_llm_logs_for_user(
        self,
        user_identifier: str,
        user_type: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """列出用户的LLM日志
        
        Args:
            user_identifier: 用户标识符
            user_type: 用户类型
            limit: 返回数量限制
            
        Returns:
            日志数据列表
        """
        pass

    # ==================== 学习计划 ====================
    
    @abstractmethod
    def save_learning_plan(
        self,
        username: str,
        filename: str,
        payload: Any,
        plan_path: Optional[str] = None,
        category: Optional[str] = None,
    ) -> None:
        """保存学习计划
        
        Args:
            username: 用户名
            filename: 文件名
            payload: 计划数据
            plan_path: 计划路径
            category: 分类
        """
        pass

    @abstractmethod
    def list_learning_plans(
        self,
        username: Optional[str] = None,
        categories: Optional[Iterable[str]] = None,
    ) -> List[Dict[str, Any]]:
        """列出学习计划
        
        Args:
            username: 用户名（可选）
            categories: 分类列表（可选）
            
        Returns:
            学习计划列表
        """
        pass

    @abstractmethod
    def list_learning_plans_by_user_identifier(
        self,
        user_identifier: str,
        user_type: Optional[str] = None,
        categories: Optional[Iterable[str]] = None,
    ) -> List[Dict[str, Any]]:
        """根据用户标识符列出学习计划
        
        Args:
            user_identifier: 用户标识符
            user_type: 用户类型
            categories: 分类列表（可选）
            
        Returns:
            学习计划列表
        """
        pass

    @abstractmethod
    def get_latest_learning_plan(
        self,
        username: str,
        category: Optional[str] = None,
        filename_prefix: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """获取最新的学习计划
        
        Args:
            username: 用户名
            category: 分类（可选）
            filename_prefix: 文件名前缀（可选）
            
        Returns:
            学习计划数据，不存在则返回None
        """
        pass

    def save_learning_path_version(
        self,
        username: str,
        payload: Any,
        *,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """保存个性化学习路径版本。"""
        raise NotImplementedError

    def list_learning_path_versions(
        self,
        *,
        username: str,
        course_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """列出个性化学习路径版本。"""
        raise NotImplementedError

    # ==================== 课程管理 ====================
    
    @abstractmethod
    def sync_course_from_graph(
        self,
        course_id: str,
        graph_data: Dict[str, Any],
        *,
        course_name: Optional[str] = None,
        source_path: Optional[str] = None,
        lifecycle_status: Optional[str] = None,
        updated_by: Optional[str] = None,
    ) -> Dict[str, int]:
        """从课程图谱同步课程数据
        
        Args:
            course_id: 课程ID
            graph_data: 课程图谱数据
            course_name: 课程名称（可选）
            source_path: 源路径（可选）
            
        Returns:
            包含nodes和resources数量的字典
        """
        pass

    @abstractmethod
    def list_courses(self) -> List[Dict[str, Any]]:
        """列出课程建设底座。"""
        pass

    @abstractmethod
    def get_course_summary(self, course_id: str) -> Optional[Dict[str, Any]]:
        """获取课程结构、资源和发布状态摘要。"""
        pass

    @abstractmethod
    def publish_course(self, course_id: str, published_by: Optional[str] = None) -> bool:
        """发布课程底座。"""
        pass

    @abstractmethod
    def list_course_resources(self, course_id: str) -> List[Dict[str, Any]]:
        """列出课程资源审核清单。"""
        pass

    @abstractmethod
    def set_resource_review_status(
        self,
        course_id: str,
        node_id: str,
        resource_path: str,
        *,
        is_enabled: bool,
        review_status: str = "enabled",
        quality_status: Optional[str] = None,
    ) -> bool:
        """设置课程资源审核状态。"""
        pass

    @abstractmethod
    def upsert_career_position(
        self,
        course_id: str,
        position_name: str,
        *,
        position_type: str = "related",
        target_rank: int = 0,
        source_keyword: Optional[str] = None,
        created_by: Optional[int] = None,
    ) -> Dict[str, Any]:
        """保存课程目标岗位配置。"""
        pass

    @abstractmethod
    def list_course_positions(self, course_id: str) -> List[Dict[str, Any]]:
        """列出课程已配置的主要岗位和关联岗位。"""
        pass

    @abstractmethod
    def upsert_career_abilities(self, position_id: int, abilities: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        """保存某岗位下的职业能力候选。"""
        pass

    @abstractmethod
    def list_course_abilities(self, course_id: str) -> List[Dict[str, Any]]:
        """列出课程岗位下的职业能力。"""
        pass

    @abstractmethod
    def upsert_course_ability_mappings(
        self,
        course_id: str,
        mappings: Iterable[Dict[str, Any]],
        *,
        updated_by: Optional[int] = None,
    ) -> Dict[str, Any]:
        """保存职业能力与叶子知识点支撑关系。"""
        pass

    @abstractmethod
    def list_course_ability_mappings(self, course_id: str) -> List[Dict[str, Any]]:
        """列出课程职业能力到叶子知识点的映射矩阵。"""
        pass

    @abstractmethod
    def review_course_ability_mapping(
        self,
        mapping_id: int,
        *,
        review_status: str,
        support_level: Optional[str] = None,
        reviewed_by: Optional[int] = None,
    ) -> bool:
        """教师审核、确认或驳回能力映射。"""
        pass

    @abstractmethod
    def evaluate_course_runtime(
        self,
        course_id: str,
        *,
        window_days: int = 30,
        min_quiz_attempts: int = 3,
    ) -> Optional[Dict[str, Any]]:
        """按课程结构、资源、测评证据、运行风险和能力支撑评估课程运行状态。"""
        pass

    @abstractmethod
    def get_course_payload(self, course_id: str) -> Optional[Dict[str, Any]]:
        """获取课程数据
        
        Args:
            course_id: 课程ID
            
        Returns:
            课程数据，不存在则返回None
        """
        pass

    @abstractmethod
    def get_course_id_by_resource_path(self, resource_path: str) -> Optional[str]:
        """根据资源路径获取课程ID
        
        Args:
            resource_path: 资源路径
            
        Returns:
            课程ID，不存在则返回None
        """
        pass

    @abstractmethod
    def list_learning_nodes_for_course(self, course_id: str) -> List[str]:
        """列出课程的所有学习节点
        
        Args:
            course_id: 课程ID
            
        Returns:
            节点名称列表
        """
        pass

    @abstractmethod
    def list_resources_for_node_name(self, course_id: str, node_name: str) -> List[str]:
        """列出节点的所有资源
        
        Args:
            course_id: 课程ID
            node_name: 节点名称
            
        Returns:
            资源路径列表
        """
        pass

    # ==================== 测验记录 ====================
    
    @abstractmethod
    def record_quiz_attempt(
        self,
        *,
        username: Optional[str],
        user_id: Optional[int],
        course_id: Optional[str],
        node_id: Optional[str],
        score: float,
        total: float,
        passed: bool,
        extra_payload: Optional[Dict[str, Any]] = None,
    ) -> int:
        """记录测验尝试
        
        Args:
            username: 用户名
            user_id: 用户ID
            course_id: 课程ID
            node_id: 节点ID
            score: 得分
            total: 总分
            passed: 是否通过
            extra_payload: 额外数据
            
        Returns:
            attempt_id
        """
        pass

    # ==================== 资源软删除 ====================
    
    @abstractmethod
    def soft_delete_resource(
        self,
        course_id: str,
        node_id: str,
        resource_path: str,
        deleted_by: Optional[str] = None
    ) -> bool:
        """软删除资源
        
        Args:
            course_id: 课程ID
            node_id: 节点ID
            resource_path: 资源路径
            deleted_by: 删除者
            
        Returns:
            是否成功
        """
        pass

    @abstractmethod
    def restore_resource(
        self,
        course_id: str,
        node_id: str,
        resource_path: str
    ) -> bool:
        """恢复已删除的资源
        
        Args:
            course_id: 课程ID
            node_id: 节点ID
            resource_path: 资源路径
            
        Returns:
            是否成功
        """
        pass

    @abstractmethod
    def list_deleted_resources(
        self,
        course_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """列出已删除的资源（回收站）
        
        Args:
            course_id: 课程ID（可选，用于过滤）
            
        Returns:
            已删除资源列表
        """
        pass

    @abstractmethod
    def permanently_delete_resource(
        self,
        course_id: str,
        node_id: str,
        resource_path: str
    ) -> bool:
        """永久删除资源
        
        Args:
            course_id: 课程ID
            node_id: 节点ID
            resource_path: 资源路径
            
        Returns:
            是否成功
        """
        pass
