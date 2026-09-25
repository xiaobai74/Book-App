"""
源站排行榜路由

GET /api/v1/ranking/sources                       → 支持排行榜的源站列表
GET /api/v1/ranking/{source_id}/boards/{index}    → 抓取指定榜单
"""

import hashlib
import json

from fastapi import APIRouter, Depends, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.books import _etag_matches
from app.database import get_db
from app.middleware.error_handler import AppException
from app.models.user import User
from app.schemas.common import ApiResponse
from app.services.ranking_service import ranking_service
from app.utils.deps import get_current_user

router = APIRouter(prefix="/ranking", tags=["源站排行榜"])


class RankingSourceItem(BaseModel):
    id: int
    name: str
    url: str
    board_names: list[str]
    is_custom: bool


class RankingBookItem(BaseModel):
    rank: int
    title: str
    author: str
    book_url: str
    category: str
    latest_chapter: str
    last_update: str


class BoardResponse(BaseModel):
    source_name: str
    board_name: str
    from_cache: bool
    items: list[RankingBookItem]


@router.get(
    "/sources",
    response_model=ApiResponse[list[RankingSourceItem]],
    summary="支持排行榜的源站列表",
)
async def ranking_sources(_: User = Depends(get_current_user)):
    sources = ranking_service.list_ranking_sources()
    return ApiResponse.ok(data=[RankingSourceItem(**s) for s in sources])


@router.get(
    "/{source_id}/boards/{board_index}",
    response_model=ApiResponse[BoardResponse],
    summary="抓取指定源站的榜单",
)
async def ranking_board(
    source_id: int,
    board_index: int,
    request: Request,
    refresh: bool = Query(False, description="跳过缓存强制重新抓取（用户点击刷新）"),
    limit: int = Query(200, ge=1, le=2000, description="返回条目上限（v2.7 阶段2：完整榜单可达 2000 条，默认截断前 200 条降低传输量）"),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await ranking_service.fetch_board(
            source_id, board_index, force=refresh, db=db
        )
    except ValueError as e:
        raise AppException(status_code=404, detail=str(e))
    except Exception as e:
        raise AppException(status_code=502, detail=f"榜单抓取失败：{e}")

    payload = BoardResponse(
        source_name=result.source_name,
        board_name=result.board_name,
        from_cache=result.from_cache,
        items=[RankingBookItem(**vars(i)) for i in result.items[:limit]],
    )
    # 弱 ETag：只对条目内容取哈希（from_cache 标志随缓存层变化，不应导致 ETag 漂移）
    items_hash = hashlib.md5(
        json.dumps(
            jsonable_encoder(payload.items), ensure_ascii=False, sort_keys=True
        ).encode("utf-8")
    ).hexdigest()[:16]
    etag = f'W/"{items_hash}"'
    cache_headers = {
        "Cache-Control": "private, max-age=300",
        "ETag": etag,
    }
    if _etag_matches(request.headers.get("if-none-match"), etag):
        return Response(status_code=304, headers=cache_headers)

    return JSONResponse(
        content=jsonable_encoder(ApiResponse.ok(data=payload)),
        headers=cache_headers,
    )
