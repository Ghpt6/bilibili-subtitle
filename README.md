# bilibili-subtitle

MCP server for extracting Bilibili video subtitles/transcripts.

## Setup

```bash
uv sync
```

## Usage

### MCP Server

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

### CLI

```bash
uv run bilibili-subtitle list BVxxx
uv run bilibili-subtitle get BVxxx -p 2 -l zh-CN
```
