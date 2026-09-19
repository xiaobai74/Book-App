-- 章节正文扩容迁移（修复 MySQL 1406 Data too long for column 'content'）
-- MySQL 的 TEXT 仅 65,535 字节，utf8mb4 下中文约 3 字节/字，
-- 超过约 2 万字的长章节会触发 1406。改为 MEDIUMTEXT（16MB）。
-- MODIFY 可重复执行（幂等）。桌面版 SQLite 的 TEXT 无长度限制，无需执行。

ALTER TABLE `chapters`
    MODIFY COLUMN `content` MEDIUMTEXT NOT NULL COMMENT '章节正文';
