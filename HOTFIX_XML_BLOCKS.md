# XML Block Hotfix

MA3 can fail to load large `FileContent/Block Base64` attribute values reliably.
This version uses small Base64 blocks (`XML_BLOCK_SIZE = 512`) for embedded XML output.

Use:

```bash
python3 tools/build.py --xml-mode embedded
```

Expected output:

```text
dist/DeskLock.xml
~/MALightingTechnology/gma3_library/datapools/plugins/jl_desklock/DeskLock.xml
```

Import in MA3:

```text
Delete Plugin 1 /NC
Import "jl_desklock/DeskLock.xml" At Plugin 1 /NoConfirmation
Call Plugin 1
```
