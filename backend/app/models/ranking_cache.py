"""排行榜持久化缓存模型

将榜单抓取结果序列化后存入数据库，进程重启后无需重新抓取源站。
配合 RankingService 实现三级缓存：内存 → DB → 实时抓取。
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, Text, UniqueConstraint

from app.database import Base


class RankingCache(Base):
    """排行榜缓存表

    source_id + board_index 联合唯一，每个榜单只保留最新一次抓取结果。
    """

    __tablename__ = "ranking_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, nullable=False, index=True)
    board_index = Column(Integer, nullable=False)
    items_json = Column(Text, nullable=False)  # JSON 序列化的榜单数据
    fetched_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("source_id", "board_index", name="uq_ranking_source_board"),
    )
