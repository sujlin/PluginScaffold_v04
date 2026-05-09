-- Placeholder for showfile-backed storage.
-- Recommended future direction: UserPlugin/Note or ComponentLua.FileContent + Base64(JSON).

local Storage = {}

function Storage.loadDefault()
    return {
        schemaVersion = 1,
        pluginVersion = "0.1.0"
    }
end

return Storage
