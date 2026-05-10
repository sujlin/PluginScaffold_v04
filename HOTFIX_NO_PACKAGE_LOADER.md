# Hotfix: no package.preload dependency

The generated Lua now uses a tiny lexical module loader instead of `package.preload`.
This avoids failures in grandMA3 plugin contexts where `package` is unavailable while MA3 resolves the plugin main function.


# 热修复：不再依赖 `package.preload`

生成的 Lua 代码现在使用一个小型词法模块加载器，而不是 `package.preload`。

这避免了在 grandMA3 插件上下文中，当 `package` 不可用时，MA3 解析插件主函数时出现的错误。