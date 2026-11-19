-- Application workspace placement rules.
-- Firefox follows the saved external-display workspace; when HDMI is absent,
-- Hyprland keeps that workspace available on the laptop display.

local function savedExternalWorkspace()
    local file = io.open(Desktop.config .. "/display-preferences.json", "r")
    if not file then
        return nil
    end

    local contents = file:read("*a")
    file:close()
    local workspace = contents:match('"external_workspace"%s*:%s*"([^"]+)"')
        or contents:match('"external_workspace"%s*:%s*(%d+)')
    if not workspace then
        return nil
    end

    local number = tonumber(workspace)
    if number and number >= 1 and number <= 10 and number % 1 == 0 then
        return tostring(number)
    end
    if workspace:match("^name:[%w][%w_. %-]*$") then
        return workspace
    end
    return nil
end

local placements = {
    { name = "firefox-external-workspace", class = "firefox", workspace = savedExternalWorkspace() },
    -- Add app-specific rules here, for example:
    -- { name = "chat-workspace", class = "your-chat-app", workspace = "3" },
}

for _, placement in ipairs(placements) do
    if placement.workspace then
        hl.window_rule({
            name = placement.name,
            match = { class = placement.class },
            workspace = placement.workspace,
        })
    end
end
