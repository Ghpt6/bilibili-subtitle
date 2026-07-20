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
from .types import CommentInfo

# Load .env from project root
_env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(_env_path)


@asynccontextmanager
async def _get_client() -> AsyncIterator[BilibiliClient]:
    """Create a BilibiliClient from configured env vars."""
    sessdata = os.environ.get("SESSDATA")
    bili_jct = os.environ.get("BILI_JCT")
    client = BilibiliClient(sessdata=sessdata, bili_jct=bili_jct)
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


@mcp.tool()
async def get_watch_later(max_results: int | None = None) -> dict:
    """获取"稍后再看"收藏夹内容。

    Args:
        max_results: 可选，限制返回的最大条目数。默认返回全部。

    Returns:
        包含条目总数和所有稍后再看视频的字典。
        每个视频包含 bvid, title, duration(HH:MM:SS), owner_name, stat。
    """
    async with _get_client() as client:
        items = await client.get_watch_later(max_results=max_results)

        return {
            "total": len(items),
            "items": [
                {
                    "bvid": item.bvid,
                    "title": item.title,
                    "duration": item.duration,
                    "owner_name": item.owner_name,
                    "stat": item.stat,
                }
                for item in items
            ],
        }


@mcp.tool()
async def get_comments(
    bvid: str,
    sort: str = "hot",
    max_results: int | None = 20,
) -> dict:
    """获取B站视频评论。

    默认按热度排序，自动翻页获取所有评论。

    Args:
        bvid: 视频的BV号，例如 "BV1xx411c7mD"。
        sort: 排序方式，"hot"（热度，默认）/ "time"（最新）。
        max_results: 可选，限制返回的最大评论数。默认 20。

    Returns:
        包含视频信息、排序方式和评论列表的字典。
        每条评论包含 rpid, mid, uname, content, ctime, like, reply_count, replies。
    """
    async with _get_client() as client:
        result = await client.get_comments(bvid, sort=sort, max_results=max_results)

        return {
            "bvid": result.bvid,
            "aid": result.aid,
            "title": result.title,
            "sort": result.sort,
            "total_comments": result.total_comments,
            "comments": [_serialize_comment(c) for c in result.comments],
        }


def _serialize_comment(c: CommentInfo) -> dict:
    """Serialize a CommentInfo to a dict, recursively handling sub-replies."""
    return {
        "rpid": c.rpid,  # 评论 ID
        "mid": c.mid,  # 评论者 UID
        "uname": c.uname,  # 评论者昵称
        "content": c.content,  # 评论正文
        "ctime": c.ctime,  # 发布时间（Unix 时间戳）
        "like": c.like,  # 点赞数
        "reply_count": c.reply_count,  # 子回复数量
        "replies": [_serialize_comment(r) for r in c.replies],  # 内嵌子回复
    }


@mcp.tool()
async def remove_watch_later(bvid: str) -> dict:
    """从"稍后再看"列表中删除指定视频。

    CSRF 令牌（bili_jct）需通过环境变量 BILI_JCT 或 MCP config env 提供。

    Args:
        bvid: 要删除的视频的BV号，例如 "BV1xx411c7mD"。

    Returns:
        包含 success, bvid, aid 的字典。
    """
    async with _get_client() as client:
        return await client.remove_watch_later(bvid)


@mcp.tool()
async def clear_watch_later() -> dict:
    """清空整个"稍后再看"列表。

    CSRF 令牌（bili_jct）需通过环境变量 BILI_JCT 或 MCP config env 提供。

    Returns:
        包含 success 的字典。
    """
    async with _get_client() as client:
        return await client.clear_watch_later()


def main() -> None:
    """Entry point: run the MCP server over stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
