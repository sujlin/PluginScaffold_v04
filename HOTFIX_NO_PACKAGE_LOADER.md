# Hotfix: no package.preload dependency

The generated Lua now uses a tiny lexical module loader instead of `package.preload`.
This avoids failures in grandMA3 plugin contexts where `package` is unavailable while MA3 resolves the plugin main function.
