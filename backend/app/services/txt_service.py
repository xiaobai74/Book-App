"""
TXT 生成服务

将小说章节内容拼接为纯文本文件，UTF-8 编码，规范排版。
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# TXT 输出目录
_TXT_OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "txt_output"


class TxtService:
    """TXT 文本文件生成器"""

    def __init__(self, output_dir: Path | None = None):
        self.output_dir = output_dir or _TXT_OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        book_id: str,
        title: str,
        author: str,
        chapters: list[dict],
    ) -> str:
        """生成 .txt 文件。

        Args:
            book_id: 书籍 UUID（用作文件名的一部分）
            title: 书名
            author: 作者
            chapters: 章节列表 [{"title": "...", "content": "..."}, ...]

        Returns:
            生成的文件路径
        """
        safe_title = "".join(c for c in title if c.isalnum() or c in " _-（）()").strip()
        safe_title = safe_title or "book"  # 标题全部被过滤时使用默认值
        filename = f"({book_id}){safe_title}-{author}.txt"
        filepath = str(self.output_dir / filename)

        lines: list[str] = []

        # ── 封面 ────────────────────────────────────
        lines.append(title)
        lines.append(f"作者：{author}")
        lines.append("")

        # ── 正文 ────────────────────────────────────
        for i, ch in enumerate(chapters):
            ch_title = ch.get("title", f"第{i + 1}章")
            ch_content = ch.get("content", "")

            # 章节标题：避免重复编号（如原标题已是"第1章 xxx"则不再添加前缀）
            import re as _re
            if _re.match(r"第\s*\d+\s*[章节回]", ch_title.strip()):
                lines.append(f"\n{ch_title}\n")
            else:
                lines.append(f"\n第{i + 1}章  {ch_title}\n")
            lines.append("")

            # 章节内容：按段落写入
            for para in ch_content.split("\n"):
                para = para.strip()
                if para:
                    # 每段首行缩进两个全角空格
                    lines.append(f"　　{para}")
            lines.append("")

        # ── 写入文件 ────────────────────────────────
        text = "\n".join(lines)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(text)

        logger.info(f"TXT 生成完成: {filepath} ({len(text)} 字符)")
        return filepath


# 全局单例
txt_service = TxtService()
