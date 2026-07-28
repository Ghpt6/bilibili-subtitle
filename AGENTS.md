# 项目简介

`bilibili-subtitle` 是一个基于 Python 3.10+、FastMCP 和 httpx 的 Bilibili 工具，同时提供 MCP 服务和命令行接口。  
项目支持获取视频字幕轨道与字幕内容、读取视频评论，以及查询、删除或清空“稍后再看”列表。

## 源码结构

主要源码位于 `src/bilibili_subtitle/`：

- `__init__.py`：定义包的基本信息和版本号。
- `bilibili.py`：封装 Bilibili API 客户端及字幕、评论、“稍后再看”等核心业务逻辑。
- `cli.py`：提供命令行入口，负责参数解析、调用业务逻辑和格式化输出结果。
- `server.py`：创建 FastMCP 服务并定义对外提供的 MCP 工具。
- `types.py`：定义项目使用的数据模型和统一异常类型。
- `wbi.py`：实现 WBI 密钥获取和请求参数签名等鉴权辅助逻辑。


## doc

源码相关文档位于`docs/`:

- docs/bilibili-doc.md
- docs/cli-doc.md
- docs/server-doc.md
- docs/types-doc.md
- docs/wbi-doc.md
- docs/init-doc.md
- docs/browser-cookies-doc.md