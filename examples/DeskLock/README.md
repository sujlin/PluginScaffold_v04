# JL DeskLock

这是由 MA3 Lua Plugin Scaffold 生成的插件项目。默认入口是一个可运行的 **Hello MA3** 示例。

## 1. 构建

在项目根目录执行：

```bash
python3 tools/build.py
```

默认构建模式是 `installed`，会生成并复制两个文件到 MA3 插件库：

```text
~/MALightingTechnology/gma3_library/datapools/plugins/jl_desklock/DeskLock.xml
~/MALightingTechnology/gma3_library/datapools/plugins/jl_desklock/DeskLock.lua
```

同时会生成本地备份：

```text
dist/DeskLock.xml
dist/DeskLock.lua
```

只生成本地文件，不写入 MA3：

```bash
python3 tools/build.py --local
```

生成 embedded 单 XML 备用包：

```bash
python3 tools/build.py --xml-mode embedded
```

## 2. 第一次导入 MA3

在 MA3 命令行执行：

```text
Import "jl_desklock/DeskLock.xml" At Plugin 1 /NoConfirmation
Call Plugin 1
```

成功时，System Monitor 里应该看到：

```text
[JL DeskLock] Hello MA3!
```

## 3. 日常开发

修改 `src/app.lua` 或其他模块后：

```bash
python3 tools/build.py
```

然后在 MA3 里：

```text
ReloadAllPlugins
Call Plugin 1
```

## 4. 生成 API 文档

直接执行：

```bash
python3 tools/docgen.py
```

默认输出：

```text
docs/API.md
```

注释可以写中文，例如：

```lua
--- 插件主入口。MA3 执行 Call Plugin 时调用。
---@param ctx table 插件上下文。
function App.Main(ctx, display_handle, argument)
end
```

## 5. 源码结构

```text
src/       当前插件源码
ma3lib/    可复用 MA3 Lua 工具库
vendor/    第三方 Lua 模块
config/    plugin.json
commands/  可选命令说明或 MA3 命令片段
tools/     Python 构建和文档工具
docs/      自动生成或手写文档
build/     构建临时文件
dist/      本地构建产物
```

## 6. 当前入口

主要从这里开始写：

```text
src/app.lua
```

其中：

```text
App.Main     插件被 Call 时运行
App.Cleanup  插件清理时运行
App.Execute  可选事件入口
```
