"""文件名安全过滤工具

用于 EPUB/TXT 生成时的文件名构造，避免 Windows 非法字符导致写入失败、
文件名过长超出 MAX_PATH 限制。
"""

# 文件名组件最大长度（保守值，避免与 book_id 拼接后超过 Windows MAX_PATH 260 字符）
_MAX_COMPONENT_LEN = 100


def safe_filename_component(text: str, fallback: str = "book") -> str:
    """过滤文件名中的非法字符并截断，返回安全文件名组件。

    与原有 safe_title 逻辑一致：仅保留字母数字（含中文）、空格与
    `` _-（）()``，其余字符剔除；长度超过 ``_MAX_COMPONENT_LEN`` 时截断。
    """
    cleaned = "".join(c for c in text if c.isalnum() or c in " _-（）()")
    cleaned = cleaned.strip()
    if len(cleaned) > _MAX_COMPONENT_LEN:
        cleaned = cleaned[:_MAX_COMPONENT_LEN].rstrip()
    return cleaned or fallback
