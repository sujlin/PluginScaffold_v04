local Object = {}

function Object.className(obj)
    if not obj then return nil end
    if obj.GetClass then
        local ok, result = pcall(function() return obj:GetClass() end)
        if ok then return result end
    end
    return nil
end

function Object.name(obj)
    if not obj then return nil end
    local ok, result = pcall(function()
        return obj.Name or obj.name or (obj.Get and obj:Get("Name"))
    end)
    if ok then return result end
    return nil
end

function Object.addr(obj)
    if not obj then return nil end
    if obj.ToAddr then
        local ok, result = pcall(function() return obj:ToAddr() end)
        if ok then return result end
    end
    return tostring(obj)
end

return Object
