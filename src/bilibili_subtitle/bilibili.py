"""Core Bilibili API client: video info, subtitle list, subtitle content."""

import os
import re
from typing import Any

import httpx

from .types import (
    BilibiliError,
    CommentInfo,
    CommentResult,
    SubtitleInfo,
    SubtitleLine,
    SubtitleResult,
    VideoInfo,
    WatchLaterItem,
)
from .wbi import get_mixin_key, sign_params

BILIBILI_VIEW_URL = "https://api.bilibili.com/x/web-interface/view"
BILIBILI_PLAYER_URL = "https://api.bilibili.com/x/player/wbi/v2"
BILIBILI_TOVIEW_URL = "https://api.bilibili.com/x/v2/history/toview"
BILIBILI_COMMENT_URL = "https://api.bilibili.com/x/v2/reply/main"

# Common headers to mimic a browser
BASE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.bilibili.com/",
}


def _build_cookie(sessdata: str | None) -> str | None:
    """Build a minimal Cookie header from SESSDATA."""
    if not sessdata:
        return None
    return f"SESSDATA={sessdata}"


def _ensure_https(url: str) -> str:
    """Convert //-prefixed URL to https://."""
    if url.startswith("//"):
        return "https:" + url
    return url


def _format_time(seconds: float) -> str:
    """Format seconds as MM:SS."""
    s = round(seconds)
    m, s = divmod(s, 60)
    return f"{m:02d}:{s:02d}"


# ---------------------------------------------------------------------------
# Subtitle source detection (ported from reference)
# ---------------------------------------------------------------------------

def _detect_source(sub: dict) -> str:
    """Classify a subtitle as 'human', 'ai', or 'unknown'."""
    # type: 0 = human, 1 = AI
    if sub.get("type") == 1:
        return "ai"
    if sub.get("type") == 0:
        return "human"

    # ai_status / ai_type > 0 signals AI
    if sub.get("ai_status", 0) > 0 or sub.get("ai_type", 0) > 0:
        return "ai"

    # Language prefix "ai-"
    lan = (sub.get("lan") or "").lower()
    if lan.startswith("ai-"):
        return "ai"

    # URL hints
    url = (sub.get("subtitle_url") or "").lower()
    if any(k in url for k in ("aisubtitle.hdslb.com", "/ai_subtitle/", "/aisubtitle/")):
        return "ai"

    # Boolean-like flags
    for field in ("is_ai", "is_ai_subtitle", "is_machine"):
        v = sub.get(field)
        if v is True or v == "true" or v == 1:
            return "ai"

    # If all boolean flags are explicitly false, it's human
    bool_flags = []
    for field in ("is_ai", "is_ai_subtitle", "is_machine"):
        v = sub.get(field)
        if v is not None:
            bool_flags.append(v)
    if bool_flags and all(
        v is False or v == "false" or v == 0 for v in bool_flags
    ):
        return "human"

    # Check source field directly
    raw_source = sub.get("source")
    if raw_source in ("human", "ai"):
        return raw_source

    return "unknown"


# ---------------------------------------------------------------------------
# Default subtitle selection (ported from reference)
# ---------------------------------------------------------------------------

def _pick_default_subtitle(subtitles: list[SubtitleInfo]) -> SubtitleInfo | None:
    """Select the best subtitle: human-zh > human-any > unknown-zh > unknown-any > zh-any > first."""
    if not subtitles:
        return None

    human_zh = next(
        (s for s in subtitles if s.lan == "zh-CN" and s.source == "human"), None
    )
    human_any = next((s for s in subtitles if s.source == "human"), None)
    unknown_zh = next(
        (s for s in subtitles if s.lan == "zh-CN" and s.source == "unknown"), None
    )
    unknown_any = next((s for s in subtitles if s.source == "unknown"), None)
    zh_any = next((s for s in subtitles if s.lan == "zh-CN"), None)

    return human_zh or human_any or unknown_zh or unknown_any or zh_any or subtitles[0]


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class BilibiliClient:
    """Async HTTP client for the Bilibili subtitle API chain."""

    def __init__(self, sessdata: str | None = None):
        cookie = _build_cookie(sessdata)
        headers = {**BASE_HEADERS}
        if cookie:
            headers["Cookie"] = cookie

        self._client = httpx.AsyncClient(headers=headers, timeout=30.0)

    async def close(self) -> None:
        await self._client.aclose()

    async def _get_json(self, url: str, check_code: bool = True, **kwargs) -> dict:
        """GET a URL and return parsed JSON, raising BilibiliError on failure.

        Args:
            url: The URL to GET.
            check_code: If True, require response['code'] == 0 (B站 API convention).
                        Set False for CDN resources that don't have a code field.
        """
        try:
            resp = await self._client.get(url, **kwargs)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise BilibiliError(
                f"HTTP {e.response.status_code} from {url}"
            ) from e
        except httpx.RequestError as e:
            raise BilibiliError(f"Request failed ({url}): {e}") from e

        data: dict = resp.json()
        if check_code:
            code = data.get("code", -1)
            if code != 0:
                msg = data.get("message", "unknown error")
                raise BilibiliError(msg, code=code)
        return data

    # ------------------------------------------------------------------
    # Step 1: video info (BVID → aid + cid)
    # ------------------------------------------------------------------

    async def get_video_info(self, bvid: str, page: int = 1) -> VideoInfo:
        """Fetch video metadata from the view API."""
        bvid = bvid.strip()
        if not re.match(r"^BV[0-9a-zA-Z]+$", bvid):
            raise BilibiliError(f"Invalid BVID: {bvid}")

        data = await self._get_json(
            BILIBILI_VIEW_URL,
            params={"bvid": bvid},
        )
        vd = data.get("data")
        if not vd:
            raise BilibiliError("Video not found or has been deleted")

        aid = vd["aid"]
        cid = vd["cid"]
        title = vd.get("title", "")
        pages = vd.get("pages") or []

        total_pages = len(pages)
        if total_pages > 0:
            idx = page - 1
            if idx < 0 or idx >= total_pages:
                raise BilibiliError(
                    f"Page {page} out of range (video has {total_pages} pages)"
                )
            page_info = pages[idx]
            cid = page_info.get("cid", cid)
            page_title = page_info.get("part", title)
        else:
            page_title = title

        # The view API may carry a subtitle.list hint for source detection
        subtitle_hint_list = vd.get("subtitle", {}).get("list") or []

        return VideoInfo(
            bvid=bvid,
            aid=aid,
            cid=cid,
            title=title,
            page=page,
            total_pages=total_pages or 1,
            page_title=page_title,
            subtitle_list=subtitle_hint_list,
        )

    # ------------------------------------------------------------------
    # Step 2: subtitle list (aid + cid → subtitle tracks)
    # ------------------------------------------------------------------

    async def get_subtitle_list(self, aid: int, cid: int) -> list[dict]:
        """Fetch raw subtitle track metadata from wbi/v2."""
        # Acquire wbi mixin key and sign
        mixin_key = await get_mixin_key(self._client)
        params = sign_params({"aid": str(aid), "cid": str(cid)}, mixin_key)

        data = await self._get_json(BILIBILI_PLAYER_URL, params=params)
        player_data = data.get("data") or {}
        subtitle = player_data.get("subtitle") or {}
        raw_list: list[dict] = subtitle.get("subtitles") or []
        return raw_list

    def _enrich_subtitle_list(
        self, subtitle_infos: list[SubtitleInfo], hint_list: list[dict]
    ) -> list[SubtitleInfo]:
        """Attach source hints from the view API's subtitle.list to the wbi result."""
        # Build a lookup from hint keys → hint entry
        hint_map: dict[str, dict] = {}
        for item in hint_list:
            for key in (
                str(item.get("id", "")),
                str(item.get("id_str", "")),
                f"{item.get('lan','')}|{item.get('type','')}",
                str(item.get("lan", "")),
            ):
                if key:
                    hint_map[key] = item

        for si in subtitle_infos:
            for key in (
                si.id,
                f"{si.lan}|{si.type}",
                si.lan,
            ):
                hint = hint_map.get(key)
                if hint and si.source == "unknown":
                    si.source = _detect_source(hint)
                    break

        return subtitle_infos

    def _process_subtitle_infos(
        self, raw_list: list[dict], hint_list: list[dict]
    ) -> list[SubtitleInfo]:
        """Detect source and sort (human-first) from raw subtitle metadata."""
        infos = [
            SubtitleInfo(
                id=str(sub.get("id_str") or sub.get("id", "")),
                lan=sub.get("lan", ""),
                lan_doc=sub.get("lan_doc", sub.get("lan", "")),
                source=_detect_source(sub),
                subtitle_url=_ensure_https(sub.get("subtitle_url", "")),
                type=sub.get("type", 0),
                ai_status=sub.get("ai_status", 0),
                ai_type=sub.get("ai_type", 0),
            )
            for sub in raw_list
        ]

        # Enrich with view API hints
        infos = self._enrich_subtitle_list(infos, hint_list)

        # Sort: human < unknown < ai (preserve original order within groups)
        source_order = {"human": 0, "unknown": 1, "ai": 2}
        infos.sort(key=lambda s: source_order.get(s.source, 1))
        return infos

    # ------------------------------------------------------------------
    # Step 3: fetch subtitle content from CDN
    # ------------------------------------------------------------------

    async def get_subtitle_content(self, subtitle_url: str) -> list[SubtitleLine]:
        """Fetch and parse the subtitle JSON from the CDN URL."""
        data = await self._get_json(subtitle_url, check_code=False)
        body: list[dict] = data.get("body") or []
        return [
            SubtitleLine(
                from_sec=float(item.get("from", 0)),
                to_sec=float(item.get("to", 0)),
                content=str(item.get("content", "")),
                time=_format_time(float(item.get("from", 0))),
            )
            for item in body
        ]

    # ------------------------------------------------------------------
    # Watch Later ("稍后再看")
    # ------------------------------------------------------------------

    def _format_duration(self, seconds: float) -> str:
        """Format duration seconds as HH:MM:SS."""
        if seconds < 0:
            seconds = 0
        s = round(seconds)
        h, remainder = divmod(s, 3600)
        m, sec = divmod(remainder, 60)
        return f"{h:02d}:{m:02d}:{sec:02d}"

    async def get_watch_later(self, max_results: int | None = None) -> list[WatchLaterItem]:
        """Fetch all items from the user's "稍后再看" (Watch Later) list.

        Auto-paginates until the list is exhausted, then returns all items.

        Args:
            max_results: Optional cap on the number of results returned.

        Returns:
            List of WatchLaterItem objects.
        """
        all_items: list[WatchLaterItem] = []
        pn = 1

        while True:
            data = await self._get_json(
                BILIBILI_TOVIEW_URL,
                params={"pn": pn},
            )
            page_data = data.get("data") or {}
            items: list[dict] = page_data.get("list") or []

            for item in items:
                duration_sec = float(item.get("duration", 0))
                owner: dict = item.get("owner") or {}
                all_items.append(WatchLaterItem(
                    bvid=str(item.get("bvid", "")),
                    aid=int(item.get("aid", 0)),
                    title=str(item.get("title", "")),
                    duration=self._format_duration(duration_sec),
                    owner_name=str(owner.get("name", "")),
                    stat=item.get("stat") or {},
                ))

            # Check if we should stop paginating
            if max_results is not None and len(all_items) >= max_results:
                all_items = all_items[:max_results]
                break

            total = page_data.get("page", {}).get("count", 0)
            if pn * 20 >= total or not items:
                break

            pn += 1

        return all_items

    # ------------------------------------------------------------------
    # Comments
    # ------------------------------------------------------------------

    def _parse_comment(self, reply: dict) -> CommentInfo:
        """Parse a single comment (or sub-reply) from the API response.

        Called recursively for embedded sub-replies.
        """
        member: dict = reply.get("member") or {}
        content: dict = reply.get("content") or {}
        sub_replies: list[dict] = reply.get("replies") or []

        return CommentInfo(
            rpid=str(reply.get("rpid", "")),  # 评论 ID
            mid=int(reply.get("mid", 0)),  # 评论者 UID
            uname=str(member.get("uname", "")),  # 评论者昵称
            content=str(content.get("message", "")),  # 评论正文
            ctime=int(reply.get("ctime", 0)),  # 发布时间（Unix 时间戳）
            like=int(reply.get("like", 0)),  # 点赞数
            reply_count=int(reply.get("rcount", 0)),  # 子回复数量
            replies=[self._parse_comment(r) for r in sub_replies],  # 内嵌子回复（最多 3 条）
        )

    async def get_comments(
        self, bvid: str, sort: str = "hot", max_results: int | None = 20
    ) -> CommentResult:
        """Fetch all comments for a video.

        Auto-paginates via cursor-based pagination until exhausted.

        Args:
            bvid: Video BV ID.
            sort: Sort order — "hot" (默认，热度) or "time" (最新).
            max_results: Optional cap on the number of results returned.

        Returns:
            CommentResult with video metadata and all comments.

        Raises:
            BilibiliError: If video not found, comments disabled, or Cookie missing.
        """
        sort_mode = 3 if sort == "hot" else 2  # hot=3, time=2

        video = await self.get_video_info(bvid)
        all_comments: list[CommentInfo] = []
        next_cursor: int = 0  # cursor-based pagination: 0 = first page

        while True:
            params = {
                "oid": video.aid,
                "type": 1,
                "mode": sort_mode,
                "next": next_cursor,
            }
            data = await self._get_json(BILIBILI_COMMENT_URL, params=params)

            page_data: dict = data.get("data") or {}
            replies: list[dict] = page_data.get("replies") or []

            for reply in replies:
                all_comments.append(self._parse_comment(reply))

            # Cap at max_results if set
            if max_results is not None and len(all_comments) >= max_results:
                all_comments = all_comments[:max_results]
                break

            # Cursor-based pagination: next=0 means no more pages
            cursor: dict = page_data.get("cursor") or {}
            next_cursor = cursor.get("next", 0)
            if next_cursor == 0 or not replies:
                break

        return CommentResult(
            bvid=video.bvid,  # 视频 BV 号
            aid=video.aid,  # 视频 AV 号
            title=video.title,  # 视频标题
            sort=sort,  # 排序方式
            total_comments=len(all_comments),  # 评论总数
            comments=all_comments,
        )

    # ------------------------------------------------------------------
    # High-level combined API
    # ------------------------------------------------------------------

    async def fetch_subtitle_list(
        self, bvid: str, page: int = 1
    ) -> tuple[VideoInfo, list[SubtitleInfo]]:
        """Fetch video info + subtitle track list (tool: get_subtitle_list)."""
        video = await self.get_video_info(bvid, page)
        raw = await self.get_subtitle_list(video.aid, video.cid)
        # If view API shows subtitles exist but wbi/v2 returned none,
        # it's almost certainly a missing-Cookie issue.
        if not raw and video.subtitle_list:
            raise BilibiliError(
                f"Video has {len(video.subtitle_list)} subtitle(s) but the API "
                "requires login to retrieve them. "
                "Set SESSDATA in .env file or MCP config env."
            )
        infos = self._process_subtitle_infos(raw, video.subtitle_list)
        return video, infos

    async def fetch_subtitle(
        self, bvid: str, page: int = 1, lan: str | None = None, source: str | None = None
    ) -> SubtitleResult:
        """Fetch video info + best subtitle content (tool: get_subtitle).

        Args:
            bvid: Video BV ID.
            page: Episode/page number (1-based).
            lan: If provided, filter subtitles by language code (e.g. 'zh-CN').
            source: If provided, filter by source ('human' / 'ai' / 'unknown').

        Returns:
            SubtitleResult with metadata and all subtitle lines.
        """
        video, infos = await self.fetch_subtitle_list(bvid, page)

        # Apply filters
        candidates = infos
        if lan:
            candidates = [s for s in candidates if s.lan == lan]
        if source:
            candidates = [s for s in candidates if s.source == source]

        if not candidates:
            details = []
            if lan:
                details.append(f"lan={lan}")
            if source:
                details.append(f"source={source}")
            raise BilibiliError(
                f"No subtitle matching {' & '.join(details)} (video has {len(infos)} tracks)"
            )

        # Pick default if no filter applied
        selected = _pick_default_subtitle(candidates) if not (lan or source) else candidates[0]

        lines = await self.get_subtitle_content(selected.subtitle_url)
        return SubtitleResult(
            bvid=video.bvid,
            page=video.page,
            title=video.page_title,
            lan=selected.lan,
            lan_doc=selected.lan_doc,
            source=selected.source,
            total_lines=len(lines),
            lines=lines,
        )
