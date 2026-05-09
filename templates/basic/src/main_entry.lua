local pluginName    = select(1, ...)
local componentName = select(2, ...)
local signalTable   = select(3, ...)
local my_handle     = select(4, ...)

local App = require("src.app")

local context = {
    pluginName = pluginName,
    componentName = componentName,
    signalTable = signalTable,
    my_handle = my_handle,
}

local function Main(display_handle, argument)
    return App.Main(context, display_handle, argument)
end

local function Cleanup()
    if App.Cleanup then
        return App.Cleanup(context)
    end
end

local function Execute(Type, ...)
    if App.Execute then
        return App.Execute(context, Type, ...)
    end
end

return Main, Cleanup, Execute
