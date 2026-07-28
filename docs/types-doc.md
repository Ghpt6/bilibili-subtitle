# `types.py`

`src/bilibili_subtitle/types.py` 定义项目共享的异常和数据模型。`BilibiliClient`、CLI 与 MCP 服务均使用这些类型。

## `BilibiliError`

`BilibiliError` 是项目统一的异常类型，用于表示参数错误、网络错误和 Bilibili API 业务错误。

```python
try:
    result = await client.fetch_subtitle("BVxxxxxxxxxx")
except BilibiliError as exc:
    print(exc)
```

异常可以携带 Bilibili 业务错误码：

```python
BilibiliError("request failed", code=-400)
```

转换为字符串后：

```text
[code=-400] request failed
```

## 数据模型

所有数据模型都使用 `dataclass` 定义。

### `VideoInfo`

保存视频和分 P 信息：

- `bvid`、`aid`、`cid`
- 视频标题和当前分 P 标题
- 当前分 P 与总分 P 数
- 视频接口返回的字幕提示列表

### `SubtitleInfo`

保存单条字幕轨道信息：

- 字幕 ID
- 语言代码和显示名称
- 来源：`human`、`ai` 或 `unknown`
- 字幕下载 URL
- AI 识别相关字段

### `SubtitleLine`

表示一行字幕，包含开始时间、结束时间、正文和格式化时间。

### `SubtitleResult`

表示完整字幕结果，包含视频信息、字幕语言、来源、总行数和 `SubtitleLine` 列表。

### `CommentInfo`

表示一条主评论或回复，包含：

- 评论 ID 和用户 UID
- 用户名和评论正文
- 发布时间与点赞数
- 回复总数
- 嵌套的 `CommentInfo` 列表

### `CommentResult`

保存视频信息、评论排序方式、返回数量和主评论列表。

### `WatchLaterItem`

表示“稍后再看”中的一个视频，包含 BV 号、AV 号、标题、时长、UP 主名称和统计数据。

列表字段使用 `field(default_factory=list)` 创建，避免不同模型实例共享同一个可变列表。
