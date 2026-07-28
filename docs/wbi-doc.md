# `wbi.py`

`src/bilibili_subtitle/wbi.py` 为 Bilibili WBI 接口生成请求签名。目前主要由 `BilibiliClient.get_subtitle_list()` 使用。

## 签名流程

WBI 签名分为三个步骤：

1. 请求 Bilibili 导航接口，取得 `img_url` 和 `sub_url`。
2. 从 URL 提取密钥，并按照固定置换表生成 32 位混合密钥。
3. 对请求参数排序，添加时间戳和 MD5 签名。

## `get_mixin_key()`

```python
await get_mixin_key(
    client: httpx.AsyncClient,
) -> str
```

该方法获取 WBI 原始密钥并生成混合密钥。

内部调用：

- `_fetch_keys()`：请求导航接口并读取两个密钥 URL。
- `_extract_key_from_url()`：从 URL 文件名中提取密钥。
- `_derive_mixin_key()`：按照 `MIXIN_KEY_ENC_TAB` 置换并截取混合密钥。

导航接口未返回密钥时，`_fetch_keys()` 会抛出 `RuntimeError`。

## `sign_params()`

```python
sign_params(
    params: dict,
    mixin_key: str,
) -> dict
```

该方法为查询参数添加：

- `wts`：当前 Unix 时间戳。
- `w_rid`：MD5 请求签名。

方法会直接修改并返回传入的 `params`：

```python
mixin_key = await get_mixin_key(client)
params = sign_params(
    {"aid": "123", "cid": "456"},
    mixin_key,
)
```

调用方应使用返回的参数发起 WBI API 请求。
