# Hotfix: 1024-byte XML FileContent blocks

MA3 exported plugin XML splits ComponentLua/FileContent into 1024 raw-byte blocks, then Base64-encodes each block.

Previous scaffold versions split the Base64 text into 512-character chunks. MA3 could import only the first block, so the plugin editor showed only the generated header and the Lua chunk had EOF/syntax/no-main errors.

This version chunks raw Lua bytes in 1024-byte blocks and emits `<Block Base64="..." />`, matching observed MA3 export structure.
