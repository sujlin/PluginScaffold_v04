local Logger = {}

Logger.prefix = "MA3Plugin"
Logger.enabled = true

function Logger.init(name)
    Logger.prefix = tostring(name or "MA3Plugin")
end

function Logger.setEnabled(enabled)
    Logger.enabled = not not enabled
end

function Logger._print(level, msg)
    if not Logger.enabled then
        return
    end

    local text = "[" .. Logger.prefix .. "]"
    if level and level ~= "INFO" then
        text = text .. "[" .. level .. "]"
    end
    text = text .. " " .. tostring(msg)

    if Printf then
        Printf(text)
    else
        print(text)
    end
end

function Logger.info(msg)
    Logger._print("INFO", msg)
end

function Logger.warn(msg)
    Logger._print("WARN", msg)
end

function Logger.error(msg)
    Logger._print("ERROR", msg)
end

return Logger
