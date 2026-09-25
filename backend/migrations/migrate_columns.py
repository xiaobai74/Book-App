"""
幂等列迁移脚本 — 为"已存在的表"补齐模型中新增的列。

背景
────
SQLAlchemy 的 ``Base.metadata.create_all`` 只会创建缺失的**表**，不会给已存在的
表补**列**。云端后端（deploy.sh 默认使用 SQLite）在旧版本部署后，``books`` 表缺少
后续版本新增的列：

    cover_path / cover_url / description / category /
    latest_chapter / last_update_time      （v1.7 源站元数据，封面/简介/分类等）
    ai_summary / ai_summary_at             （AI 摘要）

缺列会让"封面显示、AI 摘要"等新功能在运行时报错（no such column）。本脚本用于在
**不丢数据**的前提下把已有库补齐到最新模型。

行为
────
1) ``create_all`` 补齐任何缺失的**表**（例如 reading_progress）；
2) 逐表反射现有列，仅对**缺失的列**执行 ``ALTER TABLE ... ADD COLUMN``；
3) 幂等：可重复运行；SQLite / MySQL 均适用（DDL 由各方言编译器生成）。

用法
────
服务器（务必用后端虚拟环境的 python，并以运行服务的同一用户执行，确保命中同一 DB 路径）::

    cd /opt/novel-backend/backend
    sudo -u novel /opt/novel-backend/.venv/bin/python migrations/migrate_columns.py

本地验证（用一次性 SQLite 库，避免动到 .env 里的 MySQL）::

    cd backend
    set DATABASE_URL=sqlite+aiosqlite:///./_mig_test.db   # PowerShell: $env:DATABASE_URL=...
    python migrations/migrate_columns.py
"""

import asyncio
import re
import sys
from pathlib import Path

# 支持 `python migrations/migrate_columns.py` 直接运行：把 backend/ 根目录加入 sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import inspect, text  # noqa: E402
from sqlalchemy.schema import CreateColumn  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import Base, engine  # noqa: E402

# 导入所有模型，确保 Base.metadata 完整（顺序无关）
from app.models import (  # noqa: E402,F401
    Book,
    Chapter,
    CrawlSource,
    ReadingProgress,
    RefreshToken,
    User,
)


def _masked_url(url: str) -> str:
    """隐藏连接串中的密码，便于安全打印目标库。"""
    return re.sub(r"://([^:/@]+):([^@]+)@", r"://\1:****@", url)


async def migrate() -> int:
    dialect = engine.dialect
    print(f"目标数据库: {_masked_url(settings.database_url)}")
    print(f"方言: {dialect.name}\n")

    added: list[str] = []
    errors: list[str] = []

    async with engine.begin() as conn:
        # 1) 补齐缺失的表（幂等；已存在的表不会被重建）
        await conn.run_sync(Base.metadata.create_all)

        # 2) 逐表比对列，仅补缺失列
        for table in Base.metadata.sorted_tables:
            def _existing_columns(sync_conn, _name=table.name):
                insp = inspect(sync_conn)
                if not insp.has_table(_name):
                    return None
                return {c["name"] for c in insp.get_columns(_name)}

            existing = await conn.run_sync(_existing_columns)
            if existing is None:
                # create_all 之后理论上不会发生；保险跳过
                print(f"[?] 表 {table.name} 仍不存在，跳过")
                continue

            for col in table.columns:
                if col.name in existing:
                    continue
                col_ddl = str(CreateColumn(col).compile(dialect=dialect)).strip()
                quoted_table = dialect.identifier_preparer.quote(table.name)
                stmt = f"ALTER TABLE {quoted_table} ADD COLUMN {col_ddl}"
                try:
                    await conn.execute(text(stmt))
                    added.append(f"{table.name}.{col.name}")
                    print(f"[+] {table.name}.{col.name}  ->  {col_ddl}")
                except Exception as e:  # noqa: BLE001 单列失败不应中断整体迁移
                    errors.append(f"{table.name}.{col.name}: {e}")
                    print(f"[!] 跳过 {table.name}.{col.name}: {e}")

    await engine.dispose()

    print("\n════════ 迁移完成 ════════")
    if added:
        print(f"新增列 {len(added)} 个：{', '.join(added)}")
    else:
        print("没有需要新增的列（数据库已是最新，或此前已迁移过）。")
    if errors:
        print(f"\n注意：{len(errors)} 个列未能自动添加，请手动检查（多为 NOT NULL 无默认值等）：")
        for item in errors:
            print(f"  - {item}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(migrate()))
