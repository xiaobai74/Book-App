"""
阅读进度模型

映射 MySQL `reading_progress` 表，记录用户每本书的最后阅读章节。
v1.2 新增。
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _now_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ReadingProgress(Base):
    __tablename__ = "reading_progress"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    book_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("books.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # 每本书只保留一条进度记录
        comment="关联的书籍 ID",
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联的用户 ID",
    )
    last_chapter_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
        comment="最后阅读的章节序号（从 1 开始）",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=_now_utc,
        server_default=func.now(),
        onupdate=_now_utc,
        nullable=False,
        comment="最后更新时间",
    )

    # 关联
    book: Mapped["Book"] = relationship(
        "Book", back_populates="reading_progress", lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<ReadingProgress(book={self.book_id!r}, "
            f"chapter={self.last_chapter_index})>"
        )
