# Hotfix: 1024-byte XML FileContent blocks

MA3 exported plugin XML splits ComponentLua/FileContent into 1024 raw-byte blocks, then Base64-encodes each block.

Previous scaffold versions split the Base64 text into 512-character chunks. MA3 could import only the first block, so the plugin editor showed only the generated header and the Lua chunk had EOF/syntax/no-main errors.

This version chunks raw Lua bytes in 1024-byte blocks and emits `<Block Base64="..." />`, matching observed MA3 export structure.



# 热修复：1024 字节 XML 文件内容块

MA3 导出的插件 XML 会将 ComponentLua/FileContent 分割成 1024 个原始字节块，然后对每个块进行 Base64 编码。

之前的脚手架版本会将 Base64 文本分割成 512 个字符的块。MA3 只能导入第一个块，因此插件编辑器只会显示生成的头部，而 Lua 块会出现 EOF/语法错误/缺少主函数等问题。

此版本将原始 Lua 字节分割成 1024 字节的块，并生成 `<Block Base64="..." />`，与观察到的 MA3 导出结构相匹配。