-- ============================================================
-- 小说管理App — MySQL 数据库初始化脚本
-- 数据库名: book
-- 目标: MySQL 8.0+, 端口 3306
-- 用法: mysql -u root -p < scripts/init_db.sql
-- ============================================================

-- 1. 创建数据库
CREATE DATABASE IF NOT EXISTS `book`
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE `book`;

-- ============================================================
-- 2. 用户表
-- ============================================================
CREATE TABLE IF NOT EXISTS `users` (
    `id`            CHAR(36)     NOT NULL COMMENT '用户唯一标识 (UUID v4)',
    `email`         VARCHAR(255) NOT NULL COMMENT '邮箱，用作登录账号',
    `password_hash` VARCHAR(255) NOT NULL COMMENT 'bcrypt 哈希后的密码',
    `created_at`    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '注册时间',
    `updated_at`    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
    `deleted_at`    TIMESTAMP    NULL     DEFAULT NULL COMMENT '软删除时间，NULL 表示未删除',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_users_email` (`email`),
    INDEX `idx_users_deleted_at` (`deleted_at`),
    INDEX `idx_users_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='用户表';

-- ============================================================
-- 3. 小说书架表
-- ============================================================
CREATE TABLE IF NOT EXISTS `books` (
    `id`            CHAR(36)      NOT NULL COMMENT '书籍唯一标识 (UUID v4)',
    `user_id`       CHAR(36)      NOT NULL COMMENT '所属用户 ID',
    `title`         VARCHAR(500)  NOT NULL COMMENT '书名',
    `author`        VARCHAR(255)  NOT NULL DEFAULT '未知' COMMENT '作者',
    `source_url`    TEXT          NULL     DEFAULT NULL COMMENT '源网站 URL',
    `epub_path`     VARCHAR(1000) NULL     DEFAULT NULL COMMENT '生成的 .epub 文件存储路径',
    `status`        ENUM('idle', 'crawling', 'done', 'failed')
                                  NOT NULL DEFAULT 'idle' COMMENT '抓取状态: idle=待抓取, crawling=抓取中, done=已完成, failed=失败',
    `chapter_count` INT           NOT NULL DEFAULT 0 COMMENT '已抓取章节数',
    `added_at`      TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '添加到书架的时间',
    `updated_at`    TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
    `deleted_at`    TIMESTAMP     NULL     DEFAULT NULL COMMENT '软删除时间，NULL 表示未删除',
    PRIMARY KEY (`id`),
    INDEX `idx_books_user_id` (`user_id`),
    INDEX `idx_books_status` (`status`),
    INDEX `idx_books_added_at` (`added_at`),
    INDEX `idx_books_deleted_at` (`deleted_at`),
    INDEX `idx_books_user_not_deleted` (`user_id`, `deleted_at`),
    CONSTRAINT `fk_books_user_id` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='小说书架表';

-- ============================================================
-- 4. JWT Refresh Token 表
--    存储已签发的 Refresh Token 哈希值，支持吊销与轮转
-- ============================================================
CREATE TABLE IF NOT EXISTS `refresh_tokens` (
    `id`         CHAR(36)     NOT NULL COMMENT 'Token 唯一标识 (UUID v4)',
    `user_id`    CHAR(36)     NOT NULL COMMENT '所属用户 ID',
    `token_hash` VARCHAR(255) NOT NULL COMMENT 'Refresh Token 的 SHA-256 哈希值',
    `expires_at` TIMESTAMP    NOT NULL COMMENT 'Token 过期时间 (7天)',
    `created_at` TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Token 签发时间',
    `revoked_at` TIMESTAMP    NULL     DEFAULT NULL COMMENT '吊销时间，NULL 表示仍有效',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_rt_token_hash` (`token_hash`),
    INDEX `idx_rt_user_id` (`user_id`),
    INDEX `idx_rt_expires_at` (`expires_at`),
    CONSTRAINT `fk_rt_user_id` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='JWT Refresh Token 表';

-- ============================================================
-- 5. UUID 自动生成触发器
--    当 INSERT 未提供 id 时，自动填充 UUID()
-- ============================================================
DELIMITER //

DROP TRIGGER IF EXISTS `trg_users_before_insert`//
CREATE TRIGGER `trg_users_before_insert`
BEFORE INSERT ON `users`
FOR EACH ROW
BEGIN
    IF NEW.`id` IS NULL OR NEW.`id` = '' THEN
        SET NEW.`id` = UUID();
    END IF;
END;//

DROP TRIGGER IF EXISTS `trg_books_before_insert`//
CREATE TRIGGER `trg_books_before_insert`
BEFORE INSERT ON `books`
FOR EACH ROW
BEGIN
    IF NEW.`id` IS NULL OR NEW.`id` = '' THEN
        SET NEW.`id` = UUID();
    END IF;
END;//

DROP TRIGGER IF EXISTS `trg_refresh_tokens_before_insert`//
CREATE TRIGGER `trg_refresh_tokens_before_insert`
BEFORE INSERT ON `refresh_tokens`
FOR EACH ROW
BEGIN
    IF NEW.`id` IS NULL OR NEW.`id` = '' THEN
        SET NEW.`id` = UUID();
    END IF;
END;//

DELIMITER ;

-- ============================================================
-- 初始化完成
-- ============================================================
-- 验证建表结果:
--   SHOW TABLES;
--   DESCRIBE users;
--   DESCRIBE books;
--   DESCRIBE refresh_tokens;
--   SHOW TRIGGERS;
