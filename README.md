# bilibili-subtitle

MCP server for extracting Bilibili video subtitles/transcripts, fetching video comments, and viewing your Watch Laterlist.

## Tools
Current available mcp tools:
- `get_subtitle_list`: list all available subtitle tracks.
- `get_subtitle`: get subtitle content for a video.
- `get_comments`: get video comments (hot/latest, auto-paginated).
- `get_watch_later`: list your "Watch Later" items.
- `remove_watch_later`: remove a video from "Watch Later" (requires `BILI_JCT` CSRF token).
- `clear_watch_later`: clear the entire "Watch Later" list (requires `BILI_JCT` CSRF token).

## Setup

```bash
git clone https://github.com/Ghpt6/bilibili-subtitle.git

cd bilibili-subtitle

# initialization
uv sync

# test
uv run python -m bilibili_subtitle.server

╭──────────────────────────────────────────────────────────────────────────────╮
│                                                                              │
│                                                                              │
│                         ▄▀▀ ▄▀█ █▀▀ ▀█▀ █▀▄▀█ █▀▀ █▀█                        │
│                         █▀  █▀█ ▄▄█  █  █ ▀ █ █▄▄ █▀▀                        │
│                                                                              │
│                                                                              │
│                                                                              │
│                                FastMCP 3.4.4                                 │
│                            https://gofastmcp.com                             │
│                                                                              │
│                  🖥  Server:      bilibili-subtitle, 3.4.4                    │
│                  🚀 Deploy free: https://horizon.prefect.io                  │
│                                                                              │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### Add MCP Server To Your Agents

```json
{
  "mcpServers": {
    "bilibili-subtitle": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "<bilibili-subtitle mcp working directory>",
        "python",
        "-m",
        "bilibili_subtitle.server"
      ],
      "env": {
        "SESSDATA": "<your cookie value: SESSDATA>",
        "bili_jct": "<your cookie value: bili_jct>"
      }
  }
}
```

## Usage
```
try prompt:

Use the bilibili-subtitle MCP to tell me the content of this link: https://www.bilibili.com/video/BV1yx411L73B

Use the bilibili-subtitle MCP to list what is in my watch later list.

Use the bilibili-subtitle MCP to fetch the comments of this video: https://www.bilibili.com/video/BV1yx411L73B
```

### CLI
Notice: configure your `env` viariable **before** running the following command.
For convenience, just add a `.env` file with `SESSDATA=<...>` and `bili_jct=<...>` as option if you want to delete your water-later list in it.

```bash
uv run bilibili-subtitle list BVxxx
uv run bilibili-subtitle get BVxxx -p 2 -l zh-CN
uv run bilibili-subtitle toview
uv run bilibili-subtitle toview -n 10
uv run bilibili-subtitle comments BVxxx
uv run bilibili-subtitle comments BVxxx -s time
uv run bilibili-subtitle comments BVxxx -n 50
uv run bilibili-subtitle remove BVxxx
uv run bilibili-subtitle clear
```

