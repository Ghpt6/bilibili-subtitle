"""CLI entry point for bilibili-subtitle.

Usage:
    bilibili-subtitle list BVxxx              # list subtitle tracks
    bilibili-subtitle get BVxxx               # get best subtitle content
    bilibili-subtitle get BVxxx -p 2          # specific page
    bilibili-subtitle get BVxxx -l zh-CN      # filter by language
    bilibili-subtitle get BVxxx -s human      # filter by source
    bilibili-subtitle toview                  # list watch-later items
    bilibili-subtitle toview -n 10            # limit to 10 items
    bilibili-subtitle comments BVxxx          # get video comments (hot, 20)
    bilibili-subtitle comments BVxxx -s time  # sort by latest
    bilibili-subtitle comments BVxxx -n 50    # limit to 50 items
    bilibili-subtitle remove BVxxx            # remove from watch later
    bilibili-subtitle clear                   # clear entire watch later
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from .bilibili import BilibiliClient
from .types import BilibiliError

# Load .env from project root
_env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(_env_path)


def _client_from_env() -> BilibiliClient:
    return BilibiliClient(
        sessdata=os.environ.get("SESSDATA"),
        bili_jct=os.environ.get("BILI_JCT"),
    )


async def cmd_list(args: argparse.Namespace) -> None:
    client = _client_from_env()
    try:
        video, infos = await client.fetch_subtitle_list(args.bvid, page=args.page)
        output = {
            "bvid": video.bvid,
            "title": video.title,
            "page": video.page,
            "total_pages": video.total_pages,
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
        print(json.dumps(output, ensure_ascii=False, indent=2))
    except BilibiliError as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
    finally:
        await client.close()


async def cmd_get(args: argparse.Namespace) -> None:
    client = _client_from_env()
    try:
        result = await client.fetch_subtitle(
            args.bvid, page=args.page, lan=args.lan, source=args.source
        )
        output = {
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
        print(json.dumps(output, ensure_ascii=False, indent=2))
    except BilibiliError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        await client.close()


def _serialize_comment_cli(c) -> dict:
    """Serialize a CommentInfo to a dict recursively."""
    return {
        "rpid": c.rpid,
        "mid": c.mid,
        "uname": c.uname,
        "content": c.content,
        "ctime": c.ctime,
        "like": c.like,
        "reply_count": c.reply_count,
        "replies": [_serialize_comment_cli(r) for r in c.replies],
    }


async def cmd_comments(args: argparse.Namespace) -> None:
    client = _client_from_env()
    try:
        result = await client.get_comments(
            args.bvid, sort=args.sort, max_results=args.max_results
        )
        output = {
            "bvid": result.bvid,
            "aid": result.aid,
            "title": result.title,
            "sort": result.sort,
            "total_comments": result.total_comments,
            "comments": [_serialize_comment_cli(c) for c in result.comments],
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    except BilibiliError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        await client.close()


async def cmd_toview(args: argparse.Namespace) -> None:
    client = _client_from_env()
    try:
        items = await client.get_watch_later(max_results=args.max_results)
        output = {
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
        print(json.dumps(output, ensure_ascii=False, indent=2))
    except BilibiliError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        await client.close()


async def cmd_remove(args: argparse.Namespace) -> None:
    client = _client_from_env()
    try:
        result = await client.remove_watch_later(args.bvid)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except BilibiliError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        await client.close()


async def cmd_clear(args: argparse.Namespace) -> None:
    client = _client_from_env()
    try:
        result = await client.clear_watch_later()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except BilibiliError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        await client.close()


def main() -> None:
    # Ensure UTF-8 output on Windows (comments may contain emoji etc.)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        prog="bilibili-subtitle",
        description="Extract Bilibili video subtitles from the command line.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # list
    list_p = sub.add_parser("list", help="List available subtitle tracks")
    list_p.add_argument("bvid", help="Video BV ID")
    list_p.add_argument("-p", "--page", type=int, default=1, help="Page number (default: 1)")

    # get
    get_p = sub.add_parser("get", help="Get subtitle content")
    get_p.add_argument("bvid", help="Video BV ID")
    get_p.add_argument("-p", "--page", type=int, default=1, help="Page number (default: 1)")
    get_p.add_argument("-l", "--lan", help="Filter by language (e.g. zh-CN)")
    get_p.add_argument("-s", "--source", help="Filter by source (human/ai/unknown)")

    # toview
    toview_p = sub.add_parser("toview", help="List watch-later items")
    toview_p.add_argument("-n", "--max-results", type=int, default=None, help="Max results (default: all)")

    # comments
    comments_p = sub.add_parser("comments", help="Get video comments")
    comments_p.add_argument("bvid", help="Video BV ID")
    comments_p.add_argument(
        "-s", "--sort", default="hot", choices=["hot", "time"], help="Sort order (default: hot)"
    )
    comments_p.add_argument("-n", "--max-results", type=int, default=20, help="Max results (default: 20)")

    # remove
    remove_p = sub.add_parser("remove", help="Remove a video from watch later")
    remove_p.add_argument("bvid", help="Video BV ID")

    # clear
    sub.add_parser("clear", help="Clear entire watch later list")

    args = parser.parse_args()

    if args.command == "list":
        asyncio.run(cmd_list(args))
    elif args.command == "get":
        asyncio.run(cmd_get(args))
    elif args.command == "toview":
        asyncio.run(cmd_toview(args))
    elif args.command == "comments":
        asyncio.run(cmd_comments(args))
    elif args.command == "remove":
        asyncio.run(cmd_remove(args))
    elif args.command == "clear":
        asyncio.run(cmd_clear(args))


if __name__ == "__main__":
    main()
