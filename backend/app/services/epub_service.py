"""
EPUB 生成服务

使用 EbookLib 生成符合 EPUB 3.2 规范的电子书文件。
"""

import logging
from pathlib import Path

from ebooklib import epub

from app.config import settings
from app.utils.filenames import safe_filename_component

logger = logging.getLogger(__name__)

# EPUB 输出目录（桌面版存用户数据目录，由 config 统一配置）
_EPUB_OUTPUT_DIR = Path(settings.epub_output_dir)


class EpubService:
    """EPUB 电子书生成器"""

    _COVER_COLORS = [
        "#dce8ef", "#d5dfe6", "#cbd8e2", "#d8e2ea",
        "#d0dbe4", "#c5d2dd", "#dae4ec", "#cdd8e0",
    ]

    def __init__(self, output_dir: Path | None = None):
        self.output_dir = output_dir or _EPUB_OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        book_id: str,
        title: str,
        author: str,
        chapters: list[dict],
    ) -> str:
        """
        生成 .epub 文件。

        Args:
            book_id: 书籍 UUID（用作文件名）
            title: 书名
            author: 作者
            chapters: 章节列表 [{"title": "...", "content": "..."}, ...]

        Returns:
            生成的文件路径
        """
        book = epub.EpubBook()

        # ── 元数据 ──────────────────────────────────
        book.set_identifier(book_id)
        book.set_title(title)
        book.set_language("zh-CN")
        book.add_author(author)
        book.add_metadata("DC", "publisher", "小说管理App")
        book.add_metadata("DC", "date", "")
        book.add_metadata(None, "meta", "", {"property": "dcterms:modified"})

        # ── CSS ─────────────────────────────────────
        style = epub.EpubItem(
            uid="style",
            file_name="style/default.css",
            media_type="text/css",
            content=b"""
body { font-family: "PingFang SC", "Noto Serif CJK SC", "SimSun", serif; line-height: 1.8; margin: 0 1em; }
h1, h2 { text-align: center; margin: 1.5em 0 0.5em; }
h1 { font-size: 1.6em; }
h2 { font-size: 1.3em; color: #555; }
p { text-indent: 2em; margin: 0.5em 0; }
.cover-page { text-align: center; padding-top: 30%; }
.cover-page h1 { font-size: 2em; margin-bottom: 0.3em; }
.cover-page .author { font-size: 1.2em; color: #666; }
""",
        )
        book.add_item(style)

        # ── 封面页 ──────────────────────────────────
        cover_color = self._COVER_COLORS[hash(title) % len(self._COVER_COLORS)]
        cover_html = epub.EpubHtml(
            title="封面",
            file_name="cover.xhtml",
            lang="zh-CN",
        )
        cover_html.content = f"""<html>
<head><link rel="stylesheet" href="style/default.css" type="text/css"/></head>
<body>
<div class="cover-page" style="background:{cover_color};margin:-1em;padding:3em 1em;min-height:80vh">
<h1>{self._escape(title)}</h1>
<p class="author" style="text-indent:0">{self._escape(author)}</p>
</div>
</body>
</html>"""
        book.add_item(cover_html)

        # ── 目录页 ──────────────────────────────────
        toc_html = epub.EpubHtml(
            title="目录",
            file_name="toc.xhtml",
            lang="zh-CN",
        )
        toc_rows = "".join(
            f'<li><a href="chap_{i+1:04d}.xhtml">{self._escape(ch.get("title", f"第{i+1}章"))}</a></li>'
            for i, ch in enumerate(chapters)
        )
        toc_html.content = f"""<html>
<head><link rel="stylesheet" href="style/default.css" type="text/css"/></head>
<body>
<h1>目录</h1>
<ol style="list-style:none;padding:0">{toc_rows}</ol>
</body>
</html>"""
        book.add_item(toc_html)

        # ── 章节 ────────────────────────────────────
        epub_chapters = []
        for i, ch in enumerate(chapters):
            ch_title = ch.get("title", f"第{i + 1}章")
            ch_content = ch.get("content", "")
            ch_file_name = f"chap_{i + 1:04d}.xhtml"

            ch_html = epub.EpubHtml(
                title=ch_title,
                file_name=ch_file_name,
                lang="zh-CN",
            )
            paragraphs = "".join(
                f"<p>{self._escape(para)}</p>"
                for para in ch_content.split("\n")
                if para.strip()
            )
            ch_html.content = f"""<html>
<head><link rel="stylesheet" href="style/default.css" type="text/css"/></head>
<body>
<h2>{self._escape(ch_title)}</h2>
{paragraphs}
</body>
</html>"""
            book.add_item(ch_html)
            epub_chapters.append(ch_html)

        # ── 目录结构 ────────────────────────────────
        book.toc = [
            epub.Link("cover.xhtml", "封面", "cover"),
            epub.Link("toc.xhtml", "目录", "toc"),
            (
                epub.Section("正文"),
                [ch for ch in epub_chapters],
            ),
        ]

        # ── 书脊（阅读顺序） ────────────────────────
        book.spine = ["cover", "toc"] + [f"chap_{i+1:04d}.xhtml" for i in range(len(chapters))]

        # ── 必要属性 ────────────────────────────────
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        # ── 写入文件 ────────────────────────────────
        # 使用 book_id 作为文件名前缀，防止同名书覆盖
        # 书名与作者均做安全过滤，避免 Windows 非法字符导致写入失败
        safe_title = safe_filename_component(title, "book")
        safe_author = safe_filename_component(author, "未知作者")
        filename = f"({book_id}){safe_title}-{safe_author}.epub"
        filepath = str(self.output_dir / filename)

        epub.write_epub(filepath, book, {})

        logger.info(f"EPUB 生成完成: {filepath}")
        return filepath

    @staticmethod
    def _escape(text: str) -> str:
        """XML/HTML 转义"""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )


# 全局单例
epub_service = EpubService()
