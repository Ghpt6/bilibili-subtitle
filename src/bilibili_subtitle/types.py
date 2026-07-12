"""Shared types and exceptions for bilibili-subtitle."""

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
