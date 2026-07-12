# bilibili-subtitle

MCP server for extracting Bilibili video subtitles/transcripts.

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
        "SESSDATA": "<your cookie value: SESSDATA>"
      }
  }
}
```

## Usage
```
try prompt:

Use the bilibili-subtitle MCP to tell me the content of this link: https://www.bilibili.com/video/BV1yx411L73B
```

### CLI

```bash
uv run bilibili-subtitle list BVxxx
uv run bilibili-subtitle get BVxxx -p 2 -l zh-CN
```
