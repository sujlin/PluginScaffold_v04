# MA3 Lua Plugin Scaffold

Python-only scaffold and bundler for grandMA3 Lua plugins.

## Build modes

The builder is XML-first.

- `installed` mode: writes `Plugin.xml` plus external `Plugin.lua`. The XML defines `UserPlugin/ComponentLua` and the component has `FileName`, `FilePath`, and `Installed="Yes"`. This is the recommended development mode because `ReloadAllPlugins` reloads the external Lua file.
- `embedded` mode: writes one XML file with `ComponentLua/FileContent/Block Base64="..."`. No external Lua file is required.

## Commands

```bash
python3 tools/build.py --local
python3 tools/build.py
python3 tools/build.py --ma3-version 2.3.2
python3 tools/build.py --xml-mode embedded
```

Default MA3 output path:

```text
~/MALightingTechnology/gma3_library/datapools/plugins/<pluginSubdir>/<xmlFile>
~/MALightingTechnology/gma3_library/datapools/plugins/<pluginSubdir>/<luaFile>   # installed mode only
```

## Config

See `config/plugin.json`:

```json
"ma3": {
  "pluginSubdir": "jl_desklock",
  "xmlMode": "installed",
  "xmlFile": "DeskLock.xml",
  "luaFile": "DeskLock.lua",
  "componentFileName": "DeskLock.lua",
  "componentFilePath": "jl_desklock",
  "installed": true,
  "dataVersion": "2.3.2.0"
}
```
