local Runtime = {}

Runtime.hooks = {}
Runtime.timers = {}
Runtime.cleanupHandlers = {}

function Runtime.addHook(hookId)
    if hookId then
        table.insert(Runtime.hooks, hookId)
    end
    return hookId
end

function Runtime.addTimer(timerId)
    if timerId then
        table.insert(Runtime.timers, timerId)
    end
    return timerId
end

function Runtime.onCleanup(fn)
    if fn then
        table.insert(Runtime.cleanupHandlers, fn)
    end
    return fn
end

function Runtime.cleanup()
    for _, fn in ipairs(Runtime.cleanupHandlers) do
        pcall(fn)
    end

    for _, hookId in ipairs(Runtime.hooks) do
        if Unhook then
            pcall(Unhook, hookId)
        end
    end

    Runtime.hooks = {}
    Runtime.timers = {}
    Runtime.cleanupHandlers = {}
end

return Runtime
