# `cli.py`

`src/bilibili_subtitle/cli.py` 提供 `bilibili-subtitle` 命令行接口。它负责解析参数、调用 `BilibiliClient`，并将结果输出为 JSON。

## 运行方式

安装项目后使用：

```shell
bilibili-subtitle <command> [options]
```

`pyproject.toml` 将该命令映射到：

```python
bilibili_subtitle.cli:main
```

## 命令

| 命令 | 功能 | 常用选项 |
| --- | --- | --- |
| `list BVID` | 列出字幕轨道 | `-p/--page` |
| `get BVID` | 获取字幕正文 | `-p/--page`、`-l/--lan`、`-s/--source` |
| `comments BVID` | 获取视频评论 | `-s/--sort`、`-n/--max-results` |
| `toview` | 获取“稍后再看” | `-n/--max-results` |
| `remove BVID` | 删除一条“稍后再看”记录 | 无 |
| `clear` | 清空“稍后再看” | 无 |

例如：

```shell
bilibili-subtitle list BVxxxxxxxxxx
bilibili-subtitle get BVxxxxxxxxxx -p 2 -l zh-CN
bilibili-subtitle comments BVxxxxxxxxxx -s time -n 50
```

## 配置

模块从项目根目录的 `.env` 加载登录信息：

```dotenv
SESSDATA=your_sessdata
BILI_JCT=your_bili_jct
```

- `SESSDATA` 用于访问需要登录的内容。
- `BILI_JCT` 用于删除或清空“稍后再看”等写操作。

## 执行流程

`main()` 使用 `argparse` 创建子命令，再通过 `asyncio.run()` 执行对应的异步函数：

- `cmd_list()`
- `cmd_get()`
- `cmd_comments()`
- `cmd_toview()`
- `cmd_remove()`
- `cmd_clear()`

每个命令都会创建独立的 `BilibiliClient`，并在 `finally` 中关闭客户端。

命令结果写入标准输出。发生 `BilibiliError` 时，错误写入标准错误流，并以状态码 `1` 退出。
