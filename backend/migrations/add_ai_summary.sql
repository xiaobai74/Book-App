-- AI 摘要功能迁移（v1.3）
-- 为 books 表新增 AI 摘要和生成时间字段
-- 使用 information_schema 判断，支持重复执行（MySQL 8.0 兼容，非 MariaDB 语法）

SET @col_exists := (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'books' AND COLUMN_NAME = 'ai_summary'
);
SET @sql := IF(@col_exists = 0,
    'ALTER TABLE `books` ADD COLUMN `ai_summary` TEXT NULL COMMENT ''AI 生成的书籍摘要（含角色列表和风格标签）''',
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @col_exists := (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'books' AND COLUMN_NAME = 'ai_summary_at'
);
SET @sql := IF(@col_exists = 0,
    'ALTER TABLE `books` ADD COLUMN `ai_summary_at` DATETIME NULL COMMENT ''AI 摘要生成时间''',
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
