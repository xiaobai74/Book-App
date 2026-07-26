"""
自定义抓取源站模型

用户可创建和管理自己的源站抓取规则，存储在数据库中。
"""

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _now_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class CrawlSource(Base):
    """用户自定义的小说抓取源站规则"""

    __tablename__ = "crawl_sources"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="源站名称",
    )
    url: Mapped[str] = mapped_column(
        String(2048),
        nullable=False,
        comment="源站域名/首页 URL",
    )
    rule_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="JSON 格式的抓取规则（toc/chapter 选择器）",
    )
    is_public: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        comment="是否公开给所有用户",
    )
    created_at: Mapped[datetime] = mapped_column(
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

    # 关联
    user: Mapped["User"] = relationship(
        "User",
        back_populates="crawl_sources",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<CrawlSource(id={self.id}, name={self.name!r})>"
