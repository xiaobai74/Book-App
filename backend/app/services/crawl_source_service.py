"""
自定义抓取源站服务

提供自定义源站的 CRUD 操作和规则测试功能。
"""

import json
import logging
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crawl_source import CrawlSource
from app.models.user import User
from app.schemas.book import (
    CrawlSourceCreate,
    CrawlSourceResponse,
    CrawlSourceUpdate,
)

logger = logging.getLogger(__name__)


class CrawlSourceService:
    """自定义抓取源站服务"""

    @staticmethod
    async def create(
        db: AsyncSession,
        user: User,
        data: CrawlSourceCreate,
    ) -> CrawlSourceResponse:
        """创建自定义源站规则。

        Args:
            db: 数据库会话
            user: 当前用户
            data: 创建请求

        Returns:
            创建的源站响应
        """
        # 验证 rule_json 是有效 JSON
        try:
            json.loads(data.rule_json)
        except json.JSONDecodeError as e:
            from app.middleware.error_handler import AppException
            raise AppException(
                status_code=400,
                detail=f"rule_json 不是有效的 JSON 格式: {e}",
            )

        source = CrawlSource(
            user_id=user.id,
            name=data.name,
            url=data.url,
            rule_json=data.rule_json,
            is_public=False,  # 默认仅自己可见
        )
        db.add(source)
        await db.flush()
        await db.refresh(source)

        logger.info(f"用户 {user.id} 创建了自定义源站: {source.name}")
        return _source_to_response(source)

    @staticmethod
    async def list_sources(
        db: AsyncSession,
        user: User,
    ) -> list[CrawlSourceResponse]:
        """列出当前用户的所有自定义源站。

        Args:
            db: 数据库会话
            user: 当前用户

        Returns:
            自定义源站列表
        """
        result = await db.execute(
            select(CrawlSource)
            .where(CrawlSource.user_id == user.id)
            .order_by(CrawlSource.created_at.desc())
        )
        sources = list(result.scalars().all())
        return [_source_to_response(s) for s in sources]

    @staticmethod
    async def get(
        db: AsyncSession,
        user: User,
        source_id: int,
    ) -> CrawlSourceResponse:
        """获取单个自定义源站详情。

        Args:
            db: 数据库会话
            user: 当前用户
            source_id: 源站 ID

        Returns:
            源站响应
        """
        result = await db.execute(
            select(CrawlSource).where(
                CrawlSource.id == source_id,
                CrawlSource.user_id == user.id,
            )
        )
        source = result.scalar_one_or_none()
        if source is None:
            from app.middleware.error_handler import AppException
            raise AppException(status_code=404, detail="自定义源站不存在")
        return _source_to_response(source)

    @staticmethod
    async def update(
        db: AsyncSession,
        user: User,
        source_id: int,
        data: CrawlSourceUpdate,
    ) -> CrawlSourceResponse:
        """更新自定义源站规则。

        Args:
            db: 数据库会话
            user: 当前用户
            source_id: 源站 ID
            data: 更新请求

        Returns:
            更新后的源站响应
        """
        result = await db.execute(
            select(CrawlSource).where(
                CrawlSource.id == source_id,
                CrawlSource.user_id == user.id,
            )
        )
        source = result.scalar_one_or_none()
        if source is None:
            from app.middleware.error_handler import AppException
            raise AppException(status_code=404, detail="自定义源站不存在")

        if data.name is not None:
            source.name = data.name
        if data.url is not None:
            source.url = data.url
        if data.rule_json is not None:
            try:
                json.loads(data.rule_json)
            except json.JSONDecodeError as e:
                from app.middleware.error_handler import AppException
                raise AppException(
                    status_code=400,
                    detail=f"rule_json 不是有效的 JSON 格式: {e}",
                )
            source.rule_json = data.rule_json
        if data.is_public is not None:
            source.is_public = data.is_public

        source.updated_at = datetime.now(UTC).replace(tzinfo=None)
        await db.flush()
        await db.refresh(source)

        logger.info(f"用户 {user.id} 更新了自定义源站: {source.name}")
        return _source_to_response(source)

    @staticmethod
    async def delete(
        db: AsyncSession,
        user: User,
        source_id: int,
    ) -> bool:
        """删除自定义源站。

        Args:
            db: 数据库会话
            user: 当前用户
            source_id: 源站 ID

        Returns:
            是否成功
        """
        result = await db.execute(
            select(CrawlSource).where(
                CrawlSource.id == source_id,
                CrawlSource.user_id == user.id,
            )
        )
        source = result.scalar_one_or_none()
        if source is None:
            from app.middleware.error_handler import AppException
            raise AppException(status_code=404, detail="自定义源站不存在")

        await db.delete(source)
        await db.flush()
        logger.info(f"用户 {user.id} 删除了自定义源站: {source.name}")
        return True

    @staticmethod
    async def test_rule(
        url: str,
        rule_json: str,
    ) -> dict:
        """测试自定义规则是否有效。

        使用给定的规则尝试解析指定 URL 的章节列表，
        返回前几条章节标题作为验证。

        Args:
            url: 小说目录页 URL
            rule_json: JSON 格式的抓取规则

        Returns:
            {"success": bool, "chapter_count": int, "sample_chapters": [...], "error": str|None}
        """
        try:
            rule = json.loads(rule_json)
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "chapter_count": 0,
                "sample_chapters": [],
                "error": f"rule_json 不是有效的 JSON 格式: {e}",
            }

        from app.services.crawler_service import crawler

        try:
            chapters = await crawler.get_chapter_list(url, rule)
            sample = [
                {"title": title, "url": ch_url}
                for title, ch_url in chapters[:5]
            ]
            return {
                "success": True,
                "chapter_count": len(chapters),
                "sample_chapters": sample,
                "error": None,
            }
        except Exception as e:
            return {
                "success": False,
                "chapter_count": 0,
                "sample_chapters": [],
                "error": str(e),
            }


def _source_to_response(source: CrawlSource) -> CrawlSourceResponse:
    """将 ORM 模型转为响应 Schema"""
    return CrawlSourceResponse(
        id=source.id,
        name=source.name,
        url=source.url,
        rule_json=source.rule_json,
        is_public=source.is_public,
        created_at=source.created_at,
    )
