-- AI 摘要功能迁移（v1.3）
-- 为 books 表新增 AI 摘要和生成时间字段

ALTER TABLE books
  ADD COLUMN ai_summary TEXT NULL
  COMMENT 'AI 生成的书籍摘要（含角色列表和风格标签）';

ALTER TABLE books
  ADD COLUMN ai_summary_at DATETIME NULL
  COMMENT 'AI 摘要生成时间';
