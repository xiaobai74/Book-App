"""
小说爬虫服务 v4

基于规则驱动的架构，从 JSON 配置文件加载源站规则，
支持 CSS Selector / XPath 选择器、目录翻页、章节内容翻页、
并发抓取、文本过滤与 base64 解码等特性。

规则格式兼容 SoNovel 的 JSON 配置。
"""

import asyncio
import base64
import logging
import random
import re
import ssl
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from rules.rule_engine import RuleEngine, get_rule_engine

logger = logging.getLogger(__name__)

_CURRENT_UA_VERSION = "131"

_USER_AGENTS = [
    f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{_CURRENT_UA_VERSION}.0.0.0 Safari/537.36",
    f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{_CURRENT_UA_VERSION}.0.0.0 Safari/537.36",
    f"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{_CURRENT_UA_VERSION}.0.0.0 Safari/537.36",
    f"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0",
]

# base64 解码器 (兼容 SoNovel 中部分源站的正文加密)
_BASE64_KEY = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="


@dataclass
class CrawledChapter:
    """抓取到的章节"""
    index: int
    title: str
    content: str


@dataclass
class ConnectivityResult:
    """连接预检结果"""
    reachable: bool
    status_code: int | None
    content_length: int
    error_message: str | None
    suggested_fix: str | None


class CrawlerService:
    """小说爬虫引擎 v4 — 规则驱动"""

    def __init__(
        self,
        delay: float = 0.8,
        concurrency: int = 5,
        min_interval: float = 0.2,
        max_interval: float = 0.4,
        max_retries: int = 3,
        retry_min_interval: float = 2.0,
        retry_max_interval: float = 4.0,
        rules_file: str | None = None,
    ):
        self.delay = delay
        self.concurrency = concurrency
        self.min_interval = min_interval
        self.max_interval = max_interval
        self.max_retries = max_retries
        self.retry_min_interval = retry_min_interval
        self.retry_max_interval = retry_max_interval

        self._semaphore = asyncio.Semaphore(concurrency)
        self._cookie_jar: httpx.Cookies | None = None
        self._connectivity_cache: dict[str, ConnectivityResult] = {}

        # SSL 上下文（忽略证书验证）
        # 注意：国内部分小说站证书不规范（自签名/过期/域名不匹配），
        # 因此全局关闭证书校验以保证抓取可用；存在中间人内容投毒风险，
        # 仅建议用于个人阅读场景。
        self._ssl_context = ssl.create_default_context()
        self._ssl_context.check_hostname = False
        self._ssl_context.verify_mode = ssl.CERT_NONE

        # 规则引擎
        self._engine = get_rule_engine(rules_file)

    # ═══════════════════════════════════════════════════════════
    # HTTP 客户端
    # ═══════════════════════════════════════════════════════════

    def _make_client(self, cookies: dict[str, str] | None = None) -> httpx.AsyncClient:
        """创建 HTTP 客户端，配置浏览器指纹 header。"""
        headers = {
            "User-Agent": random.choice(_USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
            "DNT": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "Referer": random.choice([
                "https://www.google.com/",
                "https://www.bing.com/",
                "https://www.baidu.com/",
            ]),
        }

        client_cookies = None
        if cookies:
            client_cookies = httpx.Cookies()
            for k, v in cookies.items():
                client_cookies.set(k, v, domain="")

        return httpx.AsyncClient(
            timeout=httpx.Timeout(45.0, connect=20.0),
            follow_redirects=True,
            max_redirects=5,
            verify=self._ssl_context,
            http2=False,
            headers=headers,
            cookies=client_cookies,
        )

    # ═══════════════════════════════════════════════════════════
    # 连接预检
    # ═══════════════════════════════════════════════════════════

    async def check_connectivity(self, url: str) -> ConnectivityResult:
        """测试源站是否可达。

        策略：先尝试 GET 请求（stream 模式，只读取第一个 chunk），
        因为很多小说网站不支持 HEAD 请求（返回 405/404/403）。
        GET 回退更贴近真实抓取场景，避免误判。
        """
        if url in self._connectivity_cache:
            return self._connectivity_cache[url]

        result = ConnectivityResult(
            reachable=False,
            status_code=None,
            content_length=0,
            error_message=None,
            suggested_fix=None,
        )

        # 先尝试 GET（stream 模式，不消耗大量带宽）
        try:
            async with self._make_client() as client:
                async with client.stream("GET", url, follow_redirects=True) as resp:
                    result.reachable = 200 <= resp.status_code < 500
                    result.status_code = resp.status_code
                    cl = resp.headers.get("content-length", "0")
                    result.content_length = int(cl) if cl.isdigit() else 0
                    if resp.status_code >= 400:
                        result.error_message = f"源站返回 HTTP {resp.status_code}"
                        result.suggested_fix = "该页面可能不存在或已被移除，请检查 URL 是否正确"
                    # 读取第一个 chunk 以确认连接正常
                    try:
                        async for _ in resp.aiter_bytes(1):
                            break
                    except Exception:
                        pass
        except httpx.ConnectTimeout:
            result.error_message = "连接源站超时，服务器可能不可达或被防火墙拦截"
            result.suggested_fix = "请检查 source_url 是否正确，或尝试更换其他源站"
        except httpx.ReadTimeout:
            result.error_message = "读取源站超时，服务器响应过慢"
            result.suggested_fix = "请稍后重试，或检查网络是否正常"
        except httpx.ConnectError as e:
            result.error_message = f"无法连接到源站: {e}"
            result.suggested_fix = "请确认是否能够访问该网址（可在浏览器中打开测试），或尝试其他源站"
        except Exception as e:
            result.error_message = f"网络连接异常: {e}"
            result.suggested_fix = "请检查网络连接，或稍后重试"

        self._connectivity_cache[url] = result
        return result

    # ═══════════════════════════════════════════════════════════
    # HTTP 请求
    # ═══════════════════════════════════════════════════════════

    async def _get(
        self,
        client: httpx.AsyncClient,
        url: str,
        retries: int | None = None,
    ) -> str:
        """带指数退避重试的 GET 请求。"""
        retries = retries if retries is not None else self.max_retries
        last_err = None

        for attempt in range(retries):
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                if resp.cookies:
                    self._cookie_jar = resp.cookies
                # 先通过原始字节检测编码，再设置 encoding
                # httpx 的 charset_encoding 可能为空字符串或 None
                # 在访问 .text 之前设置 encoding 避免 httpx 锁定错误编码
                if not resp.charset_encoding:
                    detected = self._detect_encoding(resp.content[:4096])
                    if detected:
                        resp.encoding = detected
                return resp.text
            except httpx.HTTPStatusError as e:
                last_err = e
                status = e.response.status_code
                if status in (403, 404, 410):
                    raise RuntimeError(f"源站拒绝访问 (HTTP {status}): {url}")
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as e:
                last_err = e
                if attempt < retries - 1:
                    wait = 2 ** attempt
                    logger.warning(f"GET 请求失败 (尝试 {attempt + 1}/{retries}): {e}，{wait}s 后重试")
                    await asyncio.sleep(wait)
            except Exception as e:
                last_err = e
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)

        raise RuntimeError(f"无法访问 {url}，已重试 {retries} 次: {last_err}")

    @staticmethod
    def _detect_encoding(raw_bytes: bytes) -> str | None:
        """从 HTML meta 标签中检测编码。

        尝试多种常见的中文编码解码头部，从中提取 <meta charset> 声明。
        因为页面可能是 utf-8、gbk、gb2312、big5 等编码，直接用一种编码解码
        可能导致乱码而无法匹配 charset 声明。
        """
        # 优先尝试的编码列表（中文网站常见）
        candidates = ["utf-8", "gbk", "gb2312", "gb18030", "big5", "latin-1"]
        head = raw_bytes[:4096]

        for encoding in candidates:
            try:
                fragment = head.decode(encoding)
                m = re.search(
                    r'<meta[^>]+charset\s*=\s*["\']?\s*([\w-]+)',
                    fragment,
                    re.IGNORECASE,
                )
                if m:
                    detected = m.group(1)
                    # 标准化解码名称 (gb2312 → gbk)
                    if detected.lower() in ("gb2312", "gbk", "gb18030"):
                        return "gbk"
                    return detected
            except (UnicodeDecodeError, LookupError):
                continue

        return None

    # ═══════════════════════════════════════════════════════════
    # 选择器解析
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def _select_one(soup: BeautifulSoup, selector: str):
        """使用 CSS Selector 选取单个元素。

        支持 @attr 后缀提取属性值，例如 "meta[property=\"og:image\"]@content"。

        注意：XPath 选择器已弃用，请使用 CSS Selector。
        BeautifulSoup 的 .select() 仅支持 CSS Selector 语法。
        """
        if not selector:
            return None

        # 解析 @attr 后缀（仅当 @ 后面不是 = 时才是属性提取）
        # 例如 "meta[property=\"og:image\"]@content" 中的 @content
        attr_name = None
        # 查找最后一个 @ 且后面不是 "=" 的情况（排除 CSS 属性选择器中的 =）
        last_at_idx = selector.rfind("@")
        if last_at_idx > 0:
            suffix = selector[last_at_idx + 1:]
            # 确保这不是 CSS 属性选择器的一部分（如 @charset, @media）
            if not suffix.startswith("js:") and "=" not in suffix:
                attr_name = suffix.strip()
                selector = selector[:last_at_idx]

        # XPath 以 // 或 / 开头 — 不支持，建议使用 CSS Selector
        if selector.startswith("//") or selector.startswith("/"):
            logger.warning(f"XPath 选择器不支持，将作为 CSS Selector 处理: {selector[:60]}")

        # CSS Selector
        result = soup.select_one(selector)
        if result and attr_name:
            if attr_name in result.attrs:
                return result.attrs[attr_name]
            return result.get(attr_name, "")
        return result

    @staticmethod
    def _select_all(soup: BeautifulSoup, selector: str) -> list:
        """使用 CSS Selector 选取所有匹配元素。

        支持 @attr 后缀提取属性值。
        """
        if not selector:
            return []

        attr_name = None
        # 使用与 _select_one 一致的逻辑：查找最后一个 @ 且不是 CSS 属性选择器
        last_at_idx = selector.rfind("@")
        if last_at_idx > 0:
            suffix = selector[last_at_idx + 1:]
            if not suffix.startswith("js:") and "=" not in suffix:
                attr_name = suffix.strip()
                selector = selector[:last_at_idx]

        # XPath 以 // 或 / 开头 — 不支持，建议使用 CSS Selector
        if selector.startswith("//") or selector.startswith("/"):
            logger.warning(f"XPath 选择器不支持，将作为 CSS Selector 处理: {selector[:60]}")

        results = soup.select(selector)
        if attr_name and results:
            return [r.get(attr_name, "") for r in results]
        return results

    # ═══════════════════════════════════════════════════════════
    # 章节列表解析
    # ═══════════════════════════════════════════════════════════

    def _parse_chapter_list(
        self,
        html: str,
        source_url: str,
        rule: dict,
    ) -> list[tuple[str, str]]:
        """根据规则提取章节列表 [(标题, 完整URL), ...]。"""
        soup = BeautifulSoup(html, "html.parser")
        toc_rule = rule.get("toc", {})
        item_selector = toc_rule.get("item", "")

        if not item_selector:
            # 回退到通用策略
            return self._parse_chapter_list_generic(html, source_url)

        items = self._select_all(soup, item_selector)
        if not items:
            logger.warning(f"选择器 '{item_selector}' 未匹配到任何章节链接")
            return self._parse_chapter_list_generic(html, source_url)

        pairs: list[tuple[str, str]] = []
        seen: set[str] = set()

        # 判断每个 item 是 <a> 还是需要从中查找 <a>
        for item in items:
            if item.name == "a" and item.get("href"):
                title = item.get_text(strip=True)
                href = item.get("href", "").strip()
                if title and href and len(title) >= 2:
                    key = title.strip()
                    if key not in seen:
                        seen.add(key)
                        full_url = urljoin(source_url, href)
                        pairs.append((key, full_url))
            else:
                # 在 item 内部查找 <a>
                for a in item.find_all("a", href=True):
                    title = a.get_text(strip=True)
                    href = a.get("href", "").strip()
                    if title and href and len(title) >= 2:
                        key = title.strip()
                        if key not in seen:
                            seen.add(key)
                            full_url = urljoin(source_url, href)
                            pairs.append((key, full_url))

        # 章节排序（保持卷内顺序，纠正整页倒序）
        return sort_chapter_pairs(pairs)

    def _parse_chapter_list_generic(
        self,
        html: str,
        source_url: str,
    ) -> list[tuple[str, str]]:
        """通用章节列表解析（无规则时回退）。"""
        soup = BeautifulSoup(html, "html.parser")
        pairs: list[tuple[str, str]] = []

        list_selectors = [
            "#list", ".listmain", ".chapterlist", ".chapter-list",
            ".chapterList", "#chapters", ".book-list", ".book_last",
            ".section-list", ".catalog",
        ]
        list_div = None
        for sel in list_selectors:
            list_div = soup.select_one(sel)
            if list_div:
                break

        if list_div:
            for a in list_div.find_all("a", href=True):
                title = a.get_text(strip=True)
                href = a.get("href", "").strip()
                if title and href and len(title) >= 2:
                    pairs.append((title, href))

        if not pairs:
            for dd in soup.select("dl dd a, dl dt a, ul li a"):
                title = dd.get_text(strip=True)
                href = dd.get("href", "").strip()
                if title and href and len(title) >= 2:
                    pairs.append((title, href))

        if not pairs:
            # 按常见的章节 URL 模式匹配，排除导航链接
            # 模式覆盖: /123.html, 123.html, /chapter/xxx, /read/xxx, /book/123.html
            chapter_pattern = re.compile(
                r"(\d+\.html?$|/\d+_\d+/|/chapter/|/read/|/book/\d+\.html)",
                re.I,
            )
            nav_titles = {"下一章", "上一章", "下一页", "上一页", "返回目录", "回目录", "首页", "下一頁", "上一頁"}
            for a in soup.find_all("a", href=True):
                href = a.get("href", "")
                title = a.get_text(strip=True)
                if title and len(title) >= 2 and chapter_pattern.search(href):
                    if title not in nav_titles:
                        pairs.append((title, href))

        seen: set[str] = set()
        result: list[tuple[str, str]] = []
        for title, href in pairs:
            key = title.strip()
            if key in seen:
                continue
            seen.add(key)
            full_url = urljoin(source_url, href)
            result.append((key, full_url))

        result = sort_chapter_pairs(result)
        return result

    async def _fetch_toc_pages(
        self,
        client: httpx.AsyncClient,
        first_page_url: str,
        rule: dict,
        first_html: str,
    ) -> list[tuple[str, str]]:
        """获取目录所有分页的章节链接。"""
        toc_rule = rule.get("toc", {})
        pagination = toc_rule.get("pagination", False)
        if not pagination:
            return self._parse_chapter_list(first_html, first_page_url, rule)

        all_pairs = self._parse_chapter_list(first_html, first_page_url, rule)
        next_selector = toc_rule.get("nextPage", "")
        if not next_selector:
            return all_pairs

        current_url = first_page_url
        visited_urls: set[str] = {current_url}
        page_count = 0
        max_toc_pages = 50  # 安全上限
        html = first_html  # 当前页 HTML（首次由调用方传入）

        while page_count < max_toc_pages:
            soup = BeautifulSoup(html, "html.parser")

            next_el = self._select_one(soup, next_selector)
            if not next_el:
                break

            # <select><option> 的翻页：取 value 属性
            if next_el.name == "select":
                options = next_el.find_all("option")
                next_url = None
                for opt in options:
                    opt_url = urljoin(current_url, opt.get("value", ""))
                    if opt_url not in visited_urls:
                        next_url = opt_url
                        break
                if not next_url:
                    break
            elif next_el.name == "option":
                next_url = urljoin(current_url, next_el.get("value", ""))
                if next_url in visited_urls:
                    break
            else:
                href = next_el.get("href", "")
                if not href:
                    next_url_from_attr = next_el.get("value", "")
                    if not next_url_from_attr:
                        break
                    next_url = urljoin(current_url, next_url_from_attr)
                else:
                    next_url = urljoin(current_url, href)

            if not next_url or next_url in visited_urls:
                break

            visited_urls.add(next_url)
            current_url = next_url
            page_count += 1

            try:
                html = await self._get(client, current_url)
                pairs = self._parse_chapter_list(html, current_url, rule)
                all_pairs.extend(pairs)
                logger.debug(f"目录翻页 {page_count}: 获取 {len(pairs)} 章, URL={current_url}")
            except Exception as e:
                logger.warning(f"目录翻页失败 ({current_url}): {e}")
                break

            await asyncio.sleep(random.uniform(self.min_interval, self.max_interval))

        # 去重排序
        seen: set[str] = set()
        deduped: list[tuple[str, str]] = []
        for title, url in all_pairs:
            key = title.strip()
            if key not in seen:
                seen.add(key)
                deduped.append((key, url))
        deduped = sort_chapter_pairs(deduped)

        return deduped

    # ═══════════════════════════════════════════════════════════
    # 章节正文提取
    # ═══════════════════════════════════════════════════════════

    def _parse_chapter_content(self, html: str, rule: dict) -> str:
        """根据规则提取章节正文。"""
        chapter_rule = rule.get("chapter", {})
        content_selector = chapter_rule.get("content", "")
        title_selector = chapter_rule.get("title", "")
        filter_tag = chapter_rule.get("filterTag", "")
        filter_element = chapter_rule.get("filterElement", "")
        filter_txt = chapter_rule.get("filterTxt", "")

        soup = BeautifulSoup(html, "html.parser")

        # ── 默认清理 script/style 等（全局安全清理）──────────
        for tag in soup(["script", "style", "ins", "noscript", "iframe", "form"]):
            tag.decompose()

        # ── 删除推广元素（filterElement: 整块删除，含内部文字）──
        # 用于清理正文前后的站内推广块，例如:
        #   <div id="content_tip"><b>最新网址：...</b></div>
        #   <p><a href="...">亲,点击进去,给个好评呗...</a>...</p>
        # 语义与 filterTag 不同: filterTag 只去掉标签壳保留文字，
        # filterElement 则彻底移除元素及其内部文字。
        if filter_element:
            for selector in filter_element.split(","):
                selector = selector.strip()
                if not selector:
                    continue
                try:
                    for el in soup.select(selector):
                        el.decompose()
                except Exception as e:
                    logger.warning(f"filterElement 选择器无效: {selector} ({e})")

        # ── 提取章节标题 ──────────────────────────
        chapter_title = ""
        if title_selector:
            title_el = self._select_one(soup, title_selector)
            if title_el:
                chapter_title = title_el.get_text(strip=True)
                chapter_title = re.sub(r"\(\d+/\d+\)", "", chapter_title).strip()

        # ── 提取正文内容 ──────────────────────────
        content_text = ""
        if content_selector:
            content_el = self._select_one(soup, content_selector)
            if content_el:
                # ★ 关键: filterTag 的语义是"去掉这些标签壳，保留内部文字"
                # SoNovel 用 filterTag 来剔除 HTML 标签（只删标签，不删内容）
                # 所以要用 unwrap() 而不是 decompose()
                # 注意: filterTag 支持两种格式:
                #   1) 纯标签名，如 "div, p, script" → 用 .select() 匹配
                #   2) CSS 选择器，如 ".bottem2, hr"  → 也用 .select() 匹配
                if filter_tag:
                    for token in filter_tag.split(","):
                        token = token.strip()
                        if not token:
                            continue
                        for el in content_el.select(token):
                            el.unwrap()  # 去掉标签，保留文字

                if chapter_rule.get("base64Decode"):
                    raw = content_el.get_text("", strip=False)
                    content_text = self._decode_base64_content(raw)
                else:
                    content_text = self._extract_text(content_el, chapter_rule)
        else:
            # 回退到通用提取
            content_text = self._extract_text_generic(soup)

        # ── 过滤广告文本 ───────────────────────────
        if filter_txt:
            for pat in filter_txt.split("|"):
                pat = pat.strip()
                if pat:
                    try:
                        content_text = re.sub(pat, "", content_text, flags=re.I)
                    except re.error:
                        logger.warning(f"无效的正则表达式: {pat}")

        # ── 清理多余空行 ──────────────────────────
        content_text = re.sub(r"\n{3,}", "\n\n", content_text)
        content_text = re.sub(r"[ \t]{2,}", " ", content_text)

        return content_text.strip()

    @staticmethod
    def _extract_text(element, chapter_rule: dict) -> str:
        """根据规则从元素中提取文本。"""
        paragraph_tag_closed = chapter_rule.get("paragraphTagClosed", True)
        paragraph_tag = chapter_rule.get("paragraphTag", "")

        if paragraph_tag_closed:
            # <p>段落</p> 格式：用 get_text 提取，保留段落布局
            return element.get_text("\n", strip=True)
        else:
            # <br> 分隔格式：先用 \n 分隔，再清理
            if paragraph_tag == "<br>+":
                # 把 <br> 替换为换行符
                raw = str(element)
                raw = re.sub(r"<br\s*/?>", "\n", raw, flags=re.I)
                # 去掉剩余的 HTML 标签
                raw = re.sub(r"<[^>]+>", "", raw)
                return raw.strip()
            else:
                return element.get_text("\n", strip=True)

    @staticmethod
    def _extract_text_generic(soup: BeautifulSoup) -> str:
        """通用正文提取（无规则时回退）。"""
        content_selectors = [
            "#content", "#chaptercontent", "#TextContent",
            "#htmlContent", "div.content", "div.showtxt",
            ".chapter-content", ".read-content", "div#contents",
            "div.readcontent", "article", ".post-content",
            "#BookText", ".txt", ".novel-content",
        ]
        for sel in content_selectors:
            el = soup.select_one(sel)
            if el:
                return el.get_text("\n", strip=True)

        body = soup.find("body")
        if body:
            return body.get_text("\n", strip=True)
        return soup.get_text("\n", strip=True)

    def _decode_base64_content(self, raw_text: str) -> str:
        """解码 base64 编码的正文内容。

        部分源站（如燃文小说网）使用 qsbs.bb() 对正文进行 base64 编码。
        正则匹配 document.writeln(qsbs.bb('...')) 并解码。
        """
        decoded = raw_text

        # 匹配 qsbs.bb('...') 模式
        def _decode_match(m: re.Match) -> str:
            encoded = m.group(1)
            try:
                # 清理非 base64 字符
                clean = re.sub(r"[^A-Za-z0-9+/=]", "", encoded)
                raw_bytes = base64.b64decode(clean)
                return raw_bytes.decode("utf-8", errors="replace")
            except Exception:
                return m.group(0)

        decoded = re.sub(
            r"document\.writeln\(qsbs\.bb\('([^']+)'\)\);",
            _decode_match,
            decoded,
        )

        # 也尝试匹配其他变体
        def _try_decode_all(encoded_str: str) -> str:
            """尝试解码整个字符串中可能的 base64 片段。"""
            clean = re.sub(r"[^A-Za-z0-9+/=]", "", encoded_str)
            if len(clean) < 20:
                return encoded_str
            try:
                raw_bytes = base64.b64decode(clean)
                result = raw_bytes.decode("utf-8", errors="replace")
                # 验证解码结果看起来像中文文本
                chinese_chars = sum(1 for c in result if '一' <= c <= '鿿')
                if chinese_chars > len(result) * 0.1:
                    return result
            except Exception:
                pass
            return encoded_str

        # 如果主要解码方式没有匹配到，尝试全文解码
        if decoded == raw_text and len(raw_text) > 50:
            decoded = _try_decode_all(raw_text)

        return decoded

    # ═══════════════════════════════════════════════════════════
    # 章节翻页
    # ═══════════════════════════════════════════════════════════

    async def _crawl_chapter_with_pagination(
        self,
        client: httpx.AsyncClient,
        chapter_url: str,
        rule: dict,
    ) -> str:
        """抓取可能跨多页的单个章节。"""
        chapter_rule = rule.get("chapter", {})
        pagination = chapter_rule.get("pagination", False)
        next_selector = chapter_rule.get("nextPage", "")

        html = await self._get(client, chapter_url)
        content = self._parse_chapter_content(html, rule)

        if not pagination or not next_selector:
            return content

        # 翻页拼接
        current_url = chapter_url
        visited_urls: set[str] = {current_url}
        max_pages = 20  # 安全上限
        page_count = 0
        all_contents = [content]

        while page_count < max_pages:
            soup = BeautifulSoup(html, "html.parser")

            next_el = self._select_one(soup, next_selector)
            if not next_el:
                break

            href = next_el.get("href", "")
            next_url = urljoin(current_url, href) if href else None
            if not next_url or next_url in visited_urls:
                break

            visited_urls.add(next_url)
            current_url = next_url
            page_count += 1

            try:
                html = await self._get(client, current_url)
                # 翻页时只提取正文，不提取标题
                page_content = self._parse_chapter_content(html, rule)
                all_contents.append(page_content)
                logger.debug(f"章节翻页 {page_count}: {current_url}")
            except Exception as e:
                logger.warning(f"章节翻页失败 ({current_url}): {e}")
                break

            await asyncio.sleep(random.uniform(self.min_interval, self.max_interval))

        return "\n\n".join(all_contents)

    # ═══════════════════════════════════════════════════════════
    # 公共 API
    # ═══════════════════════════════════════════════════════════

    async def get_chapter_list(
        self,
        source_url: str,
        rule: dict | None = None,
    ) -> list[tuple[str, str]]:
        """获取章节列表，返回 [(标题, URL), ...]，按章节序升序。"""
        if rule is None:
            rule = self._engine.match_rule(source_url)
        if rule is None:
            # 回退到通用规则
            logger.info(f"get_chapter_list: 未匹配预配置规则，使用通用规则")
            rule = self._engine._build_generic_rule(source_url)

        cookies_raw = (rule.get("search") or {}).get("cookies", "")
        cookies = self._parse_cookies(cookies_raw) if cookies_raw else None

        async with self._make_client(cookies=cookies) as client:
            # 获取第一章页（可能需要拼接 TOC URL）
            toc_url = self._resolve_toc_url(source_url, rule)

            try:
                html = await self._get(client, toc_url)
            except RuntimeError:
                # TOC URL 解析后的 URL 返回了 404，回退到原始 source_url
                if toc_url != source_url:
                    logger.info(f"TOC URL {toc_url} 不可达，回退到原始 source_url")
                    toc_url = source_url
                    html = await self._get(client, toc_url)
                else:
                    raise
            chapters = await self._fetch_toc_pages(client, toc_url, rule, html)

            if not chapters:
                raise RuntimeError(
                    f"未能从页面解析到章节链接，请确认 {source_url} 是小说目录页"
                )
            return chapters

    def _resolve_toc_url(self, source_url: str, rule: dict) -> str:
        """解析目录页地址。

        有些源站的目录页 URL 不同于详情页，规则中 toc.url 指定了目录页的 URL 模式。
        例如 book.url 用正则从详情页 URL 提取 ID，toc.url 用 %s 拼接。
        """
        toc_rule = rule.get("toc", {})
        toc_url_template = toc_rule.get("url", "") or toc_rule.get("baseUri", "")

        if not toc_url_template:
            return source_url

        # 如果模板包含 %s，需要从 source_url 中提取 ID
        if "%s" in toc_url_template:
            book_rule = rule.get("book", {})
            book_url_pattern = book_rule.get("url", "")

            book_id = None
            if book_url_pattern:
                m = re.search(book_url_pattern, source_url)
                if m:
                    book_id = m.group(1)

            # 尝试从 URL 路径的最后一段提取（仅当正则未匹配到时）
            if not book_id:
                path_parts = urlparse(source_url).path.strip("/").split("/")
                if path_parts:
                    book_id = path_parts[-1]
                    # 去掉 .html 后缀
                    book_id = re.sub(r"\.\w+$", "", book_id)

            if book_id:
                return toc_url_template % book_id

        return source_url

    @staticmethod
    def _parse_cookies(cookies_str: str) -> dict[str, str]:
        """解析 cookies 字符串。格式: "k1='v1'; k2='v2'" 或 "k1=v1; k2=v2"。"""
        result: dict[str, str] = {}
        for part in cookies_str.split(";"):
            part = part.strip()
            if not part:
                continue
            if "=" in part:
                k, v = part.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'\"")
                result[k] = v
        return result

    async def crawl_chapter(
        self,
        chapter_url: str,
        rule: dict | None = None,
    ) -> str:
        """抓取单个章节正文。"""
        if rule is None:
            # 没给 rule 就自动匹配
            rule = self._engine.match_rule(chapter_url)
        if rule is None:
            # 回退到通用规则（与 get_chapter_list 保持一致）
            logger.info(f"crawl_chapter: 未匹配到预配置规则，使用通用规则")
            rule = self._engine._build_generic_rule(chapter_url)

        async with self._make_client() as client:
            return await self._crawl_chapter_with_pagination(client, chapter_url, rule)

    async def crawl_book(
        self,
        source_url: str,
        progress_callback=None,
        max_chapters: int = 5000,
        rule: dict | None = None,
    ) -> list[CrawledChapter]:
        """完整抓取一本书。

        Args:
            source_url: 书籍目录页/详情页 URL
            progress_callback: 进度回调 (current, total)
            max_chapters: 安全上限
            rule: 可选的源站规则，不传则自动匹配

        Returns:
            章节列表（按序号排列）

        Raises:
            RuntimeError: 连接失败、解析失败等
        """
        # Step 0: 匹配规则
        if rule is None:
            rule = self._engine.match_rule(source_url)
        if rule is None:
            # 回退到通用规则（适用于任意小说网站）
            logger.info(f"未匹配到预配置规则，使用通用规则: {source_url}")
            rule = self._engine._build_generic_rule(source_url)
        source_name = rule.get("name", "未知源站")
        is_generic = rule.get("generic", False)
        if is_generic:
            logger.info(f"使用通用规则: {source_name}")
        else:
            logger.info(f"使用规则: {source_name}")

        # Step 1: 连接预检
        logger.info(f"正在检查源站连通性: {source_url}")
        connectivity = await self.check_connectivity(source_url)
        if not connectivity.reachable:
            msg = f"源站不可达: {connectivity.error_message}"
            if connectivity.suggested_fix:
                msg += f"\n💡 {connectivity.suggested_fix}"
            raise RuntimeError(msg)
        if connectivity.status_code and connectivity.status_code >= 400:
            msg = f"源站返回错误 (HTTP {connectivity.status_code})"
            if connectivity.suggested_fix:
                msg += f"\n💡 {connectivity.suggested_fix}"
            raise RuntimeError(msg)
        logger.info(f"源站连通性检查通过 (HTTP {connectivity.status_code})")

        # Step 2: 获取所有章节链接
        logger.info(f"正在获取章节列表: {source_url}")
        chapter_links = await self.get_chapter_list(source_url, rule)
        total = min(len(chapter_links), max_chapters)
        if total == 0:
            raise RuntimeError("未找到任何章节链接，请检查源站 URL 是否为书籍目录页")
        logger.info(f"章节列表: {total}/{len(chapter_links)} 章（上限 {max_chapters}）")

        # Step 3: 并发抓取正文
        chapter_links = chapter_links[:total]

        # 源站可覆盖全局并发/间隔配置
        crawl_rule = rule.get("crawl", {})
        concurrency = crawl_rule.get("concurrency", 0) or self.concurrency
        min_int = crawl_rule.get("minInterval", 0) or self.min_interval
        max_int = crawl_rule.get("maxInterval", 0) or self.max_interval
        retry_max = crawl_rule.get("maxAttempts", 0) or self.max_retries
        retry_min = crawl_rule.get("retryMinInterval", 0) or self.retry_min_interval
        retry_max_interval = crawl_rule.get("retryMaxInterval", 0) or self.retry_max_interval

        semaphore = asyncio.Semaphore(concurrency)

        results: list[CrawledChapter] = []
        failed_count = 0
        completed_count = 0
        lock = asyncio.Lock()

        async def _fetch_one(i: int, title: str, url: str) -> CrawledChapter:
            nonlocal completed_count, failed_count

            async with semaphore:
                # 随机延迟
                await asyncio.sleep(random.uniform(min_int, max_int))

                for retry in range(retry_max):
                    try:
                        async with self._make_client() as client:
                            content = await self._crawl_chapter_with_pagination(
                                client, url, rule,
                            )
                        break
                    except Exception as e:
                        if retry < retry_max - 1:
                            wait = random.uniform(retry_min, retry_max_interval)
                            logger.warning(
                                f"章节 [{i}/{total}] 「{title}」失败 (重试 {retry + 1}/{retry_max}): {e}"
                            )
                            await asyncio.sleep(wait)
                        else:
                            logger.error(f"章节 [{i}/{total}] 「{title}」最终失败: {e}")
                            content = f"[本章抓取失败: {e}]"

                async with lock:
                    nonlocal completed_count
                    completed_count += 1
                    if len(content) < 100 and "[本章抓取失败" not in content:
                        logger.warning(
                            f"章节 [{i}/{total}] 「{title}」内容较短 ({len(content)} 字)"
                        )
                    if "[本章抓取失败" in content:
                        nonlocal failed_count
                        failed_count += 1
                    if progress_callback:
                        progress_callback(completed_count, total)

                return CrawledChapter(index=i, title=title, content=content)

        # 并发执行所有章节抓取
        tasks = [
            _fetch_one(i, title, url)
            for i, (title, url) in enumerate(chapter_links, 1)
        ]
        results = await asyncio.gather(*tasks)

        # 按原始索引排序
        results.sort(key=lambda c: c.index)

        logger.info(
            f"抓取完成: {len(results)}/{total} 章 "
            f"(成功 {len(results) - failed_count}, 失败 {failed_count})"
        )
        return results

    # ═══════════════════════════════════════════════════════════
    # 源站查询
    # ═══════════════════════════════════════════════════════════

    def list_sources(self) -> list[dict]:
        """获取所有可用源站列表。"""
        return self._engine.list_sources()

    def match_source_for_url(self, url: str) -> dict | None:
        """为给定 URL 匹配源站规则。"""
        return self._engine.match_rule(url)


# ═══════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════

_CN_NUM = {
    "零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
}

# 可出现在章节序号中的中文数字字符（含位权字符 十/百/千）
_CN_CHAPTER_NUM_RE = r"[0-9零一二三四五六七八九十百千两]+"


def _cn_to_int(cn: str) -> int | None:
    """中文数字转阿拉伯数字。

    例如 '十一' → 11，'一百二十' → 120，'29' → 29。
    无法转换（含不支持字符）时返回 None。
    """
    if not cn:
        return None
    if cn.isdigit():
        return int(cn)
    if any(ch not in _CN_NUM and ch not in "十百千" for ch in cn):
        return None
    total = 0
    section = 0
    for ch in cn:
        if ch in _CN_NUM:
            section = _CN_NUM[ch]
        elif ch == "十":
            total += (section or 1) * 10
            section = 0
        elif ch == "百":
            total += (section or 1) * 100
            section = 0
        elif ch == "千":
            total += (section or 1) * 1000
            section = 0
    return total + section


def _chapter_sort_key(title: str) -> tuple:
    """从章节标题中提取排序键（支持阿拉伯数字与中文数字）。"""
    # "第29卷 第18章" / "第二十九卷 第十八章" → (29, 18)
    m = re.search(
        rf"第\s*({_CN_CHAPTER_NUM_RE})\s*[卷]\s*(?:第\s*({_CN_CHAPTER_NUM_RE})\s*[章节回])?",
        title,
    )
    if m:
        vol = _cn_to_int(m.group(1))
        if vol is not None:
            ch = _cn_to_int(m.group(2)) if m.group(2) else 0
            return (0, vol, ch)

    # "第11章 xxx" / "第十一章 xxx" → num
    m = re.search(rf"第\s*({_CN_CHAPTER_NUM_RE})\s*[章节回]", title)
    if m:
        num = _cn_to_int(m.group(1))
        if num is not None:
            return (0, num, 0)

    # "29. 标题" 或 "29、标题" 开头
    m = re.search(r"^\s*(\d+)\s*[\.、\s]", title)
    if m:
        return (1, int(m.group(1)), 0)

    # 纯数字索引
    m = re.search(r"^\s*(\d+)\s*$", title)
    if m:
        return (2, int(m.group(1)), 0)

    # 包含数字
    m = re.search(r"(\d+)", title)
    if m:
        return (3, int(m.group(1)), 0)

    return (4, 0, 0)


# 卷标题（如「第三卷」「第五卷 沧海」）— 其后不再紧跟「第」字
# （「第5卷 第1章」这类卷-章组合不是卷标题）
_VOLUME_HEADER_RE = re.compile(rf"^\s*第\s*{_CN_CHAPTER_NUM_RE}\s*[卷集部](?!\s*第)")


def _chapter_cmp_value(key: tuple) -> tuple | None:
    """提取可用于顺序比较的数值（无可靠数值时返回 None）。

    类别 0-2 的键携带真实章节序号；类别 3（正文含任意数字，如「番外2024」）
    不可靠，视作无序号，避免误判顺序回落。
    """
    if key[0] == 0:
        return (key[1], key[2])
    if key[0] in (1, 2):
        return (key[1],)
    return None


def sort_chapter_pairs(pairs: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """对章节列表排序：保持卷内顺序，仅纠正目录页整体倒序。

    背景：源站目录页的 DOM 顺序通常就是作者写作顺序，但也存在两类
    需要特殊处理的情况：
    1. 多卷小说每卷都从「第一章」重新计数（如《诛仙》），标题序号会
       周期性回落 — 这时的"回落"是正常的，不应重排；
    2. 个别源站目录按更新时间倒序（最新章在前），整页都是倒序。

    策略：
    - 把列表按「序号回落」切分成若干段（回落点 = 新一卷/新段起点）；
    - 段内保持原始顺序（写作顺序）；
    - 段间按各段最小序号稳定升序排列（可纠正整段倒序，多卷书各卷
      段的最小序号相同，稳定排序保持原有卷序）；
    - 无可排序值的条目（序幕、尾声、卷标题等）不参与回落判断，
      固定在原位置。
    """
    if len(pairs) < 2:
        return list(pairs)

    # 计算每个条目的 (排序键, 比较值, 是否卷标题)
    entries: list[tuple[tuple, tuple | None, bool, str, str]] = []
    for title, url in pairs:
        key = _chapter_sort_key(title)
        entries.append((key, _chapter_cmp_value(key), bool(_VOLUME_HEADER_RE.match(title)), title, url))

    # 按「比较值回落」切分段：两侧都是带序号且非卷标题的条目时，
    # 当前值小于前一个值视为进入新段
    segments: list[list[tuple[tuple, tuple | None, bool, str, str]]] = []
    for e in entries:
        if segments:
            prev = segments[-1][-1]
            prev_val, prev_hdr = prev[1], prev[2]
            curr_val, curr_hdr = e[1], e[2]
            if (
                prev_val is not None and curr_val is not None
                and not prev_hdr and not curr_hdr
                and curr_val < prev_val
            ):
                segments.append([e])
                continue
            segments[-1].append(e)
        else:
            segments.append([e])

    # 段间按段内最小比较值升序（无可比较值的段视为 0，保持相对位置）
    def _segment_min(seg):
        vals = [e[1] for e in seg if e[1] is not None]
        return min(vals) if vals else (0,)

    segments.sort(key=_segment_min)

    return [(e[3], e[4]) for seg in segments for e in seg]


# 全局单例（向后兼容）
crawler = CrawlerService(delay=0.8, concurrency=5)
