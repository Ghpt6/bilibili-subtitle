# `browser_cookies.py`

`src/bilibili_subtitle/browser_cookies.py` 实现 Windows Chrome/Edge Cookie
导入。它只连接浏览器已经开放并经用户授权的 DevTools 会话，不读取或解密
Chromium 的 Cookie 数据库。

## 导入流程

1. 按 Chrome、Edge 的顺序查找 `DevToolsActivePort`。
2. 同时检查回环地址上的约定端口 `9222`、`9223`，并根据 DevTools 返回
   的浏览器产品名区分 Chrome 与 Edge。
3. 连接已授权的 DevTools WebSocket，通过 `Storage.getCookies` 读取当前
   可访问浏览器上下文。
4. 只保留可发送到 Bilibili 登录状态接口、尚未过期的 `SESSDATA` 与
   `bili_jct`。
5. 使用 `https://api.bilibili.com/x/web-interface/nav` 验证候选账号。
6. 将第一个满足 `code == 0`、`isLogin == true`、`mid > 0` 的候选写入
   项目根目录 `.env`。

只会处理当前运行且已授权的配置。工具不会启动或关闭浏览器，也不会尝试
绕过 Chrome/Edge 的应用绑定加密。

## 配置顺序

浏览器优先级固定为：

1. Chrome
2. Edge

同一浏览器中的配置顺序固定为：

1. `Default`
2. `Profile 1`
3. `Profile 2`
4. 其他配置

浏览器仅开放一个活动配置时，只检查该配置。

## `.env` 写入

写入函数 `_update_env_file()`：

- 只替换 `SESSDATA` 与 `BILI_JCT`；
- 在同一目录生成临时文件，再通过 `os.replace()` 原子替换；
- 不修改当前进程的 `os.environ`，因此导入成功后必须重启 MCP 服务。

## 返回值与错误

成功结果只包含浏览器、配置、Bilibili UID、昵称、`.env` 路径和重启提示，不会返回 Cookie 明文。

失败结果使用 `success: false` 和稳定的 `error` 值：

| 错误 | 含义 |
| --- | --- |
| `unsupported_platform` | 当前系统不是 Windows |
| `no_valid_account` | 没有找到已授权且有效的账号 |
| `validation_unavailable` | 登录接口超时、网络错误或返回异常 |
| `env_write_failed` | 无法安全更新 `.env` |

`diagnostics` 仅包含脱敏后的浏览器、配置和失败原因。
