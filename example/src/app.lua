local Logger = require("ma3lib.logger")
local Cmd = require("ma3lib.cmd")
local Runtime = require("ma3lib.runtime")

local App = {}

--- 插件主入口。MA3 执行 `Call Plugin` 时会调用这个函数。
---@param ctx table MA3 插件上下文，来自 src.main_entry。
---@param display_handle userdata|nil 当前显示器句柄。
---@param argument any Call Plugin 时传入的可选参数。
function App.Main(ctx, display_handle, argument)
    Logger.init(ctx.pluginName or "example")

    Logger.info("Hello MA3!")
    Logger.info("Plugin = examplePlugin")
    Logger.info("componentName = " .. tostring(ctx.componentName))
    Logger.info("argument = " .. tostring(argument))

    -- 这里开始写你的插件业务逻辑。
    -- 建议：所有会修改 showfile 的 Cmd 操作，都先加确认或只在测试 showfile 中运行。
    -- 示例：Cmd.safe('Label Plugin 1 "examplePlugin"')
end

--- 插件清理入口。ReloadAllPlugins、删除插件或 MA3 释放组件时可能调用。
---@param ctx table MA3 插件上下文。
function App.Cleanup(ctx)
    Runtime.cleanup()
    Logger.info("Cleanup")
end

--- 可选执行入口。用于响应 Executor / Key / Fader 等 Execute 事件。
---@param ctx table MA3 插件上下文。
---@param Type any MA3 传入的事件类型。
---@param ... any MA3 传入的事件参数。
function App.Execute(ctx, Type, ...)
    Logger.info("Execute: " .. tostring(Type))

    -- 可选：把事件转发给 MA3 signalTable 里同名处理函数。
    if ctx.signalTable and Type and ctx.signalTable[Type] then
        return ctx.signalTable[Type](ctx.signalTable, ...)
    end
end

return App
