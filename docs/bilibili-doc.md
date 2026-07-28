# BilibiliClient

`BilibiliClient` 是项目访问 Bilibili API 的异步客户端，封装了视频信息、字幕、评论和“稍后再看”等功能。

```python
from bilibili_subtitle.bilibili import BilibiliClient

client = BilibiliClient(
    sessdata="your_sessdata",
    bili_jct="your_bili_jct",
)

try:
    result = await client.fetch_subtitle("BVxxxxxxxxxx")
finally:
    await client.close()
```

## 初始化

```python
BilibiliClient(
    sessdata: str | None = None,
    bili_jct: str | None = None,
)
```

- `sessdata`：Bilibili 登录 Cookie。读取登录后可见的字幕、评论和“稍后再看”时可能需要。
- `bili_jct`：CSRF Token。删除或清空“稍后再看”时必须提供。

客户端基于 `httpx.AsyncClient`，使用完毕后应调用：

```python
await client.close()
```

请求失败、参数无效或 Bilibili 返回业务错误时，方法统一抛出 `BilibiliError`。

## 字幕

### 获取字幕

```python
await client.fetch_subtitle(
    bvid: str,
    page: int = 1,
    lan: str | None = None,
    source: str | None = None,
) -> SubtitleResult
```

这是获取字幕的主要入口。它会读取视频信息、选择字幕轨道并下载完整字幕内容。

- `bvid`：视频 BV 号。
- `page`：分 P 序号，从 `1` 开始。
- `lan`：可选的语言代码，如 `zh-CN`。
- `source`：可选的字幕来源，可为 `human`、`ai` 或 `unknown`。

未指定筛选条件时，客户端优先选择人工中文字幕，其次选择其他人工字幕和来源未知的字幕。

```python
result = await client.fetch_subtitle(
    "BVxxxxxxxxxx",
    page=1,
    lan="zh-CN",
    source="human",
)

for line in result.lines:
    print(line.time, line.content)
```

返回的 `SubtitleResult` 包含视频标题、语言、字幕来源、字幕总行数和 `SubtitleLine` 列表。

### 获取字幕轨道

```python
await client.fetch_subtitle_list(
    bvid: str,
    page: int = 1,
) -> tuple[VideoInfo, list[SubtitleInfo]]
```

只读取视频信息和可用字幕轨道，不下载字幕正文。适合先展示语言和来源，再由调用方决定使用哪条字幕。

```python
video, tracks = await client.fetch_subtitle_list("BVxxxxxxxxxx")

for track in tracks:
    print(track.lan, track.lan_doc, track.source)
```

字幕轨道按人工、未知、AI 的顺序排列。若视频存在字幕但接口要求登录，客户端会提示配置 `SESSDATA`。

## 视频信息

```python
await client.get_video_info(
    bvid: str,
    page: int = 1,
) -> VideoInfo
```

返回视频的 `bvid`、`aid`、当前分 P 的 `cid`、标题、分 P 标题和总分 P 数。无效 BV 号或越界的分 P 会抛出 `BilibiliError`。

## 评论

```python
await client.get_comments(
    bvid: str,
    sort: str = "hot",
    max_results: int | None = 20,
) -> CommentResult
```

分页获取视频主评论，并保留接口返回的嵌套回复。

- `sort="hot"`：按热度排序。
- `sort="time"`：按时间排序。
- `max_results=None`：持续分页，直到没有更多评论。

`max_results` 限制的是主评论数量，不包含嵌套回复。

```python
result = await client.get_comments(
    "BVxxxxxxxxxx",
    sort="hot",
    max_results=50,
)

for comment in result.comments:
    print(comment.uname, comment.content)
```

## 稍后再看

这些方法访问当前登录用户的数据，通常需要有效的 `SESSDATA`。

### 获取列表

```python
await client.get_watch_later(
    max_results: int | None = None,
) -> list[WatchLaterItem]
```

自动分页读取“稍后再看”。`max_results` 可限制返回数量。

### 删除视频

```python
await client.remove_watch_later(bvid: str) -> dict
```

从“稍后再看”中删除指定 BV 号的视频。需要同时配置 `SESSDATA` 和 `bili_jct`。

### 清空列表

```python
await client.clear_watch_later() -> dict
```

清空当前账号的“稍后再看”列表。该操作不可由客户端撤销，并且需要同时配置 `SESSDATA` 和 `bili_jct`。

## 底层字幕方法

通常应优先使用 `fetch_subtitle()` 和 `fetch_subtitle_list()`。需要自行组合流程时，可使用：

- `get_subtitle_list(aid, cid)`：获取接口返回的原始字幕轨道。
- `get_subtitle_content(subtitle_url)`：下载并解析指定轨道的字幕正文。

