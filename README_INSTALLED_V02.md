# MA3 Lua Plugin Scaffold v0.2 installed-default

This version keeps embedded XML working, but the default and recommended development workflow is installed mode:

```text
<MA3 root>/gma3_library/datapools/plugins/<pluginSubdir>/<Plugin>.xml
<MA3 root>/gma3_library/datapools/plugins/<pluginSubdir>/<Plugin>.lua
```

- `python3 tools/build.py` builds installed XML + external Lua and writes both to the MA3 plugin library.
- `python3 tools/build.py --local` only writes `dist/<Plugin>.xml` and `dist/<Plugin>.lua`.
- `python3 tools/build.py --xml-mode embedded` still generates a single XML with `FileContent` blocks.
- embedded FileContent blocks are encoded from 1024 raw-byte chunks, matching MA3 export behavior.
- `python3 tools/build.py --decode dist/<Plugin>.xml` decodes embedded XML back to Lua for verification.

MA3 import example:

```text
Delete Plugin 1 /NC
Import "jl_desklock/DeskLock.xml" At Plugin 1 /NoConfirmation
Call Plugin 1
```

Installed reload test:

1. Import XML once.
2. Edit `src/app.lua`.
3. Run `python3 tools/build.py`.
4. In MA3 run `ReloadAllPlugins`.
5. `Call Plugin 1` and confirm the new log appears.


# MA3 Lua 插件脚手架 v0.2 默认安装模式

此版本保留了嵌入式 XML 的功能，但默认且推荐的开发工作流程是使用安装模式：

```text

<MA3 根目录>/gma3_library/datapools/plugins/<pluginSubdir>/<Plugin>.xml

<MA3 根目录>/gma3_library/datapools/plugins/<pluginSubdir>/<Plugin>.lua

```

- `python3 tools/build.py` 会构建已安装的 XML 和外部 Lua，并将两者写入 MA3 插件库。

- `python3 tools/build.py --local` 只会写入 `dist/<Plugin>.xml` 和 `dist/<Plugin>.lua`。

- `python3 tools/build.py --xml-mode embedded` 仍然会生成一个包含 `FileContent` 块的 XML 文件。

- 嵌入式 FileContent 块由 1024 字节的原始数据块编码而成，与 MA3 的导出行为一致。

- `python3 tools/build.py --decode dist/<Plugin>.xml` 将嵌入的 XML 解码回 Lua 代码以进行验证。

MA3 导入示例：

```text
删除插件 1 /NC

在插件 1 处导入 "jl_desklock/DeskLock.xml" /NoConfirmation

调用插件 1

```

已安装插件的重新加载测试：

1. 导入一次 XML 文件。

2. 编辑 `src/app.lua` 文件。

3. 运行 `python3 tools/build.py`。

4. 在 MA3 中运行 `ReloadAllPlugins`。

5. 调用 `Call Plugin 1` 并确认新日志出现。