-- 源站元数据迁移（v1.7）
-- 为 books 表新增：封面本地路径 / 封面原始 URL / 简介 / 分类 / 最新章节 / 最后更新时间
-- 使用 information_schema 判断，支持重复执行（MySQL 8.0 兼容，非 MariaDB 语法）
-- 桌面版（SQLite）由 main.py 的 create_all 自动建列，无需执行本脚本

SET @col_exists := (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'books' AND COLUMN_NAME = 'cover_path'
);
SET @sql := IF(@col_exists = 0,
    'ALTER TABLE `books` ADD COLUMN `cover_path` VARCHAR(1000) NULL COMMENT ''封面图片本地路径（从源站下载）''',
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @col_exists := (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'books' AND COLUMN_NAME = 'cover_url'
);
SET @sql := IF(@col_exists = 0,
    'ALTER TABLE `books` ADD COLUMN `cover_url` VARCHAR(2048) NULL COMMENT ''源站封面图片原始 URL''',
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @col_exists := (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'books' AND COLUMN_NAME = 'description'
);
SET @sql := IF(@col_exists = 0,
    'ALTER TABLE `books` ADD COLUMN `description` TEXT NULL COMMENT ''小说简介（源站抓取）''',
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @col_exists := (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'books' AND COLUMN_NAME = 'category'
);
SET @sql := IF(@col_exists = 0,
    'ALTER TABLE `books` ADD COLUMN `category` VARCHAR(255) NULL COMMENT ''分类（源站抓取）''',
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @col_exists := (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'books' AND COLUMN_NAME = 'latest_chapter'
);
SET @sql := IF(@col_exists = 0,
    'ALTER TABLE `books` ADD COLUMN `latest_chapter` VARCHAR(500) NULL COMMENT ''最新章节名（源站抓取）''',
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @col_exists := (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'books' AND COLUMN_NAME = 'last_update_time'
);
SET @sql := IF(@col_exists = 0,
    'ALTER TABLE `books` ADD COLUMN `last_update_time` VARCHAR(100) NULL COMMENT ''源站最后更新时间（原始文本）''',
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
