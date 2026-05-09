local State = {}

function State.new()
    return {
        schemaVersion = 1,
        started = false
    }
end

return State
