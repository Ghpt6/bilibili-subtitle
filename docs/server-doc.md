# `server.py`

`src/bilibili_subtitle/server.py` 创建 FastMCP 服务，将 Bilibili 功能作为 MCP 工具提供给外部客户端。


入口函数为：

```python
def main() -> None:
    mcp.run(transport="stdio")
```

服务名称为 `bilibili-subtitle`。

## MCP 工具

| 工具 | 功能 |
| --- | --- |
| `import_browser_cookies` | 从 Windows Chrome/Edge 的已授权会话导入登录 Cookie |
| `get_subtitle_list` | 获取视频信息和可用字幕轨道 |
| `get_subtitle` | 获取完整字幕内容 |
| `get_comments` | 获取视频评论 |
| `get_watch_later` | 获取“稍后再看”列表 |
| `remove_watch_later` | 删除一条“稍后再看”记录 |
| `clear_watch_later` | 清空“稍后再看”列表 |

工具使用普通字典作为返回值，以便 FastMCP 进行序列化。

## 客户端生命周期

内部异步上下文管理器 `_get_client()` 从环境变量创建 `BilibiliClient`  
而在此之前通过库dotenv加载项目根目录的`.env`文件：

```python
_env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(_env_path)

SESSDATA=your_sessdata
BILI_JCT=your_bili_jct
```

每次工具调用结束后，客户端都会自动关闭：

```python
async with _get_client() as client:
    ...
```

## 实现原理
通过调用`bilibili.py` 中BilibiliClient的底层方法来实现，然后将结果转换为dict，例如：

```python
@mcp.tool()
async def get_subtitle(...):
    async with _get_client() as client:
        result = await client.fetch_subtitle(...)
    return {
            "bvid": result.bvid,
            "page": result.page,
            "title": result.title,
            ....
    }
```
