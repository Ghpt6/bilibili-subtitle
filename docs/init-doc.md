# `__init__.py`

`src/bilibili_subtitle/__init__.py` 是 `bilibili_subtitle` 包的初始化模块。

目前该模块仅定义包版本：

```python
__version__ = "0.1.0"
```

其他模块可以直接读取版本号：

```python
from bilibili_subtitle import __version__

print(__version__)
```
