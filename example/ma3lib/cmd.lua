local CmdUtil = {}

function CmdUtil.quote(value)
    value = tostring(value or "")
    value = value:gsub('"', '\\"')
    return '"' .. value .. '"'
end

function CmdUtil.run(cmd)
    cmd = tostring(cmd or "")
    if Printf then
        Printf("[CMD] " .. cmd)
    end
    return Cmd(cmd)
end

function CmdUtil.safe(cmd)
    cmd = tostring(cmd or "")
    if Printf then
        Printf("[CMD] " .. cmd)
    end

    local ok, result = pcall(Cmd, cmd)
    if not ok then
        if Printf then
            Printf("[CMD ERROR] " .. tostring(result))
        end
        return nil, result
    end
    return result
end

return CmdUtil
