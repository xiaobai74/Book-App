-- ═══════════════════════════════════════════════════════════════
-- 小说管理App · v1.2 数据库迁移脚本
-- 日期: 2026-08-05
-- 说明: 新增标记置顶字段 + 阅读进度表
-- 运行方式: mysql -u <user> -p <db> < v1.2_migration.sql
-- ═══════════════════════════════════════════════════════════════

-- ── 1. books 表新增标记字段 ──────────────────────────────
-- 若数据库中不存在该列则添加（支持重复执行）

ALTER TABLE `books`
    ADD COLUMN IF NOT EXISTS `is_marked` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '标记状态：1=已标记/置顶，0=普通',
    ADD COLUMN IF NOT EXISTS `marked_at` DATETIME NULL DEFAULT NULL COMMENT '标记时间（用于置顶排序）';

-- 为标记排序创建复合索引（提升书架列表查询性能）
CREATE INDEX IF NOT EXISTS `idx_books_user_marked` ON `books` (`user_id`, `is_marked` DESC, `marked_at` DESC, `deleted_at`);


-- ── 2. 新建 reading_progress 表 ──────────────────────────

CREATE TABLE IF NOT EXISTS `reading_progress` (
    `id` VARCHAR(36) NOT NULL,
    `book_id` VARCHAR(36) NOT NULL COMMENT '关联的书籍 ID',
    `user_id` VARCHAR(36) NOT NULL COMMENT '关联的用户 ID',
    `last_chapter_index` INT NOT NULL DEFAULT 1 COMMENT '最后阅读的章节序号（从 1 开始）',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',

    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_book_id` (`book_id`),          -- 每本书只保留一条进度记录，使用 upsert 更新
    KEY `idx_user_id` (`user_id`),                 -- 按用户查询所有书籍进度

    CONSTRAINT `fk_progress_book` FOREIGN KEY (`book_id`) REFERENCES `books` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_progress_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='阅读进度表（v1.2 新增）';


-- ── 3. 回滚脚本（仅供参考，不执行） ──────────────────────
-- DROP TABLE IF EXISTS `reading_progress`;
-- ALTER TABLE `books` DROP COLUMN IF EXISTS `is_marked`, DROP COLUMN IF EXISTS `marked_at`;
-- DROP INDEX IF EXISTS `idx_books_user_marked` ON `books`;
