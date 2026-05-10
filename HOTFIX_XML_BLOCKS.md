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


# XML 块热修复

MA3 可能无法可靠地加载较大的 `FileContent/Block Base64` 属性值。

此版本使用较小的 Base64 块（`XML_BLOCK_SIZE = 512`）进行嵌入式 XML 输出。

使用方法：

```bash

python3 tools/build.py --xml-mode embedded

```

预期输出：

```text

dist/DeskLock.xml

~/MALightingTechnology/gma3_library/datapools/plugins/jl_desklock/DeskLock.xml

```

在 MA3 中导入：

```text

Delete Plugin 1 /NC

Import "jl_desklock/DeskLock.xml" At Plugin 1 /NoConfirmation

Call Plugin 1

```