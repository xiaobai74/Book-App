"""
源站排行榜抓取服务

复用规则引擎的 ranking.boards 配置，CSS Selector 解析榜单页面。
带内存缓存（TTL 15 分钟），避免频繁请求源站被封。
编码处理与 SearchService._decode_response 一致（兼容 GBK 页面）。
"""

import asyncio
import logging
import re
import ssl
import time
from dataclasses import dataclass, field
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from rules.rule_engine import get_rule_engine

logger = logging.getLogger(__name__)

_CACHE_TTL = 15 * 60  # 秒

# 单页解析上限与多页合并后的总条目上限（避免过度请求源站）
_PER_PAGE_CAP = 100
_MAX_TOTAL_ITEMS = 300

# 榜单页表头/占位链接（无有效详情页的条目将被过滤）
_PLACEHOLDER_HREFS = {"", "#", "####", "javascript:;", "javascript:void(0)"}

# 详情页补全：榜单页本身不含作者等字段时（如香书小说/阅读库），
# 对缺失作者的前 N 条并发抓取详情页补全字段
_DETAIL_ENRICH_CAP = 30
_DETAIL_CONCURRENCY = 4

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


@dataclass
class RankingItem:
    """榜单条目"""
    rank: int
    title: str
    author: str = "未知"
    book_url: str = ""          # 详情页 URL（可直接走现有导入流程）
    category: str = ""
    latest_chapter: str = ""
    last_update: str = ""


@dataclass
class BoardResult:
    """单个榜单的抓取结果"""
    source_id: int
    source_name: str
    board_index: int
    board_name: str
    items: list[RankingItem] = field(default_factory=list)
    from_cache: bool = False


class RankingService:
    """源站排行榜抓取"""

    def __init__(self, rules_file: str | None = None):
        self._engine = get_rule_engine(rules_file)
        self._ssl_context = ssl.create_default_context()
        self._ssl_context.check_hostname = False
        self._ssl_context.verify_mode = ssl.CERT_NONE
        # 缓存: {(source_id, board_index): (timestamp, BoardResult)}
        self._cache: dict[tuple[int, int], tuple[float, BoardResult]] = {}

    def list_ranking_sources(self) -> list[dict]:
        return self._engine.list_ranking_sources()

    async def fetch_board(self, source_id: int, board_index: int, force: bool = False) -> BoardResult:
        """抓取指定源站的指定榜单（带缓存）。

        force=True 时跳过缓存强制重新抓取（用户点击刷新时传入）。
        """
        cache_key = (source_id, board_index)
        cached = self._cache.get(cache_key)
        if not force and cached and time.monotonic() - cached[0] < _CACHE_TTL:
            result = cached[1]
            result.from_cache = True
            return result

        rule = self._engine.get_rule_by_id(source_id)
        if rule is None:
            raise ValueError("源站不存在")
        boards = (rule.get("ranking") or {}).get("boards") or []
        if board_index < 0 or board_index >= len(boards):
            raise ValueError("榜单不存在")

        board = boards[board_index]

        # 支持分页：board.pageUrl 为含 {page} 的模板（page>=2 生效），
        # page 1 始终取 board.url；maxPages 控制抓取页数（默认 1）。
        max_pages = int(board.get("maxPages", 1) or 1)
        page_url_tpl = board.get("pageUrl", "") or ""
        if not page_url_tpl:
            max_pages = 1

        items: list[RankingItem] = []
        seen: set[str] = set()
        for page in range(1, max_pages + 1):
            url = board["url"] if page == 1 else page_url_tpl.replace("{page}", str(page))
            try:
                html = await self._fetch(url)
            except Exception:
                if page == 1:
                    raise
                logger.warning("榜单第 %s 页抓取失败，保留已有结果: %s", page, url)
                break
            page_items = self._parse_board(html, board, base_url=url)
            if page == 1 and not page_items:
                raise RuntimeError(
                    "榜单解析结果为空，源站页面可能已改版，请更新 ranking 规则选择器"
                )
            if not page_items:
                break
            added = 0
            for it in page_items:
                key = it.book_url or it.title
                if key in seen:
                    continue
                seen.add(key)
                it.rank = len(items) + 1
                items.append(it)
                added += 1
            # 本页无新增（多为分页失效/内容重复），停止翻页
            if added == 0:
                break
            if len(items) >= _MAX_TOTAL_ITEMS:
                break

        if not items:
            raise RuntimeError(
                "榜单解析结果为空，源站页面可能已改版，请更新 ranking 规则选择器"
            )

        # 榜单页缺作者等字段时，抓取详情页补全（board.detailFetch 配置）
        await self._enrich_from_detail(items, board)

        result = BoardResult(
            source_id=source_id,
            source_name=rule.get("name", "未知"),
            board_index=board_index,
            board_name=board.get("name", "榜单"),
            items=items,
        )
        self._cache[cache_key] = (time.monotonic(), result)
        return result

    async def _fetch(self, url: str, retries: int = 2) -> str:
        """GET 榜单页面（带重试 + 编码检测）。"""
        headers = {
            "User-Agent": _UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        last_err: Exception | None = None
        for _ in range(retries):
            try:
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(30.0, connect=15.0),
                    follow_redirects=True,
                    verify=self._ssl_context,
                    headers=headers,
                ) as client:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    return self._decode_response(resp)
            except Exception as e:
                last_err = e
                logger.warning("排行榜页面请求失败 [%s]: %s", url, e)
        raise RuntimeError(f"榜单页面请求失败: {last_err}")

    @staticmethod
    def _decode_response(resp: httpx.Response) -> str:
        """安全解码 HTML：优先服务器 charset，其次 <meta> 声明，回退 utf-8。
        （同 SearchService._decode_response；部分小说站为 GBK 编码）"""
        encoding = resp.charset_encoding
        if not encoding:
            head = resp.content[:4096].decode("ascii", errors="ignore").lower()
            m = re.search(r'charset=["\']?([\w-]+)', head)
            encoding = m.group(1) if m else None
        resp.encoding = encoding or "utf-8"
        return resp.text

    def _parse_board(
        self, html: str, board: dict, base_url: str
    ) -> list[RankingItem]:
        """按规则选择器解析榜单条目（单页上限 _PER_PAGE_CAP）。

        过滤规则：无书名、或详情页链接为空/占位的条目（如表头行）直接丢弃，
        保证返回的条目都可直接"加入书架"。
        """
        soup = BeautifulSoup(html, "html.parser")
        items: list[RankingItem] = []

        for node in soup.select(board.get("item", ""))[:_PER_PAGE_CAP]:
            title = self._text(node, board.get("bookName", ""))
            if not title:
                continue
            if title in ("更多", "查看更多", "MORE"):
                continue  # 榜单尾部的「更多」导航链接，非书籍条目
            href = (self._attr(node, board.get("bookUrl", ""), "href") or "").strip()
            if href in _PLACEHOLDER_HREFS:
                continue  # 表头行/榜单切换 Tab 等无详情页链接的条目
            items.append(RankingItem(
                rank=len(items) + 1,
                title=title,
                author=self._text(node, board.get("author", "")) or "未知",
                book_url=urljoin(base_url, href),
                category=self._clean_brackets(self._text(node, board.get("category", ""))),
                latest_chapter=self._text(node, board.get("latestChapter", "")),
                last_update=self._text(node, board.get("lastUpdateTime", "")),
            ))
        return items

    # ── 详情页字段补全 ──────────────────────────────

    async def _enrich_from_detail(self, items: list[RankingItem], board: dict) -> None:
        """榜单页缺少作者等字段时，并发抓取详情页补全。

        取值优先级：board.detailFetch 中的 CSS 选择器 → og:novel:* meta 标签
        → h1 文本中的「作\u3000者：」/「更新时间：」正则。补全失败不影响整体结果。
        """
        detail_cfg = board.get("detailFetch") or {}
        targets = [it for it in items if not it.author or it.author == "未知"]
        if not targets:
            return

        sem = asyncio.Semaphore(_DETAIL_CONCURRENCY)

        async def enrich_one(it: RankingItem) -> None:
            async with sem:
                try:
                    html = await self._fetch(it.book_url)
                except Exception:
                    logger.warning("详情页补全请求失败: %s", it.book_url)
                    return
                self._apply_detail_fields(it, html, detail_cfg)

        await asyncio.gather(*(enrich_one(it) for it in targets[:_DETAIL_ENRICH_CAP]))

    def _apply_detail_fields(
        self, item: RankingItem, html: str, detail_cfg: dict
    ) -> None:
        """从详情页 HTML 提取作者/分类/更新时间并回填条目。"""
        soup = BeautifulSoup(html, "html.parser")

        def meta(prop: str) -> str:
            el = soup.select_one(f'meta[property="{prop}"]')
            return (el.get("content") or "").strip() if el else ""

        author = self._text(soup, detail_cfg.get("author", "")) or meta("og:novel:author")
        if not author:
            author = self._regex_from_text(soup, r"作\s*者[：:]\s*([^\s|]+)")
        if author and (not item.author or item.author == "未知"):
            item.author = author

        if not item.category:
            item.category = self._clean_brackets(
                self._text(soup, detail_cfg.get("category", "")) or meta("og:novel:category")
            )

        if not item.last_update:
            upd = self._text(soup, detail_cfg.get("lastUpdateTime", ""))
            if not upd:
                upd = self._regex_from_text(soup, r"(?:更新时间|最后更新)[：:]\s*([0-9]{4}-[0-9]{2}-[0-9]{2}[0-9:]*)")
            item.last_update = upd

    @staticmethod
    def _regex_from_text(soup, pattern: str) -> str:
        """在页面文本中按正则提取字段（如 h1 里的「作者：xx」）。"""
        text = soup.get_text("|", strip=True)
        m = re.search(pattern, text)
        return m.group(1).strip() if m else ""

    @staticmethod
    def _clean_brackets(text: str) -> str:
        """去除分类字段外层的中/英文方括号，如 [玄幻] -> 玄幻。"""
        text = text.strip()
        if len(text) >= 2 and text[0] in "[【" and text[-1] in "]】":
            return text[1:-1].strip()
        return text

    # ── 选择器工具：支持 "selector" 取文本、"selector@attr" 取属性 ──

    @staticmethod
    def _text(node, selector: str) -> str:
        if not selector:
            return ""
        sel = selector.split("@")[0] if "@" in selector else selector
        el = node.select_one(sel) if sel else node
        return el.get_text(strip=True) if el else ""

    @staticmethod
    def _attr(node, selector: str, attr: str) -> str | None:
        if not selector:
            return None
        sel = selector.split("@")[0] if "@" in selector else selector
        el = node.select_one(sel) if sel else node
        return el.get(attr) if el else None


# 全局单例
ranking_service = RankingService()
