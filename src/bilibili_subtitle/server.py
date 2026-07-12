"""MCP server: exposes Bilibili subtitle tools via fastmcp.

Reads SESSDATA from .env file in the project root.

Configure in Claude's MCP settings:

    {
      "mcpServers": {
        "bilibili-subtitle": {
          "command": "uv",
          "args": ["run", "python", "-m", "bilibili_subtitle.server"],
          "cwd": "/absolute/path/to/bilibili-helper"
        }
      }
    }
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from dotenv import load_dotenv
from fastmcp import FastMCP

from .bilibili import BilibiliClient

# Load .env from project root
_env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(_env_path)


@asynccontextmanager
async def _get_client() -> AsyncIterator[BilibiliClient]:
    """Create a BilibiliClient from the configured SESSDATA env var."""
    sessdata = os.environ.get("SESSDATA")
    client = BilibiliClient(sessdata=sessdata)
    try:
        yield client
    finally:
        await client.close()


mcp = FastMCP("bilibili-subtitle")


@mcp.tool()
async def get_subtitle_list(bvid: str, page: int = 1) -> dict:
    """列出B站视频的所有可用字幕轨道。

    Args:
        bvid: 视频的BV号，例如 "BV1xx411c7mD"。
        page: 分P编号（从1开始），默认1。

    Returns:
        包含视频信息和所有字幕轨道列表的字典。
        tracks 按人工 > 未知 > AI 排序。
    """
    async with _get_client() as client:
        video, infos = await client.fetch_subtitle_list(bvid, page)

        return {
            "bvid": video.bvid,
            "title": video.title,
            "page": video.page,
            "total_pages": video.total_pages,
            "page_title": video.page_title,
            "total_tracks": len(infos),
            "tracks": [
                {
                    "id": si.id,
                    "lan": si.lan,
                    "lan_doc": si.lan_doc,
                    "source": si.source,
                }
                for si in infos
            ],
        }


@mcp.tool()
async def get_subtitle(
    bvid: str,
    page: int = 1,
    lan: str | None = None,
    source: str | None = None,
) -> dict:
    """获取B站视频字幕内容。

    未指定 lan 和 source 时，自动选择最佳字幕（人工中文优先）。
    指定过滤条件时返回第一个匹配的字幕。

    Args:
        bvid: 视频的BV号，例如 "BV1xx411c7mD"。
        page: 分P编号（从1开始），默认1。
        lan: 可选的语言过滤，例如 "zh-CN"。
        source: 可选的来源过滤："human" / "ai" / "unknown"。

    Returns:
        包含字幕元信息和完整逐行字幕的字典。
    """
    async with _get_client() as client:
        result = await client.fetch_subtitle(bvid, page, lan=lan, source=source)

        return {
            "bvid": result.bvid,
            "page": result.page,
            "title": result.title,
            "lan": result.lan,
            "lan_doc": result.lan_doc,
            "source": result.source,
            "total_lines": result.total_lines,
            "lines": [
                {
                    "from": line.from_sec,
                    "to": line.to_sec,
                    "time": line.time,
                    "content": line.content,
                }
                for line in result.lines
            ],
        }


def main() -> None:
    """Entry point: run the MCP server over stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
