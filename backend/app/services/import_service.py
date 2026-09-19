"""
本地文件导入解析服务

将用户上传的 .txt / .epub / .pdf / .docx 小说文件解析为章节列表，
供 POST /api/v1/books/import 接口写入 chapters 表，并复用
epub_service / txt_service 生成可下载的电子书文件。

设计要点：
- 各格式解析器统一返回 ParsedBook（chapters + 推断的 title/author）。
- 章节切分优先使用「第X章」类标题正则；无标记时按格式各自兜底。
- 元数据为尽力推断，最终由接口层按「表单 > 内嵌 > 文件名」优先级裁决。
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════════════════════

@dataclass
class ParsedChapter:
    """解析出的单个章节"""
    title: str
    content: str


@dataclass
class ParsedBook:
    """文件解析结果"""
    chapters: list[ParsedChapter] = field(default_factory=list)
    title: str | None = None      # 内嵌/文件名推断的书名（可空，由接口层裁决）
    author: str | None = None     # 内嵌/文件名推断的作者（可空）


# ═══════════════════════════════════════════════════════════
# 通用工具
# ═══════════════════════════════════════════════════════════

# 章节标题正则：第X章/回/节/卷/篇/集/部、序章/楔子/番外 等常见标记
_CHAPTER_TITLE_RE = re.compile(
    r"^(?:"
    r"第\s*[0-9零一二三四五六七八九十百千万两]+\s*[章回节卷篇集部]"
    r"|序章|序言|楔子|引子|前言|后记|终章|番外|尾声|结语|完本感言|尾声"
    r"|[Cc]hapter\s+\d+"
    r")"
)

# 标题最大长度（与 DB Chapter.title String(500) 对齐）
_MAX_TITLE_LEN = 500

# TXT 编码候选（utf-8-sig 处理 BOM；gb18030 为 GBK/GB2312 超集；big5 繁体）
_TXT_ENCODINGS = ["utf-8-sig", "utf-8", "gb18030", "big5"]


def _decode_text(raw: bytes) -> str:
    """按候选编码依次尝试解码，全部失败时以 utf-8 忽略错误兜底。"""
    for enc in _TXT_ENCODINGS:
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    logger.warning("TXT 编码嗅探全部失败，使用 utf-8 errors=ignore 兜底")
    return raw.decode("utf-8", errors="ignore")


def _normalize_text(text: str) -> str:
    """统一换行、逐行去首尾空白并丢弃空行，每个非空行视为一个段落。

    epub/txt 生成器按 content.split('\\n') 还原段落，故此处保留单换行分隔。
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ")
    out: list[str] = []
    for ln in text.split("\n"):
        ln = ln.strip()
        if ln:
            out.append(ln)
    return "\n".join(out).strip()


def _first_meta(entries) -> str | None:
    """从 ebooklib get_metadata 返回值中取首个非空字符串。

    ebooklib 将条目存为 (value, others) 元组；不同版本可能存在差异，
    此处对元组/列表/字符串均做防御性处理。
    """
    if not entries:
        return None
    first = entries[0]
    candidates = first if isinstance(first, (tuple, list)) else [first]
    for c in candidates:
        if isinstance(c, str) and c.strip():
            return c.strip()
    return None


def _infer_from_filename(name: str) -> tuple[str, str | None]:
    """从文件名推断书名/作者。

    规则：
    1. 去除扩展名与括号噪音（如 (UUID)、[网站]、【标签】）。
    2. 《书名》作者：X → (书名, X)。
    3. 含分隔符（— － - _）→ 左为书名、右为作者（最常见「书名-作者」约定）。
    4. 其余 → (整体, None)。
    """
    stem = Path(name).stem
    cleaned = re.sub(r"[\(（\[【][^\)）\]】]*[\)）\]】]", "", stem).strip()
    cleaned = cleaned.strip(" -_—–·")
    if not cleaned:
        cleaned = stem.strip()

    # 《书名》作者：X
    m = re.match(r"^《(.+?)》\s*(?:作者\s*[:：])?\s*(.*)$", cleaned)
    if m:
        title = m.group(1).strip()
        author = m.group(2).strip() or None
        return (title[:_MAX_TITLE_LEN], author)

    # 书名-作者（取首个分隔符拆分）
    for sep in ("—", "－", "-", "_"):
        if sep in cleaned:
            left, right = cleaned.split(sep, 1)
            left, right = left.strip(), right.strip()
            if left and right:
                return (left[:_MAX_TITLE_LEN], right[:255])
            break

    return (cleaned[:_MAX_TITLE_LEN], None)


# ═══════════════════════════════════════════════════════════
# 解析服务
# ═══════════════════════════════════════════════════════════

class ImportService:
    """本地小说文件解析器（.txt / .epub / .pdf / .docx）"""

    _PARSERS = {
        ".txt": "_parse_txt",
        ".epub": "_parse_epub",
        ".pdf": "_parse_pdf",
        ".docx": "_parse_docx",
    }

    def parse(
        self,
        filepath: str | Path,
        ext: str,
        source_name: str | None = None,
    ) -> ParsedBook:
        """解析入口：按扩展名分派到对应解析器。

        Args:
            filepath: 实际待解析的文件路径。接口层会先把上传内容写入随机命名的
                临时文件，故 filepath.name 不含用户原始文件名信息。
            ext: 扩展名，决定分派到哪个解析器。
            source_name: 用户原始文件名，专用于「文件名 → 书名/作者」推断；为空时
                退回 filepath.name。上传场景必须传入原始名，否则推断出的书名会被
                随机临时名污染（如 tmpXXXX）。

        Raises:
            ValueError: 不支持的扩展名。
        """
        filepath = Path(filepath)
        ext = ext.lower()
        method_name = self._PARSERS.get(ext)
        if method_name is None:
            raise ValueError(f"不支持的文件格式: {ext}")
        return getattr(self, method_name)(filepath, source_name)

    # ── 章节切分（TXT / PDF 共用） ──────────────────────────

    @staticmethod
    def _is_chapter_title(line: str) -> bool:
        """判断一行是否为章节标题（匹配正则且长度合理）。"""
        s = line.strip()
        if not s or len(s) > 40:  # 标题通常较短，过长视为正文
            return False
        return bool(_CHAPTER_TITLE_RE.match(s))

    def _split_by_markers(self, text: str) -> list[ParsedChapter]:
        """按章节标题正则切分；标题前的内容（封面页等）忽略。"""
        chapters: list[ParsedChapter] = []
        cur_title: str | None = None
        cur_lines: list[str] = []

        for line in text.splitlines():
            if self._is_chapter_title(line):
                if cur_title is not None:
                    chapters.append(ParsedChapter(
                        cur_title[:_MAX_TITLE_LEN],
                        _normalize_text("\n".join(cur_lines)),
                    ))
                cur_title = line.strip()
                cur_lines = []
            elif cur_title is not None:
                cur_lines.append(line)

        if cur_title is not None:
            chapters.append(ParsedChapter(
                cur_title[:_MAX_TITLE_LEN],
                _normalize_text("\n".join(cur_lines)),
            ))
        # 过滤空正文章节（如「第一卷」类卷标题后紧跟章节的场景）
        return [c for c in chapters if c.content.strip()]

    @staticmethod
    def _split_blank_lines(text: str) -> list[ParsedChapter]:
        """兜底切分：按连续空行分段。

        段数为 1 或超过 300（避免逐段碎片化撑爆 DB）时，整篇作为单章「全文」。
        """
        blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
        if not blocks:
            return []
        if len(blocks) == 1 or len(blocks) > 300:
            whole = _normalize_text(text)
            return [ParsedChapter("全文", whole)] if whole else []

        chapters: list[ParsedChapter] = []
        for i, b in enumerate(blocks, 1):
            first = b.splitlines()[0].strip()
            title = (first[:20] if first else f"第{i}节") or f"第{i}节"
            chapters.append(ParsedChapter(title, _normalize_text(b)))
        return chapters

    # ── TXT ────────────────────────────────────────────────

    def _parse_txt(self, filepath: Path, source_name: str | None = None) -> ParsedBook:
        text = _decode_text(filepath.read_bytes())
        chapters = self._split_by_markers(text)
        if len(chapters) < 2:
            chapters = self._split_blank_lines(text)
        title, author = _infer_from_filename(source_name or filepath.name)
        logger.info("TXT 解析完成: %s — %d 章", filepath.name, len(chapters))
        return ParsedBook(chapters=chapters, title=title, author=author)

    # ── EPUB ───────────────────────────────────────────────

    def _parse_epub(self, filepath: Path, source_name: str | None = None) -> ParsedBook:
        import warnings

        from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
        from ebooklib import ITEM_DOCUMENT, epub

        # EPUB 内容为 XHTML，用 HTML 解析器会触发该警告，此处按文件级屏蔽
        warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

        book = epub.read_epub(str(filepath), options={"ignore_ncx": True})

        # 按 spine 顺序取文档项；spine 为空时退回全部文档项
        items = []
        for item_id, _ in getattr(book, "spine", []) or []:
            it = book.get_item_with_id(item_id)
            if it is not None:
                items.append(it)
        if not items:
            items = list(book.get_items_of_type(ITEM_DOCUMENT))

        chapters: list[ParsedChapter] = []
        for idx, it in enumerate(items, 1):
            # 跳过封面/目录/导航页（非正文）
            fname = (getattr(it, "file_name", "") or "").lower()
            if any(k in fname for k in ("cover", "toc", "nav", "titlepage")):
                continue
            try:
                content = it.get_content()
            except Exception:  # noqa: BLE001 单项损坏不阻断整体
                continue
            soup = BeautifulSoup(content, "lxml")
            for tag in soup(["script", "style"]):
                tag.decompose()

            # 段落级提取，避免 get_text 将行内元素碎片化
            paras = [
                el.get_text(" ", strip=True)
                for el in soup.find_all(["p", "h1", "h2", "h3", "li", "blockquote"])
            ]
            paras = [p for p in paras if p]
            text = "\n".join(paras) if paras else soup.get_text("\n")
            text = _normalize_text(text)
            # 过短项（封面残留/分隔页）跳过
            if len(text) < 10:
                continue

            # 标题：首个 h1~h3 > 项 title > 序号
            title = None
            h = soup.find(["h1", "h2", "h3"])
            if h and h.get_text(strip=True):
                title = h.get_text(strip=True)
            if not title:
                title = getattr(it, "title", None) or f"第{len(chapters) + 1}节"
            chapters.append(ParsedChapter(title.strip()[:_MAX_TITLE_LEN], text))

        title = _first_meta(book.get_metadata("DC", "title"))
        author = _first_meta(book.get_metadata("DC", "creator"))
        if not title:
            title, inferred_author = _infer_from_filename(source_name or filepath.name)
            author = author or inferred_author
        logger.info("EPUB 解析完成: %s — %d 章", filepath.name, len(chapters))
        return ParsedBook(chapters=chapters, title=title, author=author)

    # ── PDF ────────────────────────────────────────────────

    def _parse_pdf(self, filepath: Path, source_name: str | None = None) -> ParsedBook:
        from pypdf import PdfReader

        reader = PdfReader(str(filepath))
        meta = reader.metadata
        title = getattr(meta, "title", None) if meta else None
        author = getattr(meta, "author", None) if meta else None

        pages: list[str] = []
        for page in reader.pages:
            try:
                pages.append(page.extract_text() or "")
            except Exception:  # noqa: BLE001 单页提取失败置空
                pages.append("")

        full = "\n".join(pages)
        chapters = self._split_by_markers(full)
        if len(chapters) < 2:
            # 兜底：按页切分
            chapters = []
            for i, p in enumerate(pages, 1):
                p = _normalize_text(p)
                if p:
                    chapters.append(ParsedChapter(f"第{i}页", p))
            if not chapters:
                whole = _normalize_text(full)
                if whole:
                    chapters = [ParsedChapter("全文", whole)]

        if not title or not str(title).strip():
            title, inferred_author = _infer_from_filename(source_name or filepath.name)
            author = author or inferred_author
        logger.info("PDF 解析完成: %s — %d 章", filepath.name, len(chapters))
        return ParsedBook(chapters=chapters, title=title, author=author)

    # ── DOCX ───────────────────────────────────────────────

    def _parse_docx(self, filepath: Path, source_name: str | None = None) -> ParsedBook:
        import docx

        doc = docx.Document(str(filepath))
        cp = doc.core_properties
        title = (cp.title or "").strip() or None
        author = (cp.author or "").strip() or None

        chapters: list[ParsedChapter] = []
        cur_title: str | None = None
        cur_paras: list[str] = []

        for para in doc.paragraphs:
            text = (para.text or "").strip()
            if not text:
                continue
            style_name = (para.style.name if para.style else "") or ""
            is_heading = (
                style_name.startswith("Heading")
                or style_name.startswith("标题")
                or self._is_chapter_title(text)
            )
            if is_heading:
                if cur_title is not None:
                    chapters.append(ParsedChapter(
                        cur_title[:_MAX_TITLE_LEN],
                        _normalize_text("\n".join(cur_paras)),
                    ))
                cur_title = text
                cur_paras = []
            elif cur_title is not None:
                cur_paras.append(text)

        if cur_title is not None:
            chapters.append(ParsedChapter(
                cur_title[:_MAX_TITLE_LEN],
                _normalize_text("\n".join(cur_paras)),
            ))
        # 过滤空正文章节
        chapters = [c for c in chapters if c.content.strip()]

        if len(chapters) < 2:
            # 兜底：全部段落作为单章
            all_paras = [(p.text or "").strip() for p in doc.paragraphs]
            all_paras = [p for p in all_paras if p]
            if all_paras:
                chapters = [ParsedChapter("全文", _normalize_text("\n".join(all_paras)))]

        if not title:
            title, inferred_author = _infer_from_filename(source_name or filepath.name)
            author = author or inferred_author
        logger.info("DOCX 解析完成: %s — %d 章", filepath.name, len(chapters))
        return ParsedBook(chapters=chapters, title=title, author=author)


# 全局单例
import_service = ImportService()
