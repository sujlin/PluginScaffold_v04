
# MA3 Lua 插件脚手架 v0.4 使用说明文档（基于上传压缩包内容）

## 1. 脚手架目录结构

```
MA3LuaPluginScaffold_v04/
├─ templates/
│  └─ basic/
│     ├─ src/
│     ├─ ma3lib/
│     ├─ vendor/
│     ├─ assets/
│     └─ config/plugin.json
├─ tools/
│  ├─ new_plugin.py
│  ├─ migrate.py
├─ README.md
└─ LICENSE.txt
```

说明：

- templates/basic/：新项目模板，包括 src/、ma3lib/、vendor/、assets/、plugin.json
- tools/：脚手架工具，负责创建新项目、迁移、构建和生成文档
- README.md / LICENSE.txt：说明与授权

## 2. 新建项目流程

1. 执行 new_plugin.py 创建新项目：

```bash
python3 tools/new_plugin.py MyPlugin --display-name "JL MyPlugin" --plugin-subdir jl_myplugin --output /path/to/projects
```

- 复制 templates/basic 到目标路径
- 生成 src/、ma3lib/、vendor/、tools/、config/、assets/ 等目录
- 默认包含 Hello MA3 Lua 示例
- assets/images/ 中包含模板默认图片

2. 构建项目：

```bash
cd /path/to/projects/MyPlugin
python3 tools/build.py
```

- 生成 Lua + XML
- assets/images 中默认图片生成 UserImage + Appearance
- 占位符 {{PLUGIN_NAME}} 和 {{DISPLAY_NAME}} 替换为项目实际值

3. 生成中文 API 文档：

```bash
python3 tools/docgen.py
```

- 输出到 docs/API.md
- 扫描 src/、ma3lib/、vendor/ 的 Lua 注释
- 支持中文注释

## 3. 老项目迁移流程

1. 使用 migrate.py 增量迁移老项目：

```bash
python3 tools/migrate.py /path/to/OldProject
```

- 默认覆盖 tools/ 文件
- ma3lib/、vendor/、assets/、demo/ 等新增文件增量复制
- src/ 业务代码不覆盖
- plugin.json 新字段递归合并模板默认值
- scaffoldVersion 自动更新
- 中文迁移报告生成在 docs/MIGRATION.md

2. 查看迁移报告：

```bash
cat /path/to/OldProject/docs/MIGRATION.md
```

- 显示新增字段、默认值和需要用户手动修改的必填字段

3. 修改必填字段后构建：

```bash
cd /path/to/OldProject
python3 tools/build.py
```

## 4. 占位符说明

| 占位符 | 含义 |
|---------|-----|
| {{PLUGIN_NAME}} | 对应项目 config["name"] |
| {{DISPLAY_NAME}} | 对应项目 config["displayName"] |

- build.py 构建时自动替换
- file 字段保持原值，不支持占位符

## 5. assets / Appearance 处理

- assets/images 下资源生成 UserImage + Appearance
- useAsPluginAppearance 为 true 的生成插件图标 Appearance
- build.py 使用模板配置生成 XML

## 6. 脚手架迭代策略

- tools/ 文件默认覆盖
- 模板新增文件增量迁移到老项目
- plugin.json 增量合并模板字段
- src/ 业务代码不覆盖
- scaffoldVersion 记录脚手架版本
- 中文迁移报告便于用户操作

## 7. 建议实践

- 更新脚手架模板后，对老项目执行 migrate.py
- 检查迁移报告并修改必填字段
- 执行 build.py 生成最新 Lua + XML
- docgen.py 可随时生成 API 文档
