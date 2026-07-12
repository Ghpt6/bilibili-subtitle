"""CLI entry point for bilibili-subtitle.

Usage:
    bilibili-subtitle list BVxxx              # list subtitle tracks
    bilibili-subtitle get BVxxx               # get best subtitle content
    bilibili-subtitle get BVxxx -p 2          # specific page
    bilibili-subtitle get BVxxx -l zh-CN      # filter by language
    bilibili-subtitle get BVxxx -s human      # filter by source
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
    return BilibiliClient(sessdata=os.environ.get("SESSDATA"))


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


def main() -> None:
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

    args = parser.parse_args()

    if args.command == "list":
        asyncio.run(cmd_list(args))
    elif args.command == "get":
        asyncio.run(cmd_get(args))


if __name__ == "__main__":
    main()
