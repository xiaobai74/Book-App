"""
Source connectivity check — test if each source's domain is reachable.
Prints English to avoid Windows GBK encoding issues.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import httpx
import ssl


async def check_url(url, timeout=15):
    """Quick connectivity check for a URL."""
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(timeout),
        follow_redirects=True,
        verify=ssl_ctx,
    ) as client:
        try:
            resp = await client.get(url)
            return f"OK (HTTP {resp.status_code})"
        except httpx.ConnectTimeout:
            return "TIMEOUT (connect)"
        except httpx.ReadTimeout:
            return "TIMEOUT (read)"
        except httpx.ConnectError as e:
            return f"REFUSED: {e}"
        except Exception as e:
            return f"ERROR: {e}"


SOURCES = [
    ("笔趣阁(biquh)", "https://www.biquh.com/"),
    ("香书小说", "http://www.xbiqugu.la/"),
    ("书海阁小说网", "https://www.shuhaige.net/"),
    ("梦书中文", "http://www.mcxs.info/"),
    ("笔趣阁22", "https://www.22biqu.com/"),
    ("笔尖中文", "http://www.xbiquwk.com/"),
    ("悠久小说网", "http://www.ujxsw.org/"),
    ("阅读库", "http://www.yeudusk.com/"),
    ("笔趣阁365", "https://www.biquge365.net/"),
    ("燃文小说网", "https://www.ranwen8.cc/"),
    ("笔趣阁365备用", "https://www.biquge365.xyz/"),
]

async def main():
    print("=" * 60)
    print("Source Connectivity Check")
    print("=" * 60)
    for name, url in SOURCES:
        result = await check_url(url)
        print(f"  {name:20s} | {url:40s} | {result}")

asyncio.run(main())
