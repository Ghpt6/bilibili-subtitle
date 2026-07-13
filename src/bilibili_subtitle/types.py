"""Shared types and exceptions for bilibili-subtitle."""

from __future__ import annotations

from dataclasses import dataclass, field


class BilibiliError(Exception):
    """Unified error for all Bilibili API failures."""

    def __init__(self, message: str, code: int | None = None):
        super().__init__(message)
        self.code = code

    def __str__(self) -> str:
        if self.code is not None:
            return f"[code={self.code}] {super().__str__()}"
        return super().__str__()


@dataclass
class SubtitleInfo:
    """Metadata for a single subtitle track."""

    id: str
    lan: str
    lan_doc: str
    source: str  # "human" | "ai" | "unknown"
    subtitle_url: str
    type: int = 0
    ai_status: int = 0
    ai_type: int = 0


@dataclass
class SubtitleLine:
    """A single subtitle line."""

    from_sec: float
    to_sec: float
    content: str
    time: str = ""  # formatted MM:SS


@dataclass
class SubtitleResult:
    """Full subtitle result for a video."""

    bvid: str
    page: int
    title: str
    lan: str
    lan_doc: str
    source: str
    total_lines: int
    lines: list[SubtitleLine] = field(default_factory=list)


@dataclass
class WatchLaterItem:
    """A single item in the user's "稍后再看" (Watch Later) list."""

    bvid: str
    aid: int
    title: str
    duration: str  # formatted HH:MM:SS
    owner_name: str
    stat: dict


@dataclass
class CommentInfo:
    """B站视频评论（主评论或子回复，结构相同）。"""

    rpid: str  # 评论 ID
    mid: int  # 评论者 UID
    uname: str  # 评论者昵称
    content: str  # 评论正文
    ctime: int  # 发布时间（Unix 时间戳）
    like: int  # 点赞数
    reply_count: int  # 子回复数量
    replies: list[CommentInfo] = field(default_factory=list)  # 内嵌子回复（最多 3 条）


@dataclass
class CommentResult:
    """视频评论完整结果。"""

    bvid: str  # 视频 BV 号
    aid: int  # 视频 AV 号
    title: str  # 视频标题
    sort: str  # 排序方式："hot" / "time"
    total_comments: int  # 返回的评论总数
    comments: list[CommentInfo] = field(default_factory=list)


@dataclass
class VideoInfo:
    """Parsed video metadata."""

    bvid: str
    aid: int
    cid: int
    title: str
    page: int
    total_pages: int
    page_title: str
    subtitle_list: list[dict] = field(default_factory=list)
