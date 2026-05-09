local Object = require("ma3lib.object")

local Inspect = {}

function Inspect.printObject(obj, label)
    label = label or "object"
    local parts = {
        tostring(label),
        "class=" .. tostring(Object.className(obj)),
        "name=" .. tostring(Object.name(obj)),
        "addr=" .. tostring(Object.addr(obj)),
    }
    local text = table.concat(parts, " | ")
    if Printf then Printf(text) else print(text) end
end

function Inspect.properties(obj)
    local result = {}
    if not obj or not obj.PropertyCount then
        return result
    end
    local ok, count = pcall(function() return obj:PropertyCount() end)
    if not ok then return result end
    for i = 1, count do
        local nameOk, name = pcall(function() return obj:PropertyName(i) end)
        if nameOk and name then
            local valueOk, value = pcall(function() return obj:Get(name) end)
            result[#result + 1] = { index = i, name = name, value = valueOk and value or nil }
        end
    end
    return result
end

return Inspect
