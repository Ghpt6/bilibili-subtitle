# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync                        # install dependencies
uv run bilibili-subtitle list BVxxx    # CLI: list subtitle tracks
uv run bilibili-subtitle get BVxxx     # CLI: get subtitle content
```

## Architecture

This is a Python MCP server that extracts subtitles from B站 (Bilibili) videos. It exposes two tools (`get_subtitle_list`, `get_subtitle`) via fastmcp over stdio, plus an identical CLI (`cli.py`). All B站 API logic lives in `bilibili.py`; the server and CLI are thin wrappers.

### API chain (3 steps)

Every subtitle extraction walks this pipeline:

1. **`view` API** → `GET /x/web-interface/view?bvid=...` → returns `aid`, `cid`, `pages[]`, and an optional `subtitle.list` (used as source-detection hints).
2. **`wbi/v2` API** → `GET /x/player/wbi/v2?aid=...&cid=...` (wbi-signed) → returns `subtitle.subtitles[]` with `subtitle_url` and metadata fields used to classify source.
3. **CDN subtitle JSON** → `GET {subtitle_url}` (includes `auth_key` query param from step 2) → returns `{"body": [{"from": ..., "to": ..., "content": "..."}]}`.

Steps 1 and 2 require Cookie (`SESSDATA`). Step 3 (CDN) does not.

### WBI signing (`wbi.py`)

The wbi/v2 endpoint requires `w_rid` + `wts` parameters. Flow:

1. `GET /x/web-interface/nav` → `data.wbi_img` contains `img_url` and `sub_url` (NOT `img_key`/`sub_key` — the key is the filename without extension, e.g. `7cd084941338484aae1ad9425b84077c.png` → `7cd084941338484aae1ad9425b84077c`).
2. Concatenate `img_key + sub_key`, apply the fixed `MIXIN_KEY_ENC_TAB` permutation, truncate to 32 chars → `mixin_key`.
3. Sort request params by key, build query string, append `mixin_key`, MD5 → `w_rid`. Add `wts` (current Unix timestamp).

`get_mixin_key()` is called per-request (no caching by design decision).

### Subtitle source classification (`_detect_source`)

Classifies each subtitle track as `"human"`, `"ai"`, or `"unknown"` by checking multiple signals in priority order: `type` field (0=human, 1=AI) → `ai_status`/`ai_type` > 0 → language prefix `ai-` → URL contains `aisubtitle.hdslb.com`/`/ai_subtitle/`/`/aisubtitle/` → boolean flags (`is_ai`, `is_ai_subtitle`, `is_machine`) → explicit `source` field.

Tracks are sorted human-first. Default selection priority: human-zh > human-any > unknown-zh > unknown-any > zh-any > first item.

### Key gotchas

- **CDN responses lack a `code` field.** `_get_json()` has `check_code=True` by default (checks `response["code"] == 0` per B站 API convention). Pass `check_code=False` when calling CDN endpoints — otherwise it errors with `code=-1`.
- **wbi/v2 returns empty `subtitles` without Cookie.** The `view` API may report subtitles exist, but wbi/v2 withholds the URLs unless `SESSDATA` is present. `fetch_subtitle_list()` explicitly checks for this mismatch and raises a helpful error.
- **Auth is set via MCP config `env` block.** `SESSDATA` is passed through the MCP config's `env` field (see README). Both `server.py` and `cli.py` also support loading from `.env` via `python-dotenv`.

## Reference

Based on [glasscatya/bilibili-video-transcript](https://github.com/glasscatya/bilibili-video-transcript) (Chrome extension). This project adapts its API chain and source-detection logic from browser-extension to headless Python/MCP context.
