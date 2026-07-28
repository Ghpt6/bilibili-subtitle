"""Import Bilibili cookies from an authorised Chromium DevTools session.

The module deliberately does not read or decrypt Chromium's cookie database.
Chrome and Edge must already be running with remote debugging enabled, and the
browser remains in charge of showing/handling any user consent prompt.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import httpx
import websockets

from .bilibili import BASE_HEADERS

BILIBILI_NAV_URL = "https://api.bilibili.com/x/web-interface/nav"
_COOKIE_HOST = "api.bilibili.com"
_COOKIE_PATH = "/x/web-interface/nav"
_COOKIE_NAMES = ("SESSDATA", "bili_jct")
_ENV_NAMES = ("SESSDATA", "BILI_JCT")
_IMPORT_LOCK = asyncio.Lock()


@dataclass(frozen=True)
class BrowserSpec:
    key: str
    name: str
    user_data_dir: Path
    fallback_port: int


@dataclass(frozen=True)
class DebugEndpoint:
    browser: BrowserSpec
    profile: str
    websocket_url: str


@dataclass(frozen=True)
class CookiePair:
    sessdata: str
    bili_jct: str


@dataclass(frozen=True)
class AccountInfo:
    uid: int
    name: str


class BrowserConnectionError(Exception):
    """A safe-to-display browser connection failure."""


class ValidationUnavailable(Exception):
    """The login state could not be determined reliably."""


def _browser_specs() -> list[BrowserSpec]:
    local_app_data = Path(
        os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")
    )
    return [
        BrowserSpec(
            key="chrome",
            name="Chrome",
            user_data_dir=local_app_data / "Google" / "Chrome" / "User Data",
            fallback_port=9222,
        ),
        BrowserSpec(
            key="edge",
            name="Edge",
            user_data_dir=local_app_data / "Microsoft" / "Edge" / "User Data",
            fallback_port=9223,
        ),
    ]


def _profile_sort_key(profile: str) -> tuple[int, int, str]:
    """Sort Default, Profile 1..N, then any other profile names."""
    if profile == "Default":
        return (0, 0, profile)
    match = re.fullmatch(r"Profile (\d+)", profile)
    if match:
        return (1, int(match.group(1)), profile)
    return (2, 0, profile.casefold())


def _profile_display_name(user_data_dir: Path, profile_dir: str) -> str:
    """Return Chromium's display name while keeping the directory deterministic."""
    try:
        state = json.loads((user_data_dir / "Local State").read_text(encoding="utf-8"))
        info = state.get("profile", {}).get("info_cache", {}).get(profile_dir, {})
        display_name = str(info.get("name") or "").strip()
    except (OSError, UnicodeError, json.JSONDecodeError, AttributeError):
        display_name = ""
    if display_name and display_name != profile_dir:
        return f"{profile_dir} ({display_name})"
    return profile_dir


def _last_used_profile(user_data_dir: Path) -> str:
    try:
        state = json.loads((user_data_dir / "Local State").read_text(encoding="utf-8"))
        profile = str(state.get("profile", {}).get("last_used") or "Default")
    except (OSError, UnicodeError, json.JSONDecodeError, AttributeError):
        profile = "Default"
    return _profile_display_name(user_data_dir, profile)


def _read_active_port(path: Path) -> tuple[int, str] | None:
    try:
        lines = path.read_text(encoding="ascii").splitlines()
        port = int(lines[0])
        websocket_path = lines[1].strip()
    except (OSError, UnicodeError, ValueError, IndexError):
        return None
    if not 1 <= port <= 65535 or not websocket_path.startswith("/devtools/browser/"):
        return None
    return port, websocket_path


async def _devtools_info_from_port(port: int) -> tuple[str, str] | None:
    """Resolve a manually configured DevTools HTTP endpoint on loopback."""
    try:
        async with httpx.AsyncClient(timeout=1.0, trust_env=False) as client:
            response = await client.get(f"http://127.0.0.1:{port}/json/version")
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError):
        return None
    url = payload.get("webSocketDebuggerUrl")
    if isinstance(url, str) and url.startswith(
        (f"ws://127.0.0.1:{port}/", f"ws://localhost:{port}/")
    ):
        return url, str(payload.get("Browser") or "")
    return None


async def _discover_endpoints(spec: BrowserSpec) -> list[DebugEndpoint]:
    """Find already-running, user-authorised DevTools endpoints."""
    endpoints: list[DebugEndpoint] = []
    seen_urls: set[str] = set()

    active_port_files: list[tuple[str, Path]] = [
        (
            _last_used_profile(spec.user_data_dir),
            spec.user_data_dir / "DevToolsActivePort",
        )
    ]
    try:
        profile_dirs = sorted(
            (
                path
                for path in spec.user_data_dir.iterdir()
                if path.is_dir()
                and (path.name == "Default" or re.fullmatch(r"Profile \d+", path.name))
            ),
            key=lambda path: _profile_sort_key(path.name),
        )
    except OSError:
        profile_dirs = []
    if profile_dirs:
        active_port_files.extend(
            (
                _profile_display_name(spec.user_data_dir, profile_dir.name),
                profile_dir / "DevToolsActivePort",
            )
            for profile_dir in profile_dirs
        )

    for profile, active_port_file in active_port_files:
        active = _read_active_port(active_port_file)
        if active is None:
            continue
        port, websocket_path = active
        url = f"ws://127.0.0.1:{port}{websocket_path}"
        if url not in seen_urls:
            seen_urls.add(url)
            endpoints.append(DebugEndpoint(spec, profile, url))

    for port in (spec.fallback_port, 9223 if spec.fallback_port == 9222 else 9222):
        fallback = await _devtools_info_from_port(port)
        if fallback is None:
            continue
        fallback_url, product = fallback
        is_edge = "Edg/" in product
        if (spec.key == "edge") != is_edge:
            continue
        if fallback_url not in seen_urls:
            seen_urls.add(fallback_url)
            endpoints.append(DebugEndpoint(spec, "Default", fallback_url))

    return endpoints


async def _cdp_command(
    websocket: Any,
    command_id: int,
    method: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    message: dict[str, Any] = {"id": command_id, "method": method}
    if params:
        message["params"] = params
    await websocket.send(json.dumps(message))

    while True:
        raw = await asyncio.wait_for(websocket.recv(), timeout=10)
        response = json.loads(raw)
        if response.get("id") != command_id:
            continue
        if "error" in response:
            error = response["error"]
            code = (
                error.get("code", "unknown") if isinstance(error, dict) else "unknown"
            )
            raise BrowserConnectionError(f"DevTools command failed (code {code})")
        result = response.get("result")
        if not isinstance(result, dict):
            raise BrowserConnectionError("DevTools returned an invalid response")
        return result


async def _read_endpoint_cookies(
    endpoint: DebugEndpoint,
) -> tuple[str, list[list[dict[str, Any]]]]:
    """Read cookies per accessible browser context over one approved connection."""
    try:
        async with websockets.connect(
            endpoint.websocket_url,
            open_timeout=30,
            close_timeout=2,
            max_size=4 * 1024 * 1024,
        ) as websocket:
            version = await _cdp_command(websocket, 1, "Browser.getVersion")
            product = str(version.get("product") or "")
            if endpoint.browser.key == "chrome" and "Edg/" in product:
                raise BrowserConnectionError("endpoint belongs to Edge")
            if endpoint.browser.key == "edge" and "Edg/" not in product:
                raise BrowserConnectionError("endpoint does not belong to Edge")

            cookie_sets: list[list[dict[str, Any]]] = []
            default_result = await _cdp_command(websocket, 2, "Storage.getCookies")
            default_cookies = default_result.get("cookies")
            if isinstance(default_cookies, list):
                cookie_sets.append(default_cookies)

            contexts_result = await _cdp_command(
                websocket, 3, "Target.getBrowserContexts"
            )
            context_ids = contexts_result.get("browserContextIds") or []
            next_id = 4
            for context_id in context_ids:
                result = await _cdp_command(
                    websocket,
                    next_id,
                    "Storage.getCookies",
                    {"browserContextId": context_id},
                )
                next_id += 1
                cookies = result.get("cookies")
                if isinstance(cookies, list):
                    cookie_sets.append(cookies)
            return product, cookie_sets
    except BrowserConnectionError:
        raise
    except (OSError, TimeoutError, json.JSONDecodeError) as exc:
        raise BrowserConnectionError("could not connect to authorised session") from exc
    except Exception as exc:
        # WebSocket implementations expose several version-specific exception
        # classes; keep their details out of MCP output.
        raise BrowserConnectionError(
            "authorisation was denied or connection failed"
        ) from exc


def _cookie_applies(cookie: dict[str, Any], now: float) -> bool:
    domain = str(cookie.get("domain") or "").lstrip(".").lower()
    path = str(cookie.get("path") or "/")
    expires = cookie.get("expires")
    if not (domain == "bilibili.com" or _COOKIE_HOST.endswith("." + domain)):
        return False
    if path != "/" and not (
        _COOKIE_PATH == path or _COOKIE_PATH.startswith(path.rstrip("/") + "/")
    ):
        return False
    if isinstance(expires, (int, float)) and expires > 0 and expires <= now:
        return False
    return bool(cookie.get("value"))


def _cookie_sort_key(cookie: dict[str, Any]) -> tuple[int, int, str]:
    domain = str(cookie.get("domain") or "").lstrip(".").lower()
    path = str(cookie.get("path") or "/")
    # Prefer the broad, persistent Bilibili cookies that are suitable for .env.
    domain_rank = 0 if domain == "bilibili.com" else 1
    path_rank = 0 if path == "/" else 1
    return (domain_rank, path_rank, domain)


def _extract_cookie_pairs(cookies: list[dict[str, Any]]) -> list[CookiePair]:
    now = time.time()
    matching: dict[str, list[dict[str, Any]]] = {
        name: sorted(
            (
                cookie
                for cookie in cookies
                if cookie.get("name") == name and _cookie_applies(cookie, now)
            ),
            key=_cookie_sort_key,
        )
        for name in _COOKIE_NAMES
    }
    pairs: list[CookiePair] = []
    seen: set[tuple[str, str]] = set()
    for sessdata in matching["SESSDATA"]:
        for bili_jct in matching["bili_jct"]:
            values = (str(sessdata["value"]), str(bili_jct["value"]))
            if values not in seen:
                seen.add(values)
                pairs.append(CookiePair(*values))
    return pairs


async def _validate_cookie_pair(pair: CookiePair) -> AccountInfo | None:
    headers = {
        **BASE_HEADERS,
        "Cookie": f"SESSDATA={pair.sessdata}; bili_jct={pair.bili_jct}",
    }
    try:
        async with httpx.AsyncClient(
            headers=headers, timeout=10.0, follow_redirects=False
        ) as client:
            response = await client.get(BILIBILI_NAV_URL)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise ValidationUnavailable("Bilibili login validation is unavailable") from exc

    if not isinstance(payload, dict):
        raise ValidationUnavailable("Bilibili login validation returned invalid data")
    if payload.get("code") != 0:
        raise ValidationUnavailable("Bilibili login validation returned an API error")
    data = payload.get("data")
    if not isinstance(data, dict) or data.get("isLogin") is not True:
        return None
    try:
        uid = int(data.get("mid"))
    except (TypeError, ValueError):
        return None
    if uid <= 0:
        return None
    return AccountInfo(uid=uid, name=str(data.get("uname") or ""))


def _validate_env_value(value: str) -> None:
    if not value or any(char in value for char in ("\x00", "\r", "\n")):
        raise ValueError("Cookie contains an invalid value")


def _update_env_file(env_path: Path, pair: CookiePair) -> None:
    """Atomically replace only SESSDATA/BILI_JCT while preserving other lines."""
    _validate_env_value(pair.sessdata)
    _validate_env_value(pair.bili_jct)

    try:
        original = env_path.read_text(encoding="utf-8-sig") if env_path.exists() else ""
    except (OSError, UnicodeError) as exc:
        raise OSError("could not read .env") from exc

    newline = "\r\n" if "\r\n" in original else "\n"
    had_trailing_newline = original.endswith(("\r", "\n"))
    lines = original.splitlines()
    replacements = {
        "SESSDATA": f"SESSDATA={pair.sessdata}",
        "BILI_JCT": f"BILI_JCT={pair.bili_jct}",
    }
    found: set[str] = set()
    output: list[str] = []
    assignment = re.compile(r"^\s*(?:export\s+)?(SESSDATA|BILI_JCT)\s*=")
    for line in lines:
        match = assignment.match(line)
        if not match:
            output.append(line)
            continue
        key = match.group(1)
        if key not in found:
            output.append(replacements[key])
            found.add(key)

    if output and len(found) < len(replacements) and output[-1] != "":
        output.append("")
    for key in _ENV_NAMES:
        if key not in found:
            output.append(replacements[key])

    rendered = newline.join(output)
    if output and (had_trailing_newline or not original):
        rendered += newline

    env_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            prefix=f".{env_path.name}.",
            suffix=".tmp",
            dir=env_path.parent,
            delete=False,
        ) as temp_file:
            temp_file.write(rendered)
            temp_file.flush()
            os.fsync(temp_file.fileno())
            temp_path = Path(temp_file.name)
        os.replace(temp_path, env_path)
    except OSError as exc:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise OSError("could not update .env") from exc


def _diagnostic(browser: str, profile: str | None, reason: str) -> dict[str, str]:
    result = {"browser": browser, "reason": reason}
    if profile:
        result["profile"] = profile
    return result


async def import_browser_cookies_to_env(env_path: Path) -> dict[str, Any]:
    """Import the first valid authorised Chrome/Edge Bilibili account."""
    if sys.platform != "win32":
        return {
            "success": False,
            "error": "unsupported_platform",
            "message": "Browser Cookie import currently supports Windows only.",
        }

    async with _IMPORT_LOCK:
        diagnostics: list[dict[str, str]] = []
        for spec in _browser_specs():
            endpoints = await _discover_endpoints(spec)
            if not endpoints:
                diagnostics.append(
                    _diagnostic(spec.name, None, "not_running_or_not_authorised")
                )
                continue

            endpoints.sort(
                key=lambda endpoint: _profile_sort_key(
                    endpoint.profile.split(" (", 1)[0]
                )
            )
            for endpoint in endpoints:
                try:
                    _, cookie_sets = await _read_endpoint_cookies(endpoint)
                except BrowserConnectionError as exc:
                    diagnostics.append(
                        _diagnostic(spec.name, endpoint.profile, str(exc))
                    )
                    continue

                pairs = list(
                    dict.fromkeys(
                        pair
                        for cookies in cookie_sets
                        for pair in _extract_cookie_pairs(cookies)
                    )
                )
                if not pairs:
                    diagnostics.append(
                        _diagnostic(
                            spec.name,
                            endpoint.profile,
                            "missing_or_expired_bilibili_cookies",
                        )
                    )
                    continue

                for pair in pairs:
                    try:
                        account = await _validate_cookie_pair(pair)
                    except ValidationUnavailable as exc:
                        return {
                            "success": False,
                            "error": "validation_unavailable",
                            "message": str(exc),
                            "diagnostics": diagnostics,
                        }
                    if account is None:
                        diagnostics.append(
                            _diagnostic(
                                spec.name,
                                endpoint.profile,
                                "bilibili_account_not_logged_in",
                            )
                        )
                        continue
                    try:
                        _update_env_file(env_path, pair)
                    except (OSError, ValueError) as exc:
                        return {
                            "success": False,
                            "error": "env_write_failed",
                            "message": str(exc),
                            "diagnostics": diagnostics,
                        }
                    return {
                        "success": True,
                        "browser": spec.name,
                        "profile": endpoint.profile,
                        "uid": account.uid,
                        "name": account.name,
                        "env_path": str(env_path.resolve()),
                        "message": "Cookie saved. Restart the MCP server to use it.",
                    }

        return {
            "success": False,
            "error": "no_valid_account",
            "message": "No valid authorised Bilibili account was found.",
            "diagnostics": diagnostics,
        }
