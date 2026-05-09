# MA3 Lua Plugin Scaffold v0.3 - Hello Starter

本版本在 v0.2 installed-default 基础上新增：

1. `templates/basic/src/app.lua` 默认是可运行的 Hello MA3 插件入口。
2. `templates/basic/tools/docgen.py` 已内置，创建新项目后可以直接生成文档。
3. `templates/basic/docs/.gitkeep` 默认创建 docs 目录。
4. `templates/basic/README.md` 已更新为 installed 默认工作流。
5. `tools/new_plugin.py` 创建项目后提示 `python3 tools/build.py` 和 `python3 tools/docgen.py`。

## 创建新项目

```bash
cd /Users/oreo/Documents/ma3_lua_plugin_scaffold
python3 tools/new_plugin.py MyPlugin --display-name "JL MyPlugin" --plugin-subdir jl_myplugin --output /Users/oreo/Documents/MA3Projects
cd /Users/oreo/Documents/MA3Projects/MyPlugin
python3 tools/build.py
```

MA3 中：

```text
Import "jl_myplugin/MyPlugin.xml" At Plugin 1 /NoConfirmation
Call Plugin 1
```

System Monitor 里应该看到：

```text
[JL MyPlugin] Hello MA3!
```

## 生成文档

```bash
python3 tools/docgen.py
```

输出：

```text
docs/API.md
```
