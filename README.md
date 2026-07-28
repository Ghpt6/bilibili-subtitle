# bilibili-subtitle

MCP server for extracting Bilibili video subtitles/transcripts, fetching video comments, and viewing your Watch Laterlist.

## Tools
Current available mcp tools:
- `get_subtitle_list`: list all available subtitle tracks.
- `get_subtitle`: get subtitle content for a video.
- `get_comments`: get video comments (hot/latest, auto-paginated).
- `get_watch_later`: list your "Watch Later" items.
- `import_browser_cookies`: import Bilibili login cookies from an authorised Chrome/Edge session on Windows.
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
      ]
  }
}
```

Creating and configuring your own `.env` file in project root directory.

For example:
```.env
SESSDATA=xxxxxxxxxxxxxx

BILI_JCT=xxxxxxxxxxxxxx
```

### Import Cookie from Chrome or Edge on Windows

`import_browser_cookies` can create or update the two login entries in `.env`
without exposing their values in the MCP result.

1. Sign in to Bilibili in Chrome or Edge.
2. Enable the browser's permission-based remote debugging feature (for recent
   Chrome versions, open `chrome://inspect/#remote-debugging`).
3. Keep the authorised browser/profile running.
4. Ask the MCP client to call `import_browser_cookies` and approve the
   sensitive write operation and the browser's connection prompt.
5. Restart this MCP server after a successful import.

The tool checks authorised sessions in this order: Chrome before Edge, then
`Default`, `Profile 1`, `Profile 2`, and so on. It saves only `SESSDATA` and
`BILI_JCT`, after confirming the account with Bilibili's login-status API.
It never starts or closes a browser and never decrypts the browser's cookie
database. Closed or unauthorised profiles are skipped.

If the browser does not expose permission-based remote debugging, an already
running DevTools endpoint on loopback port `9222` or `9223` is also detected.
Do not expose a DevTools port to another machine.

## Usage
```
try prompt:

Use the bilibili-subtitle MCP to tell me the content of this link: https://www.bilibili.com/video/BV1yx411L73B

Use the bilibili-subtitle MCP to list what is in my watch later list.

Use the bilibili-subtitle MCP to fetch the comments of this video: https://www.bilibili.com/video/BV1yx411L73B
```

### CLI
Notice: configure your `env` viariable **before** running the following command.
For convenience, just add a `.env` file with `SESSDATA=<...>` and `BILI_JCT=<...>` as option if you want to delete your water-later list in it.

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

