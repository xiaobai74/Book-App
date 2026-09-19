"""
章节模型

映射 MySQL `chapters` 表，存储已抓取的小说章节内容。
"""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.book import Book


def _now_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Chapter(Base):
    __tablename__ = "chapters"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    book_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("books.id", ondelete="CASCADE"),
        nullable=False,
    )
    index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="章节序号（从 1 开始）",
    )
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="章节标题",
    )
    content: Mapped[str] = mapped_column(
        # MySQL 的 TEXT 仅 64KB（utf8mb4 下中文约 3 字节/字，长章节易超），
        # 改用 MEDIUMTEXT（16MB）；SQLite 的 TEXT 无长度限制，保持默认。
        Text().with_variant(MEDIUMTEXT, "mysql"),
        nullable=False,
        comment="章节正文",
    )
    word_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="字数统计",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=_now_utc,
        server_default=func.now(),
        nullable=False,
    )

    # 关联
    book: Mapped["Book"] = relationship("Book", back_populates="chapters", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Chapter(book={self.book_id!r}, index={self.index}, title={self.title!r})>"
