-- MySQL数据库表结构
-- 用于AI教育系统的数据库迁移项目

-- 设置字符集和排序规则
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- 用户主表
CREATE TABLE IF NOT EXISTS users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    login_id VARCHAR(50) UNIQUE NOT NULL,
    user_type ENUM('student', 'teacher', 'admin') NOT NULL,
    username VARCHAR(100) NOT NULL,
    password VARCHAR(255),
    display_name VARCHAR(200),
    teacher_id INT,
    email VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_type_username (user_type, username),
    INDEX idx_login_id (login_id),
    INDEX idx_teacher_id (teacher_id),
    INDEX idx_username (username),
    FOREIGN KEY (teacher_id) REFERENCES users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 用户扩展信息表
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id INT PRIMARY KEY,
    avatar_url VARCHAR(500),
    phone VARCHAR(20),
    address VARCHAR(500),
    bio TEXT,
    preferences JSON,
    metadata JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 学习计划主表
CREATE TABLE IF NOT EXISTS learning_plans (
    plan_id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(100) NOT NULL,
    user_id INT NOT NULL,
    filename VARCHAR(255) NOT NULL,
    plan_path VARCHAR(500),
    category ENUM('global', 'user', 'path') DEFAULT 'user',
    title VARCHAR(500),
    description TEXT,
    status ENUM('draft', 'active', 'completed', 'archived') DEFAULT 'draft',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_username_filename (username, filename),
    INDEX idx_user_id (user_id),
    INDEX idx_category (category),
    INDEX idx_status (status),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 学习计划节点表
CREATE TABLE IF NOT EXISTS learning_plan_nodes (
    node_id INT PRIMARY KEY AUTO_INCREMENT,
    plan_id INT NOT NULL,
    node_key VARCHAR(100) NOT NULL,
    node_name VARCHAR(500),
    node_type VARCHAR(50),
    sequence_order INT DEFAULT 0,
    parent_node_id INT,
    content JSON,
    metadata JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_plan_node (plan_id, node_key),
    INDEX idx_plan_id (plan_id),
    INDEX idx_parent_node (parent_node_id),
    FOREIGN KEY (plan_id) REFERENCES learning_plans(plan_id) ON DELETE CASCADE,
    FOREIGN KEY (parent_node_id) REFERENCES learning_plan_nodes(node_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 恢复外键检查
SET FOREIGN_KEY_CHECKS = 1;