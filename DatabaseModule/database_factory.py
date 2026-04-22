"""
数据库工厂类

根据配置创建相应的数据库存储实例，支持SQLite和MySQL的动态切换。
"""

import os
import logging
from typing import Any, Dict, Optional
from pathlib import Path

from .database_store import DatabaseStore
from .sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)


class DatabaseFactory:
    """数据库工厂类
    
    根据环境变量或配置文件创建相应的数据库存储实例。
    支持SQLite和MySQL的动态切换，提供单例模式访问。
    """
    
    _instance: Optional[DatabaseStore] = None
    _config_cache: Optional[Dict[str, Any]] = None

    @classmethod
    def create_store(cls, config: Optional[Dict[str, Any]] = None) -> DatabaseStore:
        """根据配置创建数据库存储实例
        
        Args:
            config: 数据库配置字典，如果为None则从环境变量加载
            
        Returns:
            DatabaseStore实例
            
        Raises:
            ValueError: 不支持的数据库类型
            ImportError: 缺少必要的依赖包
            ConnectionError: 数据库连接失败
        """
        if config is None:
            config = cls._load_config_from_env()
        
        # 验证配置
        cls._validate_config(config)
        
        db_type = config.get('type', 'sqlite').lower()
        
        try:
            if db_type == 'mysql':
                # 动态导入MySQLStore以避免循环导入
                from .mysql_store import MySQLStore
                
                return MySQLStore(
                    host=config['host'],
                    port=config.get('port', 3306),
                    user=config['user'],
                    password=config['password'],
                    database=config['database'],
                    charset=config.get('charset', 'utf8mb4'),
                    **config.get('extra_params', {})
                )
            elif db_type == 'sqlite':
                return SQLiteStore(db_path=config.get('path', 'data/app.db'))
            else:
                raise ValueError(f"Unsupported database type: {db_type}")
                
        except ImportError as e:
            if 'pymysql' in str(e):
                raise ImportError(
                    "MySQL support requires pymysql. Install with: pip install pymysql"
                ) from e
            raise
        except Exception as e:
            logger.error("Failed to create database store: %s", e)
            raise ConnectionError(f"Failed to create database store: {e}") from e

    @classmethod
    def get_store(cls) -> DatabaseStore:
        """获取单例数据库存储实例
        
        Returns:
            DatabaseStore实例
        """
        if cls._instance is None:
            cls._instance = cls.create_store()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """重置单例实例
        
        用于测试或配置更改时重新创建实例。
        """
        cls._instance = None
        cls._config_cache = None

    @classmethod
    def _load_config_from_env(cls) -> Dict[str, Any]:
        """从环境变量加载数据库配置
        
        Returns:
            数据库配置字典
        """
        if cls._config_cache is not None:
            return cls._config_cache
        
        # 尝试加载.env文件
        cls._load_env_file()
        
        db_type = os.getenv('DB_TYPE', 'sqlite').lower()
        
        if db_type == 'mysql':
            config = {
                'type': 'mysql',
                'host': os.getenv('DB_HOST', 'localhost'),
                'port': int(os.getenv('DB_PORT', '3306')),
                'user': os.getenv('DB_USER', 'root'),
                'password': os.getenv('DB_PASSWORD', ''),
                'database': os.getenv('DB_NAME', 'ai_education'),
                'charset': os.getenv('DB_CHARSET', 'utf8mb4'),
            }
            
            # 添加SSL配置（如果提供）
            ssl_ca = os.getenv('DB_SSL_CA')
            ssl_cert = os.getenv('DB_SSL_CERT')
            ssl_key = os.getenv('DB_SSL_KEY')
            
            if ssl_ca or ssl_cert or ssl_key:
                config['extra_params'] = {
                    'ssl_ca': ssl_ca,
                    'ssl_cert': ssl_cert,
                    'ssl_key': ssl_key,
                    'ssl_verify_cert': os.getenv('DB_SSL_VERIFY', 'true').lower() == 'true'
                }
        else:
            config = {
                'type': 'sqlite',
                'path': os.getenv('DB_PATH', 'data/app.db')
            }
        
        cls._config_cache = config
        logger.info("Loaded database config: type=%s", config['type'])
        
        return config

    @classmethod
    def _load_env_file(cls) -> None:
        """加载.env文件中的环境变量"""
        env_path = Path('.env')
        if not env_path.exists():
            return
        
        try:
            with env_path.open('r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key and key not in os.environ:
                            os.environ[key] = value
        except Exception as e:
            logger.warning("Failed to load .env file: %s", e)

    @classmethod
    def _validate_config(cls, config: Dict[str, Any]) -> None:
        """验证数据库配置的完整性和有效性
        
        Args:
            config: 数据库配置字典
            
        Raises:
            ValueError: 配置无效
        """
        if not isinstance(config, dict):
            raise ValueError("Database config must be a dictionary")
        
        db_type = config.get('type', '').lower()
        
        if db_type == 'mysql':
            required_fields = ['host', 'user', 'password', 'database']
            missing_fields = [field for field in required_fields if not config.get(field)]
            
            if missing_fields:
                raise ValueError(
                    f"MySQL configuration missing required fields: {', '.join(missing_fields)}"
                )
            
            # 验证端口号
            port = config.get('port', 3306)
            if not isinstance(port, int) or port <= 0 or port > 65535:
                raise ValueError(f"Invalid MySQL port: {port}")
                
        elif db_type == 'sqlite':
            db_path = config.get('path', 'data/app.db')
            if not db_path:
                raise ValueError("SQLite configuration missing database path")
                
            # 确保目录存在
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            
        else:
            raise ValueError(f"Unsupported database type: {db_type}")

    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """获取当前数据库配置
        
        Returns:
            数据库配置字典
        """
        return cls._load_config_from_env()

    @classmethod
    def test_connection(cls, config: Optional[Dict[str, Any]] = None) -> bool:
        """测试数据库连接
        
        Args:
            config: 数据库配置，如果为None则使用当前配置
            
        Returns:
            连接是否成功
        """
        try:
            store = cls.create_store(config)
            with store.connection():
                pass  # 只测试连接，不执行任何操作
            return True
        except Exception as e:
            logger.error("Database connection test failed: %s", e)
            return False
