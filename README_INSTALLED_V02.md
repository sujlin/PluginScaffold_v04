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
