pragma ComponentBehavior: Bound

import Quickshell
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../config"

PopupWindow {
    id: root

    required property Theme theme
    required property Settings settings
    required property var hostWindow
    required property var targetScreen
    property string query: ""
    property int selectedIndex: 0

    anchor.window: hostWindow
    anchor.rect.x: Math.round((hostWindow.width - settings.overlayWidth) / 2)
    anchor.rect.y: settings.barPosition === "top" ? Math.round(targetScreen.height * 0.16) : Math.round(settings.barHeight + settings.barMarginBottom - targetScreen.height * 0.84)
    implicitWidth: settings.overlayWidth
    implicitHeight: Math.min(settings.overlayMaxHeight, Math.max(180, appList.implicitHeight + 126))
    visible: settings.shellEnabled && settings.launcherOpen && targetScreen === Quickshell.screens[0]
    grabFocus: true
    color: "transparent"
    onVisibleChanged: {
        if (visible) {
            query = "";
            selectedIndex = 0;
            search.forceActiveFocus();
        } else if (settings.launcherOpen) {
            settings.launcherOpen = false;
        }
    }

    function matchingApps() {
        const needle = query.trim().toLocaleLowerCase();
        if (needle.startsWith("=") || needle.startsWith("?") || needle.startsWith("!"))
            return [];
        const entries = DesktopEntries.applications.values;
        if (needle.length === 0) {
            const favorites = entries.filter(entry => root.settings.favoriteAppIds.includes(entry.id));
            return favorites.slice(0, settings.searchLimit);
        }

        const words = needle.split(/\s+/).filter(word => word.length > 0);
        const matches = [];
        for (const entry of entries) {
            const haystack = (entry.name + " " + entry.genericName + " " + entry.comment + " " + entry.keywords.join(" ")).toLocaleLowerCase();
            let score = 0;
            for (const word of words) {
                let cursor = 0;
                let prior = -2;
                let wordScore = 0;
                let matched = true;
                for (const character of word) {
                    const position = haystack.indexOf(character, cursor);
                    if (position < 0) {
                        matched = false;
                        break;
                    }
                    wordScore += position - prior - 1;
                    if (position === 0 || haystack[position - 1] === " ")
                        wordScore -= 2;
                    prior = position;
                    cursor = position + 1;
                }
                if (!matched) {
                    score = -1;
                    break;
                }
                score += wordScore;
            }
            if (score >= 0)
                matches.push({ entry: entry, score: score });
        }
        matches.sort((a, b) => a.score - b.score || a.entry.name.localeCompare(b.entry.name));
        return matches.slice(0, settings.searchLimit).map(result => result.entry);
    }

    function recordSearch() {
        const term = query.trim();
        if (term.length === 0)
            return;
        let next = [term].concat(settings.searchHistory.filter(item => item.toLocaleLowerCase() !== term.toLocaleLowerCase()));
        settings.searchHistory = next.slice(0, 12);
    }

    function toggleFavorite(entry) {
        let next = settings.favoriteAppIds.slice();
        const index = next.indexOf(entry.id);
        if (index >= 0)
            next.splice(index, 1);
        else
            next.push(entry.id);
        settings.favoriteAppIds = next;
    }

    function runQuickAction(action) {
        const scripts = {
            control: "/desktop/quick-settings.py",
            clipboard: "/clipboard/clipboard-menu.sh",
            wallpaper: "/wallpaper/wallpaper-selector.sh",
            power: "/session/power-menu.sh"
        };
        if (action === "settings")
            settings.settingsOpen = true;
        else if (action === "dashboard")
            settings.dashboardOpen = true;
        else if (scripts[action])
            Quickshell.execDetached([settings.scriptsRoot + scripts[action]]);
        else
            return false;
        recordSearch();
        settings.launcherOpen = false;
        return true;
    }

    function calculationResult() {
        const expression = query.trim().slice(1).replace(/\s+/g, "");
        if (expression.length === 0 || !/^[0-9+\-*/().%]+$/.test(expression))
            return "";

        let cursor = 0;
        function parsePrimary() {
            if (expression[cursor] === "(") {
                cursor++;
                const value = parseExpression();
                if (expression[cursor] !== ")")
                    throw new Error("Unclosed parenthesis");
                cursor++;
                return value;
            }
            const start = cursor;
            while (cursor < expression.length && /[0-9.]/.test(expression[cursor]))
                cursor++;
            if (start === cursor)
                throw new Error("Expected a number");
            const value = Number(expression.slice(start, cursor));
            if (!Number.isFinite(value))
                throw new Error("Invalid number");
            return value;
        }
        function parseUnary() {
            if (expression[cursor] === "+") {
                cursor++;
                return parseUnary();
            }
            if (expression[cursor] === "-") {
                cursor++;
                return -parseUnary();
            }
            return parsePrimary();
        }
        function parseTerm() {
            let value = parseUnary();
            while (["*", "/", "%"].includes(expression[cursor])) {
                const operator = expression[cursor++];
                const rhs = parseUnary();
                if ((operator === "/" || operator === "%") && rhs === 0)
                    throw new Error("Division by zero");
                value = operator === "*" ? value * rhs : operator === "/" ? value / rhs : value % rhs;
            }
            return value;
        }
        function parseExpression() {
            let value = parseTerm();
            while (["+", "-"].includes(expression[cursor])) {
                const operator = expression[cursor++];
                const rhs = parseTerm();
                value = operator === "+" ? value + rhs : value - rhs;
            }
            return value;
        }
        try {
            const result = parseExpression();
            if (cursor !== expression.length || !Number.isFinite(result))
                return "Invalid expression";
            return String(Number(result.toPrecision(10)));
        } catch (error) {
            return "Invalid expression";
        }
    }

    function executeSelected() {
        const term = query.trim();
        if (term.startsWith("!")) {
            runQuickAction(term.slice(1).trim().toLocaleLowerCase());
            return;
        }
        if (term.startsWith("=")) {
            const result = calculationResult();
            if (result.length > 0 && result !== "Invalid expression")
                Quickshell.execDetached(["wl-copy", result]);
            recordSearch();
            settings.launcherOpen = false;
            return;
        }
        if (term.startsWith("?") && term.slice(1).trim().length > 0) {
            Quickshell.execDetached([settings.browserCommand, "https://duckduckgo.com/?q=" + encodeURIComponent(term.slice(1).trim())]);
            recordSearch();
            settings.launcherOpen = false;
            return;
        }
        const items = matchingApps();
        if (items.length > 0 && selectedIndex >= 0 && selectedIndex < items.length) {
            recordSearch();
            items[selectedIndex].execute();
            settings.launcherOpen = false;
        }
    }

    Rectangle {
        anchors.fill: parent
        color: root.theme.background
        radius: root.theme.radiusLarge
        border.width: 1
        border.color: root.theme.border

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: root.theme.spacingLarge
            spacing: root.theme.spacing

            TextField {
                id: search
                Layout.fillWidth: true
                placeholderText: "Search apps, or use ? for a web search…"
                color: root.theme.text
                placeholderTextColor: root.theme.textMuted
                font.family: root.theme.fontFamily
                font.pixelSize: root.theme.fontSizeLarge
                background: Rectangle {
                    color: root.theme.surface
                    radius: root.theme.radius
                    border.width: 1
                    border.color: search.activeFocus ? root.theme.accent : root.theme.border
                }
                onTextChanged: {
                    root.query = text;
                    root.selectedIndex = 0;
                }
                Keys.onEscapePressed: root.settings.launcherOpen = false
                Keys.onReturnPressed: root.executeSelected()
                Keys.onDownPressed: root.selectedIndex = Math.min(root.matchingApps().length - 1, root.selectedIndex + 1)
                Keys.onUpPressed: root.selectedIndex = Math.max(0, root.selectedIndex - 1)
            }

            Text {
                Layout.fillWidth: true
                visible: root.query.length === 0 && root.settings.searchHistory.length > 0
                text: visible ? "Recent: " + root.settings.searchHistory.slice(0, 4).join("  ·  ") : ""
                color: root.theme.textMuted
                font.family: root.theme.fontFamily
                font.pixelSize: root.theme.fontSizeSmall
                elide: Text.ElideRight
            }

            Text {
                Layout.fillWidth: true
                visible: root.query.trim().startsWith("=")
                text: visible ? (root.calculationResult().length > 0 ? "= " + root.calculationResult() + "   ·   Enter copies result" : "Enter an arithmetic expression") : ""
                color: root.theme.accent
                font.family: root.theme.fontFamily
                font.pixelSize: root.theme.fontSize
            }

            Text {
                Layout.fillWidth: true
                visible: root.query.trim().startsWith("!")
                text: visible ? "Actions: !control  !clipboard  !wallpaper  !power  !dashboard  !settings" : ""
                color: root.theme.accent
                font.family: root.theme.fontFamily
                font.pixelSize: root.theme.fontSizeSmall
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: root.theme.spacingSmall
                Repeater {
                    model: [
                        { label: "Wallpaper", script: "/wallpaper/wallpaper-selector.sh" },
                        { label: "Clipboard", script: "/clipboard/clipboard-menu.sh" },
                        { label: "Controls", script: "/desktop/quick-settings.py" },
                        { label: "Power", script: "/session/power-menu.sh" },
                        { label: "Dashboard", script: "dashboard" },
                        { label: "Settings", script: "" }
                    ]
                    delegate: Rectangle {
                        id: actionCard
                        required property var modelData
                        Layout.fillWidth: true
                        implicitHeight: 32
                        color: actionMouse.containsMouse ? root.theme.surfaceRaised : root.theme.surface
                        radius: root.theme.radiusSmall
                        Text {
                            anchors.centerIn: parent
                            text: parent.modelData.label
                            color: root.theme.text
                            font.family: root.theme.fontFamily
                            font.pixelSize: root.theme.fontSizeSmall
                        }
                        MouseArea {
                            id: actionMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: {
                                if (actionCard.modelData.script === "dashboard") {
                                    root.settings.dashboardOpen = true;
                                } else if (actionCard.modelData.script.length > 0) {
                                    Quickshell.execDetached([root.settings.scriptsRoot + actionCard.modelData.script]);
                                } else {
                                    root.settings.settingsOpen = true;
                                }
                                root.settings.launcherOpen = false;
                            }
                        }
                    }
                }
            }

            ListView {
                id: appList
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                model: root.matchingApps()
                spacing: 3
                delegate: Rectangle {
                    id: appRow
                    required property var modelData
                    required property int index
                    width: appList.width
                    height: 42
                    radius: root.theme.radiusSmall
                    color: index === root.selectedIndex ? root.theme.surfaceRaised : "transparent"
                    MouseArea {
                        anchors.fill: parent
                        hoverEnabled: true
                        onEntered: root.selectedIndex = appRow.index
                        onClicked: {
                            appRow.modelData.execute();
                            root.settings.launcherOpen = false;
                        }
                    }
                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: root.theme.spacing
                        anchors.rightMargin: root.theme.spacing
                        spacing: root.theme.spacing
                        Image {
                            source: Quickshell.iconPath(appRow.modelData.icon, "application-x-executable")
                            sourceSize.width: 24
                            sourceSize.height: 24
                            Layout.preferredWidth: 24
                            Layout.preferredHeight: 24
                        }
                        Text {
                            Layout.fillWidth: true
                            text: appRow.modelData.name
                            color: root.theme.text
                            font.family: root.theme.fontFamily
                            font.pixelSize: root.theme.fontSize
                            elide: Text.ElideRight
                        }
                        Text {
                            text: appRow.modelData.genericName
                            color: root.theme.textMuted
                            font.family: root.theme.fontFamily
                            font.pixelSize: root.theme.fontSizeSmall
                        }
                        Text {
                            text: root.settings.favoriteAppIds.includes(appRow.modelData.id) ? "★" : "☆"
                            color: root.theme.accent
                            font.pixelSize: root.theme.fontSizeLarge
                            MouseArea {
                                anchors.fill: parent
                                onClicked: root.toggleFavorite(appRow.modelData)
                            }
                        }
                    }
                }
                Text {
                    anchors.centerIn: parent
                        visible: appList.count === 0
                        text: root.query.length > 0 ? "No matching applications" : "Star an app to add a favorite"
                    color: root.theme.textMuted
                    font.family: root.theme.fontFamily
                    font.pixelSize: root.theme.fontSize
                }
            }
        }
    }
}
