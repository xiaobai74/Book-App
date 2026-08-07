"""
书籍模型

映射 MySQL `books` 表。
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.chapter import Chapter  # noqa: F401  确保 Chapter 模型已注册


def _now_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Book(Base):
    __tablename__ = "books"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    author: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="未知",
        server_default="未知",
    )
    source_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )
    epub_path: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )
    txt_path: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="idle",
        server_default="idle",
    )
    chapter_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    is_marked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        comment="标记状态：True=已标记/置顶，False=普通",
    )
    marked_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        default=None,
        comment="标记时间（用于置顶排序）",
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=_now_utc,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=_now_utc,
        server_default=func.now(),
        onupdate=_now_utc,
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        default=None,
    )
    ai_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
        comment="AI 生成的书籍摘要（含角色列表和风格标签）",
    )
    ai_summary_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        default=None,
        comment="AI 摘要生成时间",
    )

    # 关联
    user: Mapped["User"] = relationship(
        "User",
        back_populates="books",
        lazy="selectin",
    )
    chapters: Mapped[list["Chapter"]] = relationship(
        "Chapter",
        back_populates="book",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    reading_progress: Mapped["ReadingProgress | None"] = relationship(
        "ReadingProgress",
        back_populates="book",
        uselist=False,
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Book(id={self.id!r}, title={self.title!r})>"
