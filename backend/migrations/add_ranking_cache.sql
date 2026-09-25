-- 排行榜持久化缓存表
-- 用于 MySQL 部署环境手动迁移（SQLite 桌面版由 create_all 自动建表）

CREATE TABLE IF NOT EXISTS ranking_cache (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source_id INT NOT NULL,
    board_index INT NOT NULL,
    items_json TEXT NOT NULL,
    fetched_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_ranking_source_board UNIQUE (source_id, board_index),
    INDEX ix_ranking_cache_source_id (source_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
