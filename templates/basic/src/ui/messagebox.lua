local Logger = require("ma3lib.logger")

local MessageBoxUI = {}

function MessageBoxUI.info(title, message)
    title = tostring(title or "Info")
    message = tostring(message or "")

    if MessageBox then
        return MessageBox({
            title = title,
            message = message,
            commands = {
                { value = 1, name = "OK" }
            }
        })
    end

    Logger.info(title .. ": " .. message)
    return nil
end

return MessageBoxUI
