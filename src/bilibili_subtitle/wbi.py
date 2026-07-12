"""WBI signing for Bilibili API (wbi/v2 endpoints).

Reference: https://github.com/SocialSisterYi/bilibili-API-collect/blob/master/docs/misc/sign/wbi.md
"""

import hashlib
import os
import time
from urllib.parse import urlencode

import httpx

# Fixed permutation table for mixing the raw key
MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
    37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
    22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 52, 44, 34,
]

NAV_URL = "https://api.bilibili.com/x/web-interface/nav"


def _extract_key_from_url(url: str) -> str:
    """Extract the key from a wbi image URL (filename without extension)."""
    filename = os.path.basename(url)
    return os.path.splitext(filename)[0]


async def _fetch_keys(client: httpx.AsyncClient) -> tuple[str, str]:
    """Fetch img_key and sub_key from Bilibili nav endpoint.

    The nav endpoint returns img_url / sub_url even when not logged in.
    We extract the key from the URL path's filename.
    """
    resp = await client.get(NAV_URL)
    resp.raise_for_status()
    data = resp.json()
    wbi_img = data.get("data", {}).get("wbi_img", {})

    img_url = wbi_img.get("img_url", "")
    sub_url = wbi_img.get("sub_url", "")

    if not img_url or not sub_url:
        raise RuntimeError(
            "Failed to fetch wbi keys: nav response missing img_url / sub_url"
        )

    return _extract_key_from_url(img_url), _extract_key_from_url(sub_url)


def _derive_mixin_key(img_key: str, sub_key: str) -> str:
    """Derive the 32-char mixin key from img_key and sub_key."""
    raw = img_key + sub_key
    return "".join(raw[i] for i in MIXIN_KEY_ENC_TAB if i < len(raw))[:32]


async def get_mixin_key(client: httpx.AsyncClient) -> str:
    """Fetch and derive the mixin key for wbi signing."""
    img_key, sub_key = await _fetch_keys(client)
    return _derive_mixin_key(img_key, sub_key)


def sign_params(params: dict, mixin_key: str) -> dict:
    """Add w_rid and wts to the given params dict (mutated in place).

    Args:
        params: Query parameters dict (will be sorted by key).
        mixin_key: The 32-char mixin key.

    Returns:
        The same dict with w_rid and wts added.
    """
    sorted_params = dict(sorted(params.items()))
    query_string = urlencode(sorted_params)
    params["wts"] = int(time.time())
    sign_string = query_string + mixin_key
    params["w_rid"] = hashlib.md5(sign_string.encode()).hexdigest()
    return params
