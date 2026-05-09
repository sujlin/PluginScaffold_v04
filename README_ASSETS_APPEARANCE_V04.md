# MA3 Lua Plugin Scaffold v0.4 - Assets / Appearance Support

## 状态

v0.4 在 v0.3 hello starter 基础上新增图片资源打包：

```text
assets/images/*.png
        ↓
config/plugin.json -> assets.images
        ↓
build.py
        ↓
DeskLock.xml 内生成 DependencyExport / Appearance / UserImage / FileContent
```

默认仍然是 installed 模式：

```text
<plugin>.xml + <plugin>.lua
```

`embedded` 模式继续保留，Lua 可以包进 XML；图片资源始终写进 XML。

## 新项目图片目录

```text
MyPlugin/
├─ assets/
│  └─ images/
│     ├─ plugin_icon.png
│     └─ lock_screen.png
```

## plugin.json 配置

```json
{
  "assets": {
    "images": [
      {
        "name": "MyPlugin_Icon",
        "file": "assets/images/plugin_icon.png",
        "appearanceName": "JL MyPlugin Icon",
        "useAsPluginAppearance": true,
        "imageMode": "Crop",
        "backColor": { "r": 25, "g": 25, "b": 30, "alpha": 255 }
      },
      {
        "name": "MyPlugin_LockScreen",
        "file": "assets/images/lock_screen.png",
        "appearanceName": "JL MyPlugin Lock Screen",
        "useAsPluginAppearance": false,
        "imageMode": "Stretch",
        "backColor": { "r": 0, "g": 0, "b": 0, "alpha": 255 }
      }
    ]
  }
}
```

字段说明：

```text
name                    MA3 MediaPool Image / UserImage 名称
file                    项目内图片路径
appearanceName          MA3 Appearance 名称
useAsPluginAppearance   是否把这个 Appearance 赋给 UserPlugin
imageMode               Crop / Stretch 等 MA3 Appearance 图片模式
backColor               Appearance 背景色
```

## XML 生成结构

```text
UserPlugin Appearance="JL MyPlugin Icon"
├─ DependencyExport
│  └─ Dependency Address="ShowData.Appearances.'JL MyPlugin Icon'"
│     └─ Appearance MediaFileName="CUSTOM/plugin_icon.png"
│        └─ DependencyExport
│           └─ Dependency Address="ShowData.MediaPools.Images.'MyPlugin_Icon'"
│              └─ UserImage FileName="plugin_icon.png"
│                 └─ FileContent
│                    └─ Block Base64="..."
└─ ComponentLua Installed="Yes" FileName="MyPlugin.lua" FilePath="jl_myplugin"
```

图片和 Lua embedded FileContent 都使用 grandMA3 导出风格：**原始 bytes 每 1024 bytes 一块，每块单独 Base64**。

## 使用

创建新插件：

```bash
python3 tools/new_plugin.py MyPlugin \
  --display-name "JL MyPlugin" \
  --plugin-subdir jl_myplugin \
  --output /Users/oreo/Documents/MA3Projects
```

构建：

```bash
cd /Users/oreo/Documents/MA3Projects/MyPlugin
python3 tools/build.py
```

输出：

```text
~/MALightingTechnology/gma3_library/datapools/plugins/jl_myplugin/MyPlugin.xml
~/MALightingTechnology/gma3_library/datapools/plugins/jl_myplugin/MyPlugin.lua
```

MA3 导入：

```text
Import "jl_myplugin/MyPlugin.xml" At Plugin 1 /NoConfirmation
Call Plugin 1
```

如果只改 Lua，后续可以：

```text
ReloadAllPlugins
Call Plugin 1
```

如果改了图片，建议删除旧插件后重新 Import XML；图片资源已经写入 showfile，ReloadAllPlugins 通常只刷新 Lua。
