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
      "args": ["run", "python", "-m", "bilibili_subtitle.server"],
      "cwd": "/absolute/path/to/bilibili-helper"
    }
  }
}
```

### CLI

```bash
uv run bilibili-subtitle list BVxxx
uv run bilibili-subtitle get BVxxx -p 2 -l zh-CN
```
