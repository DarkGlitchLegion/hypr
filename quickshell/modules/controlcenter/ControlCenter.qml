pragma ComponentBehavior: Bound

import Quickshell
import Quickshell.Io
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
    property var wallpapers: []
    property var clips: []
    property var displayOutputs: []
    property string displayWorkspace: "2"
    property var audioDevices: []
    property var wifiNetworks: []
    property var bluetoothDevices: []
    property string securityStatus: ""
    property var sessionPresets: []
    property string presetName: ""
    property int clipboardIndex: 0
    property string wifiPassword: ""
    property string pendingPower: ""

    readonly property var pages: [
        { id: "home", label: "Overview", icon: "⌂" },
        { id: "controls", label: "Quick controls", icon: "◉" },
        { id: "network", label: "Network", icon: "⌁" },
        { id: "audio", label: "Audio & display", icon: "♫" },
        { id: "display", label: "Displays", icon: "▣" },
        { id: "idle", label: "Idle & power", icon: "◷" },
        { id: "capture", label: "Screenshots", icon: "▧" },
        { id: "security", label: "HyprSec", icon: "⬡" },
        { id: "system", label: "System", icon: "⌘" },
        { id: "maintenance", label: "Maintenance", icon: "⚒" },
        { id: "developer", label: "Developer tools", icon: "⌁" },
        { id: "presets", label: "Session presets", icon: "▣" },
        { id: "notifications", label: "Notifications", icon: "◌" },
        { id: "wallpaper", label: "Wallpaper", icon: "▧" },
        { id: "clipboard", label: "Clipboard", icon: "▤" },
        { id: "keys", label: "Keybindings", icon: "⌨" },
        { id: "power", label: "Session & power", icon: "⏻" },
        { id: "settings", label: "Shell settings", icon: "⚙" }
    ]

    readonly property var bindings: [
        ["Launcher", "Super + Space", "Open application launcher"],
        ["Control Center", "Super + C · Super + Alt + Space", "Open this QML control center"],
        ["Keybindings", "Super + K", "Search this keybinding reference"],
        ["Keybindings", "Super + Shift + K", "Open the keybinding reference"],
        ["Applications", "Super + Return", "Open terminal"],
        ["Applications", "Super + Shift + Return", "Open web browser"],
        ["Applications", "Super + Shift + F", "Open file manager"],
        ["Applications", "Super + Shift + E", "Open editor"],
        ["Applications", "Super + Shift + T", "Open process monitor"],
        ["Applications", "Super + Shift + I", "Show system information"],
        ["Applications", "Super + Shift + M", "Open display controls"],
        ["Applications", "Super + Shift + C", "Open terminal matrix screensaver"],
        ["Security", "Super + Shift + H", "Open HyprSec Box"],
        ["Windows", "Super + M", "Minimize focused window with genie effect"],
        ["Windows", "Super + Alt + M", "Restore last genie-minimized window"],
        ["Hardware", "Super + Shift + S", "Open Wi-Fi controls"],
        ["Hardware", "Super + Shift + B", "Open Bluetooth controls"],
        ["Hardware", "Super + Ctrl + A", "Open audio controls"],
        ["Windows", "Super + Alt + F", "Maximize focused window"],
        ["Windows", "Super + J", "Toggle split direction"],
        ["Windows", "Super + G", "Toggle window group"],
        ["Windows", "Super + Alt + G", "Remove window from group"],
        ["Windows", "Super + Alt + Tab", "Cycle windows in group"],
        ["Windows", "Super + ; / '", "Resize focused window"],
        ["Workspaces", "Super + Shift + Alt + 1…0", "Move window without following"],
        ["Workspaces", "Super + Tab", "Next workspace"],
        ["Workspaces", "Super + Shift + Tab", "Previous workspace"],
        ["Workspaces", "Super + Ctrl + Tab", "Return to previous workspace"],
        ["Workspaces", "Super + Mouse wheel", "Cycle workspaces"],
        ["Wallpaper", "Super + Ctrl + W · Super + Ctrl + Space", "Choose wallpaper"],
        ["Clipboard", "Super + Ctrl + V", "Browse clipboard history"],
        ["Clipboard", "Super + Ctrl + Shift + V", "Clear clipboard history"],
        ["Session", "Super + Escape", "Open session and power actions"],
        ["Session", "Super + Ctrl + L · Super + L", "Lock screen"],
        ["Notifications", "Super + Shift + D", "Toggle do not disturb"],
        ["Notifications", "Super + Ctrl + N", "Open notification history"],
        ["Notifications", "Super + N", "Show previous notification"],
        ["Notifications", "Super + Shift + N", "Dismiss notifications"],
        ["Windows", "Super + W · Super + Q", "Close focused window"],
        ["Windows", "Super + T · Super + V", "Toggle floating window"],
        ["Windows", "Super + F", "Toggle fullscreen"],
        ["Windows", "Super + P", "Toggle pseudo tiling"],
        ["Windows", "Super + Arrow keys", "Focus window by direction"],
        ["Windows", "Super + Shift + Arrow keys", "Move window by direction"],
        ["Windows", "Super + Left mouse drag", "Move floating window"],
        ["Windows", "Super + Right mouse drag", "Resize floating window"],
        ["Workspaces", "Super + 1…0", "Switch workspace 1–10"],
        ["Workspaces", "Super + Shift + 1…0", "Move window to workspace"],
        ["Capture", "Print", "Capture selected region"],
        ["Capture", "Super + Print", "Capture screen"],
        ["Capture", "Super + Ctrl + C", "Open screenshot options"],
        ["System", "Super + Shift + R", "Restart the selected bar and reload Hyprland"],
        ["Audio", "Alt + XF86AudioRaiseVolume / LowerVolume", "Change volume by 1%"],
        ["Audio", "XF86AudioMute", "Toggle output mute"],
        ["Audio", "XF86AudioMicMute", "Toggle microphone mute"],
        ["Volume", "XF86AudioRaiseVolume / LowerVolume", "Change output volume"],
        ["Brightness", "Alt + XF86MonBrightnessUp / Down", "Change brightness by 1%"],
        ["Brightness", "Shift + XF86MonBrightnessUp", "Set brightness to 100%"],
        ["Brightness", "Shift + XF86MonBrightnessDown", "Set brightness to 5%"],
        ["Brightness", "XF86MonBrightnessUp / Down", "Change display brightness"]
    ]

    anchor.window: hostWindow
    anchor.rect.x: Math.round((hostWindow.width - Math.min(hostWindow.width - 24, 920)) / 2)
    anchor.rect.y: Math.round(targetScreen.height * 0.08)
    implicitWidth: Math.min(hostWindow.width - 24, 920)
    implicitHeight: Math.min(targetScreen.height - 90, 680)
    visible: settings.shellEnabled && settings.controlCenterOpen && targetScreen === Quickshell.screens[0]
    grabFocus: true
    color: "transparent"
    onVisibleChanged: {
        if (!visible && settings.controlCenterOpen)
            settings.controlCenterOpen = false;
        if (visible && settings.controlCenterPage === "wallpaper")
            loadWallpapers();
        if (visible && settings.controlCenterPage === "clipboard")
            loadClipboard();
    }
    Connections {
        target: root.settings
        function onControlCenterPageChanged() {
            root.query = "";
            root.pendingPower = "";
            search.text = "";
            root.presetName = "";
            if (root.settings.controlCenterPage === "wallpaper") root.loadWallpapers();
            if (root.settings.controlCenterPage === "clipboard") root.loadClipboard();
            if (root.settings.controlCenterPage === "display") displayProcess.running = true;
            if (root.settings.controlCenterPage === "audio" || root.settings.controlCenterPage === "controls") audioProcess.running = true;
            if (root.settings.controlCenterPage === "network" || root.settings.controlCenterPage === "controls") wifiProcess.running = true;
            if (root.settings.controlCenterPage === "network") bluetoothProcess.running = true;
            if (root.settings.controlCenterPage === "security") securityProcess.running = true;
            if (root.settings.controlCenterPage === "presets") presetProcess.running = true;
            if (root.settings.controlCenterPage === "notifications") { root.settings.notificationOpen = true; root.settings.controlCenterOpen = false; }
            if (["keys", "clipboard", "wallpaper", "presets"].includes(root.settings.controlCenterPage)) Qt.callLater(() => search.forceActiveFocus());
        }
    }

    function open(page) { settings.controlCenterPage = page; settings.controlCenterOpen = true; }
    function run(args) { Quickshell.execDetached(args); }
    function loadWallpapers() { wallpaperProcess.running = true; }
    function loadClipboard() { clipboardProcess.running = true; }
    function applyWallpaper(path) {
        run([settings.scriptsRoot + "/wallpaper/set-wallpaper.sh", path]);
        settings.wallpaperHistory = [path].concat(settings.wallpaperHistory.filter(item => item !== path)).slice(0, 20);
        settings.wallpaperFavoritesOnly = false;
    }
    function toggleWallpaperFavorite(path) {
        let favorites = settings.wallpaperFavorites.slice();
        const index = favorites.indexOf(path);
        if (index >= 0) favorites.splice(index, 1);
        else favorites.push(path);
        settings.wallpaperFavorites = favorites;
    }
    function chooseRandomWallpaper() {
        const choices = wallpapers.filter(path => !settings.wallpaperFavoritesOnly || settings.wallpaperFavorites.includes(path));
        if (choices.length > 0) applyWallpaper(choices[Math.floor(Math.random() * choices.length)]);
    }
    function filteredClips() {
        return clips.filter(item => !query || item.preview.toLowerCase().includes(query.toLowerCase()));
    }
    function copyClipboardAt(index) {
        const items = filteredClips();
        if (index < 0 || index >= items.length) return;
        run(["python3", settings.scriptsRoot + "/clipboard/qml-clipboard.py", "copy", String(items[index].id)]);
        settings.controlCenterOpen = false;
    }

    Process {
        id: wallpaperProcess
        command: ["python3", "-c", "import json,os,sys; d=sys.argv[1]; e={'.png','.jpg','.jpeg','.webp','.avif'}; print(json.dumps([os.path.join(d,n) for n in sorted(os.listdir(d)) if os.path.splitext(n)[1].lower() in e and os.path.isfile(os.path.join(d,n))]))", root.settings.configRoot + "/wallpapers"]
        stdout: StdioCollector {
            onStreamFinished: { try { root.wallpapers = JSON.parse(text); } catch (e) { root.wallpapers = []; } }
        }
        onExited: function(code) { if (code !== 0) root.wallpapers = []; }
    }
    Process {
        id: clipboardProcess
        command: ["python3", root.settings.scriptsRoot + "/clipboard/qml-clipboard.py", "list"]
        stdout: StdioCollector {
            onStreamFinished: { try { root.clips = JSON.parse(text); } catch (e) { root.clips = []; } }
        }
        onExited: function(code) { if (code !== 0) root.clips = []; }
    }
    Process {
        id: displayProcess
        command: ["python3", root.settings.scriptsRoot + "/hardware/display-manager.py", "--json"]
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const result = JSON.parse(text);
                    root.displayOutputs = result.monitors.filter(item => item.connected);
                    root.displayWorkspace = result.externalWorkspace || "2";
                }
                catch (e) { root.displayOutputs = []; }
            }
        }
        onExited: function(code) { if (code !== 0) root.displayOutputs = []; }
    }
    Process {
        id: audioProcess
        command: ["python3", root.settings.scriptsRoot + "/hardware/audio-manager.py", "--json"]
        stdout: StdioCollector {
            onStreamFinished: { try { root.audioDevices = JSON.parse(text); } catch (e) { root.audioDevices = []; } }
        }
        onExited: function(code) { if (code !== 0) root.audioDevices = []; }
    }
    Process {
        id: wifiProcess
        command: ["python3", root.settings.scriptsRoot + "/hardware/qml-network.py", "list"]
        stdout: StdioCollector {
            onStreamFinished: { try { root.wifiNetworks = JSON.parse(text); } catch (e) { root.wifiNetworks = []; } }
        }
        onExited: function(code) { if (code !== 0) root.wifiNetworks = []; }
    }
    Timer { id: audioRefreshTimer; interval: 900; onTriggered: audioProcess.running = true }
    Process {
        id: bluetoothProcess
        command: ["python3", root.settings.scriptsRoot + "/hardware/qml-bluetooth.py", "list"]
        stdout: StdioCollector {
            onStreamFinished: { try { root.bluetoothDevices = JSON.parse(text); } catch (e) { root.bluetoothDevices = []; } }
        }
        onExited: function(code) { if (code !== 0) root.bluetoothDevices = []; }
    }
    Process {
        id: securityProcess
        command: [root.settings.scriptsRoot + "/security/hyprsec-box.sh", "status"]
        stdout: StdioCollector { onStreamFinished: root.securityStatus = text }
        onExited: function(code) { if (code !== 0) root.securityStatus = "HyprSec status is unavailable. Check Podman and the HyprSec configuration." }
    }
    Process {
        id: presetProcess
        command: ["python3", root.settings.scriptsRoot + "/session/session-presets.py", "--json"]
        stdout: StdioCollector { onStreamFinished: { try { root.sessionPresets = JSON.parse(text); } catch (e) { root.sessionPresets = []; } } }
        onExited: function(code) { if (code !== 0) root.sessionPresets = []; }
    }

    Rectangle {
        focus: true
        Keys.onEscapePressed: root.settings.controlCenterOpen = false
        anchors.fill: parent
        color: root.theme.background
        radius: root.theme.radiusLarge
        border.width: 1
        border.color: root.theme.border

        RowLayout {
            anchors.fill: parent
            anchors.margins: root.theme.spacingLarge
            spacing: root.theme.spacingLarge

            ColumnLayout {
                Layout.preferredWidth: 190
                Layout.minimumWidth: 180
                Layout.maximumWidth: 200
                Layout.fillWidth: false
                Layout.fillHeight: true
                spacing: root.theme.spacing

                Text {
                    text: "HYPR  /  SHELL"
                    color: root.theme.accent
                    font.family: root.theme.fontFamily
                    font.pixelSize: root.theme.fontSizeLarge
                    font.bold: true
                    Layout.margins: root.theme.spacing
                }
                Flickable {
                    id: navFlick
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    contentWidth: width
                    contentHeight: navColumn.implicitHeight
                    ColumnLayout {
                        id: navColumn
                        width: navFlick.width
                        spacing: root.theme.spacing
                        Repeater {
                            model: root.pages
                            delegate: Rectangle {
                                id: navItem
                                required property var modelData
                                Layout.fillWidth: true
                                implicitHeight: 38
                                radius: root.theme.radius
                                color: root.settings.controlCenterPage === navItem.modelData.id ? root.theme.surfaceRaised : (navMouse.containsMouse ? root.theme.surface : "transparent")
                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: root.theme.spacingLarge
                                    anchors.rightMargin: root.theme.spacing
                                    Text { text: navItem.modelData.icon; color: root.theme.accent; font.pixelSize: 16 }
                                    Text { text: navItem.modelData.label; color: root.theme.text; font.family: root.theme.fontFamily; font.pixelSize: root.theme.fontSize; Layout.fillWidth: true }
                                }
                                MouseArea { id: navMouse; anchors.fill: parent; hoverEnabled: true; onClicked: root.open(navItem.modelData.id) }
                            }
                        }
                    }
                }
                Text { text: "Quickshell · QML"; color: root.theme.textMuted; font.family: root.theme.fontFamily; font.pixelSize: root.theme.fontSizeSmall; Layout.margins: root.theme.spacing }
            }

            Rectangle { Layout.fillHeight: true; implicitWidth: 1; color: root.theme.border }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: root.theme.spacingLarge

                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        Layout.fillWidth: true
                        text: {
                            const page = root.pages.find(p => p.id === root.settings.controlCenterPage);
                            return page ? page.label : "Control Center";
                        }
                        color: root.theme.text
                        font.family: root.theme.fontFamily
                        font.pixelSize: 20
                        font.bold: true
                    }
                    Text { text: "×"; color: root.theme.textMuted; font.pixelSize: 24; MouseArea { anchors.fill: parent; onClicked: root.settings.controlCenterOpen = false } }
                }

                TextField {
                    id: search
                    visible: root.settings.controlCenterPage === "keys" || root.settings.controlCenterPage === "clipboard" || root.settings.controlCenterPage === "wallpaper" || root.settings.controlCenterPage === "presets"
                    Layout.fillWidth: true
                    placeholderText: root.settings.controlCenterPage === "keys" ? "Filter keybindings…" : root.settings.controlCenterPage === "clipboard" ? "Filter clipboard history…" : root.settings.controlCenterPage === "presets" ? "New preset name…" : "Search wallpapers…"
                    color: root.theme.text
                    placeholderTextColor: root.theme.textMuted
                    selectionColor: root.theme.accent
                    font.family: root.theme.fontFamily
                    font.pixelSize: root.theme.fontSize
                    background: Rectangle {
                        color: root.theme.surface
                        radius: root.theme.radius
                        border.width: 1
                        border.color: search.activeFocus ? root.theme.accent : root.theme.border
                    }
                    onTextChanged: {
                        root.query = text;
                        root.clipboardIndex = 0;
                        if (root.settings.controlCenterPage === "presets") root.presetName = text;
                    }
                    Keys.onEscapePressed: root.settings.controlCenterOpen = false
                    Keys.onDownPressed: function(event) {
                        if (root.settings.controlCenterPage === "clipboard") {
                            root.clipboardIndex = Math.min(root.filteredClips().length - 1, root.clipboardIndex + 1);
                            pageFlick.contentY = Math.max(0, root.clipboardIndex * 72 - 40);
                            event.accepted = true;
                        }
                    }
                    Keys.onUpPressed: function(event) {
                        if (root.settings.controlCenterPage === "clipboard") {
                            root.clipboardIndex = Math.max(0, root.clipboardIndex - 1);
                            pageFlick.contentY = Math.max(0, root.clipboardIndex * 72 - 40);
                            event.accepted = true;
                        }
                    }
                    Keys.onReturnPressed: {
                        if (root.settings.controlCenterPage === "clipboard") root.copyClipboardAt(root.clipboardIndex);
                    }
                }

                Flickable {
                    id: pageFlick
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    contentWidth: width
                    contentHeight: pageColumn.implicitHeight
                    ScrollBar.vertical: ScrollBar {}
                    ColumnLayout {
                        id: pageColumn
                        width: pageFlick.width
                        spacing: root.theme.spacing

                        // Overview
                        GridLayout {
                            visible: root.settings.controlCenterPage === "home"
                            Layout.fillWidth: true
                            columns: 2
                            rowSpacing: root.theme.spacing
                            columnSpacing: root.theme.spacing
                            Repeater {
                                model: [
                                    { page: "controls", title: "Quick controls", detail: "Wi-Fi, Bluetooth, audio and brightness" },
                                    { page: "wallpaper", title: "Personalization", detail: "Choose from your wallpaper collection" },
                                    { page: "clipboard", title: "Clipboard history", detail: "Search and restore copied items" },
                                    { page: "keys", title: "Keybindings", detail: "Search shortcuts and descriptions" },
                                    { page: "power", title: "Session & power", detail: "Lock, suspend, restart or log out" },
                                    { page: "display", title: "Displays", detail: "Apply a monitor layout or enter presentation mode" },
                                    { page: "idle", title: "Idle management", detail: "Set timeout profile or keep the screen awake" },
                                    { page: "capture", title: "Screenshots", detail: "Capture a region, window or full screen" },
                                    { page: "security", title: "HyprSec Box", detail: "Manage the isolated security workspace" },
                                    { page: "system", title: "System tools", detail: "Process monitor, storage and desktop reload" },
                                    { page: "maintenance", title: "Maintenance", detail: "Diagnostics, snapshots, logs and validation" },
                                    { page: "developer", title: "Developer tools", detail: "Terminal, editor, Git and security workspace" },
                                    { page: "presets", title: "Session presets", detail: "Save or restore display, workspace, DND and idle state" },
                                    { page: "notifications", title: "Notifications", detail: "Review Dunst history and manage do not disturb" },
                                    { page: "dashboard", title: "System dashboard", detail: "CPU, memory, storage and battery metrics" },
                                    { page: "settings", title: "Shell settings", detail: "Bar, appearance and launcher options" }
                                ]
                                delegate: Rectangle {
                                    id: homeCard
                                    required property var modelData
                                    Layout.fillWidth: true
                                    implicitHeight: 96
                                    radius: root.theme.radius
                                    color: cardMouse.containsMouse ? root.theme.surfaceRaised : root.theme.surface
                                    border.width: 1
                                    border.color: root.theme.border
                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: root.theme.spacingLarge
                                        Text { text: homeCard.modelData.title; color: root.theme.text; font.family: root.theme.fontFamily; font.pixelSize: root.theme.fontSizeLarge; font.bold: true }
                                        Text { text: homeCard.modelData.detail; color: root.theme.textMuted; font.family: root.theme.fontFamily; font.pixelSize: root.theme.fontSizeSmall; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                                    }
                                MouseArea {
                                    id: cardMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    onClicked: {
                                        if (homeCard.modelData.page === "dashboard") {
                                            root.settings.dashboardOpen = true;
                                            root.settings.controlCenterOpen = false;
                                        } else root.open(homeCard.modelData.page);
                                    }
                                }
                                }
                            }
                        }

                        // Quick controls and one-click toggles
                        ColumnLayout {
                            visible: root.settings.controlCenterPage === "controls" || root.settings.controlCenterPage === "network" || root.settings.controlCenterPage === "audio"
                            Layout.fillWidth: true
                            spacing: root.theme.spacing
                            Text { visible: root.settings.controlCenterPage !== "controls"; text: root.settings.controlCenterPage === "network" ? "Connectivity" : "Sound and display"; color: root.theme.textMuted; font.family: root.theme.fontFamily; font.pixelSize: root.theme.fontSize }
                            GridLayout {
                                visible: root.settings.controlCenterPage !== "audio"
                                Layout.fillWidth: true
                                columns: 2
                                Repeater {
                                    model: [
                                        { title: "Wi-Fi on", detail: "Enable wireless networking", cmd: ["nmcli", "radio", "wifi", "on"] },
                                        { title: "Wi-Fi off", detail: "Disable wireless networking", cmd: ["nmcli", "radio", "wifi", "off"] },
                                        { title: "Bluetooth on", detail: "Power on the Bluetooth adapter", cmd: ["bluetoothctl", "power", "on"] },
                                        { title: "Bluetooth off", detail: "Power off the Bluetooth adapter", cmd: ["bluetoothctl", "power", "off"] },
                                        { title: "Rescan Wi-Fi", detail: "Refresh nearby access points", cmd: ["nmcli", "device", "wifi", "rescan"] },
                                        { title: "Scan Bluetooth", detail: "Scan for nearby devices", cmd: ["bluetoothctl", "scan", "on"] }
                                    ]
                                    delegate: Rectangle {
                                        id: controlCard
                                        required property var modelData
                                        Layout.fillWidth: true
                                        implicitHeight: 76
                                        radius: root.theme.radius
                                        color: controlMouse.containsMouse ? root.theme.surfaceRaised : root.theme.surface
                                        border.width: 1; border.color: root.theme.border
                                        ColumnLayout {
                                            anchors.fill: parent; anchors.margins: root.theme.spacingLarge
                                            Text { text: controlCard.modelData.title; color: root.theme.text; font.family: root.theme.fontFamily; font.pixelSize: root.theme.fontSizeLarge }
                                            Text { text: controlCard.modelData.detail; color: root.theme.textMuted; font.family: root.theme.fontFamily; font.pixelSize: root.theme.fontSizeSmall }
                                        }
                                        MouseArea { id: controlMouse; anchors.fill: parent; hoverEnabled: true; onClicked: root.run(controlCard.modelData.cmd) }
                                    }
                                }
                            }
                            ColumnLayout {
                                visible: root.settings.controlCenterPage === "network"
                                Layout.fillWidth: true
                                Timer { id: wifiRefreshTimer; interval: 1800; onTriggered: wifiProcess.running = true }
                                RowLayout {
                                    Layout.fillWidth: true
                                    Text { Layout.fillWidth: true; text: "Nearby Wi-Fi networks"; color: root.theme.textMuted; font.family: root.theme.fontFamily; font.pixelSize: root.theme.fontSize }
                                    HubButton {
                                    theme: root.theme
                                    text: "Rescan"; onClicked: { root.run(["nmcli", "device", "wifi", "rescan"]); wifiRefreshTimer.start() } }
                                }
                                TextField { id: wifiPass; Layout.fillWidth: true; placeholderText: "Wi-Fi password (only needed for a new secured network)"; echoMode: TextInput.Password; onTextChanged: root.wifiPassword = text }
                                Repeater {
                                    model: root.wifiNetworks
                                    delegate: Rectangle {
                                        id: wifiRow
                                        required property var modelData
                                        Layout.fillWidth: true; implicitHeight: 48; radius: root.theme.radius
                                        color: wifiMouse.containsMouse ? root.theme.surfaceRaised : root.theme.surface
                                        RowLayout {
                                            anchors.fill: parent; anchors.margins: root.theme.spacingLarge
                                            Text { Layout.fillWidth: true; text: (wifiRow.modelData.active ? "●  " : "") + wifiRow.modelData.ssid + "  ·  " + wifiRow.modelData.signal + "%  ·  " + wifiRow.modelData.security; color: root.theme.text; font.family: root.theme.fontFamily; font.pixelSize: root.theme.fontSize; elide: Text.ElideRight }
                                            Text { text: wifiRow.modelData.active ? "Connected" : "Connect"; color: root.theme.accent; font.family: root.theme.fontFamily; font.pixelSize: root.theme.fontSize }
                                        }
                                    MouseArea { id: wifiMouse; anchors.fill: parent; hoverEnabled: true; onClicked: { root.run(["python3", root.settings.scriptsRoot + "/hardware/qml-network.py", "connect", wifiRow.modelData.ssid].concat(root.wifiPassword ? [root.wifiPassword] : [])); wifiRefreshTimer.start() } }
                                    }
                                }
                                Text { visible: root.wifiNetworks.length === 0; text: "No networks returned. Enable Wi-Fi and rescan."; color: root.theme.textMuted; font.family: root.theme.fontFamily; font.pixelSize: root.theme.fontSizeSmall }
                                Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: root.theme.border }
                                RowLayout {
                                    Layout.fillWidth: true
                                    Text { Layout.fillWidth: true; text: "Bluetooth devices"; color: root.theme.textMuted; font.family: root.theme.fontFamily; font.pixelSize: root.theme.fontSize }
                                    HubButton {
                                    theme: root.theme
                                    text: "Scan"; onClicked: { root.run(["bluetoothctl", "scan", "on"]); bluetoothRefreshTimer.start() } }
                                    HubButton {
                                    theme: root.theme
                                    text: "Refresh"; onClicked: bluetoothProcess.running = true }
                                }
                                Timer { id: bluetoothRefreshTimer; interval: 2500; onTriggered: bluetoothProcess.running = true }
                                Repeater {
                                    model: root.bluetoothDevices
                                    delegate: Rectangle {
                                        id: btRow
                                        required property var modelData
                                        Layout.fillWidth: true; implicitHeight: 76; radius: root.theme.radius; color: root.theme.surface
                                        RowLayout {
                                            anchors.fill: parent; anchors.margins: root.theme.spacingLarge
                                            ColumnLayout {
                                                Layout.fillWidth: true
                                                Text { text: btRow.modelData.name; color: root.theme.text; font.family: root.theme.fontFamily; font.pixelSize: root.theme.fontSize; elide: Text.ElideRight }
                                                Text { text: btRow.modelData.mac + (btRow.modelData.connected ? " · connected" : btRow.modelData.paired ? " · paired" : " · new device"); color: root.theme.textMuted; font.family: root.theme.fontFamily; font.pixelSize: root.theme.fontSizeSmall }
                                            }
                                            HubButton {
                                    theme: root.theme
                                    visible: !btRow.modelData.paired; text: "Pair"; onClicked: { root.run(["python3", root.settings.scriptsRoot + "/hardware/qml-bluetooth.py", "pair", btRow.modelData.mac]); bluetoothRefreshTimer.start() } }
                                            HubButton {
                                    theme: root.theme
                                    visible: btRow.modelData.paired && !btRow.modelData.connected; text: "Connect"; onClicked: { root.run(["python3", root.settings.scriptsRoot + "/hardware/qml-bluetooth.py", "connect", btRow.modelData.mac]); bluetoothRefreshTimer.start() } }
                                            HubButton {
                                    theme: root.theme
                                    visible: btRow.modelData.connected; text: "Disconnect"; onClicked: { root.run(["python3", root.settings.scriptsRoot + "/hardware/qml-bluetooth.py", "disconnect", btRow.modelData.mac]); bluetoothRefreshTimer.start() } }
                                        }
                                    }
                                }
                            }
                            GridLayout {
                                visible: root.settings.controlCenterPage !== "network"
                                Layout.fillWidth: true
                                columns: 2
                                Repeater {
                                    model: [
                                        { title: "Volume −", detail: "Lower output volume by 5%", cmd: ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "5%-"] },
                                        { title: "Volume +", detail: "Raise output volume by 5%", cmd: ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "5%+"] },
                                        { title: "Mute output", detail: "Toggle output mute", cmd: ["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"] },
                                        { title: "Mute microphone", detail: "Toggle microphone mute", cmd: ["wpctl", "set-mute", "@DEFAULT_AUDIO_SOURCE@", "toggle"] },
                                        { title: "Brightness −", detail: "Lower screen brightness", cmd: [root.settings.scriptsRoot + "/hardware/brightness.sh", "down", "5"] },
                                        { title: "Brightness +", detail: "Raise screen brightness", cmd: [root.settings.scriptsRoot + "/hardware/brightness.sh", "up", "5"] },
                                        { title: "Power saver", detail: "Select power-saving profile", cmd: ["powerprofilesctl", "set", "power-saver"] },
                                        { title: "Balanced", detail: "Select balanced profile", cmd: ["powerprofilesctl", "set", "balanced"] },
                                        { title: "Performance", detail: "Select performance profile", cmd: ["powerprofilesctl", "set", "performance"] },
                                        { title: "Do Not Disturb", detail: "Toggle notification delivery", cmd: [root.settings.scriptsRoot + "/session/notification-toggle.sh"] }
                                    ]
                                    delegate: Rectangle {
                                        id: audioCard
                                        required property var modelData
                                        Layout.fillWidth: true; implicitHeight: 76; radius: root.theme.radius
                                        color: audioMouse.containsMouse ? root.theme.surfaceRaised : root.theme.surface
                                        border.width: 1; border.color: root.theme.border
                                        ColumnLayout {
                                            anchors.fill: parent; anchors.margins: root.theme.spacingLarge
                                            Text { text: audioCard.modelData.title; color: root.theme.text; font.family: root.theme.fontFamily; font.pixelSize: root.theme.fontSizeLarge }
                                            Text { text: audioCard.modelData.detail; color: root.theme.textMuted; font.family: root.theme.fontFamily; font.pixelSize: root.theme.fontSizeSmall }
                                        }
                                        MouseArea { id: audioMouse; anchors.fill: parent; hoverEnabled: true; onClicked: root.run(audioCard.modelData.cmd) }
                                    }
                                }
                            }
                            ColumnLayout {
                                visible: root.settings.controlCenterPage === "audio"
                                Layout.fillWidth: true
                                Text { text: "Audio devices · choose the active input or output"; color: root.theme.textMuted; font.family: root.theme.fontFamily; font.pixelSize: root.theme.fontSize }
                                Repeater {
                                    model: root.audioDevices.filter(device => device.active)
                                    delegate: RowLayout {
                                        id: activeAudioLevel
                                        required property var modelData
                                        Layout.fillWidth: true
                                        Text { Layout.preferredWidth: 110; text: activeAudioLevel.modelData.type === "output" ? "Output volume" : "Input level"; color: root.theme.text; font.family: root.theme.fontFamily; font.pixelSize: root.theme.fontSize }
                                        Slider {
                                            id: audioSlider
                                            Layout.fillWidth: true
                                            from: 0; to: 150; value: Number(activeAudioLevel.modelData.volume)
                                            onMoved: root.run(["wpctl", "set-volume", activeAudioLevel.modelData.type === "output" ? "@DEFAULT_AUDIO_SINK@" : "@DEFAULT_AUDIO_SOURCE@", (value / 100).toFixed(2)])
                                        }
                                        Text { text: Math.round(audioSlider.value) + "%"; color: root.theme.textMuted; font.family: root.theme.fontFamily; font.pixelSize: root.theme.fontSizeSmall }
                                    }
                                }
                                Repeater {
                                    model: root.audioDevices
                                    delegate: HubButton {
                                    theme: root.theme
                                        id: audioDevice
                                        required property var modelData
                                        visible: audioDevice.modelData.type === "output" || audioDevice.modelData.type === "input"
                                        Layout.fillWidth: true
                                        text: (audioDevice.modelData.active ? "●  " : "○  ") + audioDevice.modelData.type + " · " + audioDevice.modelData.description + " · " + audioDevice.modelData.volume + "%"
                                        onClicked: { root.run(["python3", root.settings.scriptsRoot + "/hardware/audio-manager.py", "--set", audioDevice.modelData.type, audioDevice.modelData.name]); audioRefreshTimer.start() }
                                    }
                                }
                                HubButton {
                                    theme: root.theme
                                    text: "Toggle automatic HDMI audio switching"; onClicked: root.run(["python3", root.settings.scriptsRoot + "/hardware/audio-manager.py", "--toggle-auto"]) }
                            }
                        }

                        // Wallpaper gallery
                        GridLayout {
                            visible: root.settings.controlCenterPage === "wallpaper"
                            Layout.fillWidth: true
                            columns: 3
                            HubButton {
                                    theme: root.theme
                                    Layout.columnSpan: 3; text: root.settings.wallpaperFavoritesOnly ? "Show all wallpapers" : "Show favorites"; onClicked: root.settings.wallpaperFavoritesOnly = !root.settings.wallpaperFavoritesOnly }
                            HubButton {
                                    theme: root.theme
                                    Layout.columnSpan: 3; text: "Choose random wallpaper"; onClicked: root.chooseRandomWallpaper() }
                            Repeater {
                                model: root.wallpapers.filter(path => (!root.settings.wallpaperFavoritesOnly || root.settings.wallpaperFavorites.includes(path)) && (!root.query || path.split("/").pop().toLowerCase().includes(root.query.toLowerCase())))
                                delegate: Rectangle {
                                    id: wallpaperCard
                                    required property string modelData
                                    Layout.fillWidth: true; implicitHeight: 142; radius: root.theme.radius; clip: true
                                    color: root.theme.surface; border.width: 1; border.color: root.theme.border
                                    Image { anchors.fill: parent; source: "file://" + wallpaperCard.modelData; fillMode: Image.PreserveAspectCrop; asynchronous: true }
                                    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 30; color: "#CC0C0D10" }
                                    Text { anchors.bottom: parent.bottom; anchors.left: parent.left; anchors.right: parent.right; anchors.margins: root.theme.spacing; text: wallpaperCard.modelData.split("/").pop(); color: root.theme.text; font.family: root.theme.fontFamily; font.pixelSize: root.theme.fontSizeSmall; elide: Text.ElideMiddle }
                                    Text {
                                        anchors.top: parent.top; anchors.right: parent.right; anchors.margins: root.theme.spacing
                                        text: root.settings.wallpaperFavorites.includes(wallpaperCard.modelData) ? "★" : "☆"
                                        color: root.theme.accent; font.pixelSize: 22
                                        MouseArea { anchors.fill: parent; anchors.margins: -6; onClicked: root.toggleWallpaperFavorite(wallpaperCard.modelData) }
                                    }
                                    MouseArea { anchors.fill: parent; z: -1; onClicked: root.applyWallpaper(wallpaperCard.modelData) }
                                }
                            }
                            Text { visible: root.wallpapers.length === 0; Layout.columnSpan: 3; text: "No wallpapers found in ~/.config/hypr/wallpapers"; color: root.theme.textMuted; font.family: root.theme.fontFamily }
                        }

                        // Clipboard history
                        ColumnLayout {
                            visible: root.settings.controlCenterPage === "clipboard"
                            Layout.fillWidth: true
                            Repeater {
                                model: root.filteredClips()
                                delegate: Rectangle {
                                    id: clipRow
                                    required property var modelData
                                    required property int index
                                    Layout.fillWidth: true; implicitHeight: 64; radius: root.theme.radius
                                    color: index === root.clipboardIndex ? root.theme.surfaceRaised : root.theme.surface
                                    border.width: 1; border.color: root.theme.border
                                    Text { anchors.fill: parent; anchors.margins: root.theme.spacingLarge; text: clipRow.modelData.preview; color: root.theme.text; font.family: root.theme.fontFamily; font.pixelSize: root.theme.fontSize; elide: Text.ElideRight; verticalAlignment: Text.AlignVCenter }
                                    MouseArea { id: clipMouse; anchors.fill: parent; hoverEnabled: true; onEntered: root.clipboardIndex = clipRow.index; onClicked: root.copyClipboardAt(clipRow.index) }
                                }
                            }
                            Text { visible: root.clips.length === 0; text: "Clipboard history is empty"; color: root.theme.textMuted; font.family: root.theme.fontFamily }
                            HubButton {
                                    theme: root.theme
                                    text: "Clear clipboard history"; onClicked: { root.run([root.settings.scriptsRoot + "/clipboard/clipboard-clear.sh"]); root.clips = [] } }
                        }

                        // Searchable shortcut reference
                        ColumnLayout {
                            visible: root.settings.controlCenterPage === "keys"
                            Layout.fillWidth: true
                            Repeater {
                                model: root.bindings.filter(item => !root.query || (item[0] + " " + item[1] + " " + item[2]).toLowerCase().includes(root.query.toLowerCase()))
                                delegate: Rectangle {
                                    id: bindingRow
                                    required property var modelData
                                    Layout.fillWidth: true; implicitHeight: 58; radius: root.theme.radius; color: root.theme.surface
                                    RowLayout {
                                        anchors.fill: parent; anchors.margins: root.theme.spacingLarge; spacing: root.theme.spacingLarge
                                        Text { Layout.preferredWidth: 82; text: bindingRow.modelData[0]; color: root.theme.accent; font.family: root.theme.fontFamily; font.pixelSize: root.theme.fontSizeSmall; wrapMode: Text.WordWrap }
                                        Text { Layout.preferredWidth: 205; text: bindingRow.modelData[1]; color: root.theme.text; font.family: root.theme.fontFamily; font.pixelSize: root.theme.fontSize; wrapMode: Text.WordWrap }
                                        Text { Layout.fillWidth: true; text: bindingRow.modelData[2]; color: root.theme.textMuted; font.family: root.theme.fontFamily; font.pixelSize: root.theme.fontSize; wrapMode: Text.WordWrap }
                                    }
                                }
                            }
                        }

                        // Session and power actions with confirmation
                        ColumnLayout {
                            visible: root.settings.controlCenterPage === "power"
                            Layout.fillWidth: true
                            Text { visible: root.pendingPower !== ""; Layout.fillWidth: true; text: "Confirm " + root.pendingPower + "? Unsaved work may be lost."; color: root.theme.warning; font.family: root.theme.fontFamily; font.pixelSize: root.theme.fontSizeLarge; wrapMode: Text.WordWrap }
                            GridLayout {
                                Layout.fillWidth: true; columns: 2
                                Repeater {
                                    model: [
                                        { name: "Lock screen", action: "lock" }, { name: "Suspend", action: "suspend" },
                                        { name: "Restart", action: "reboot" }, { name: "Shut down", action: "poweroff" },
                                        { name: "Log out", action: "logout" }, { name: "Reload Hyprland", action: "reload" }
                                    ]
                                    delegate: HubButton {
                                    theme: root.theme
                                        id: powerButton
                                        required property var modelData
                                        Layout.fillWidth: true; implicitHeight: 68
                                        text: powerButton.modelData.name
                                        onClicked: {
                                            const action = powerButton.modelData.action;
                                            if (["reboot", "poweroff", "logout"].includes(action) && root.pendingPower !== action) {
                                                root.pendingPower = action;
                                                return;
                                            }
                                            if (action === "lock") root.run(["hyprlock", "-c", root.settings.configRoot + "/hyprlock/hyprlock.conf"]);
                                            else if (action === "suspend") root.run(["systemctl", "suspend"]);
                                            else if (action === "reboot") root.run(["systemctl", "reboot"]);
                                            else if (action === "poweroff") root.run(["systemctl", "poweroff"]);
                                            else if (action === "logout") root.run(["hyprctl", "dispatch", "exit"]);
                                            else if (action === "reload") root.run([root.settings.scriptsRoot + "/desktop/restart-bar.sh"]);
                                            root.pendingPower = "";
                                            root.settings.controlCenterOpen = false;
                                        }
                                    }
                                }
                            }
                            HubButton {
                                    theme: root.theme
                                    visible: root.pendingPower !== ""; text: "Cancel"; onClicked: root.pendingPower = "" }
                        }

                        // Display profiles use the existing transactional backend.
                        ColumnLayout {
                            visible: root.settings.controlCenterPage === "display"
                            Layout.fillWidth: true
                            Text { text: "Display layout operations use the existing rollback-aware display manager."; color: root.theme.textMuted; font.family: root.theme.fontFamily; font.pixelSize: root.theme.fontSize; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                            Repeater {
                                model: [
                                    { label: "Laptop only", cmd: ["python3", root.settings.scriptsRoot + "/hardware/display-manager.py", "--preset", "laptop"] },
                                    { label: "Save current layout", cmd: ["python3", root.settings.scriptsRoot + "/hardware/display-manager.py", "--save"] },
                                    { label: "Reapply saved layout", cmd: ["python3", root.settings.scriptsRoot + "/hardware/display-manager.py", "--restore"] }
                                ]
                                delegate: HubButton {
                                    theme: root.theme
                                    required property var modelData
                                    Layout.fillWidth: true
                                    text: modelData.label
                                    onClicked: root.run(modelData.cmd)
                                }
                            }
                            Text { text: "Connected displays · per-monitor controls"; color: root.theme.textMuted; font.family: root.theme.fontFamily; font.pixelSize: root.theme.fontSize }
                            Repeater {
                                model: root.displayOutputs
                                delegate: ColumnLayout {
                                    id: displayOutput
                                    required property var modelData
                                    Layout.fillWidth: true
                                    spacing: root.theme.spacing
                                    Text { text: displayOutput.modelData.name + (displayOutput.modelData.internal ? " · built-in" : " · external"); color: root.theme.text; font.family: root.theme.fontFamily; font.pixelSize: root.theme.fontSizeLarge }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Repeater {
                                            model: ["0.75", "1.0", "1.25", "1.5", "1.75", "2.0"]
                                            delegate: HubButton {
                                                required property string modelData
                                                theme: root.theme
                                                Layout.fillWidth: true
                                                text: modelData + "×"
                                                onClicked: root.run(["python3", root.settings.scriptsRoot + "/hardware/display-manager.py", "--set-scale", displayOutput.modelData.name, modelData])
                                            }
                                        }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        HubButton { theme: root.theme; Layout.fillWidth: true; text: "Landscape"; onClicked: root.run(["python3", root.settings.scriptsRoot + "/hardware/display-manager.py", "--set-transform", displayOutput.modelData.name, "0"]) }
                                        HubButton { theme: root.theme; Layout.fillWidth: true; text: "Portrait"; onClicked: root.run(["python3", root.settings.scriptsRoot + "/hardware/display-manager.py", "--set-transform", displayOutput.modelData.name, "1"]) }
                                        HubButton { theme: root.theme; Layout.fillWidth: true; text: "Primary"; onClicked: root.run(["python3", root.settings.scriptsRoot + "/hardware/display-manager.py", "--primary", displayOutput.modelData.name]) }
                                    }
                                    ComboBox {
                                        id: modeSelector
                                        Layout.fillWidth: true
                                        model: displayOutput.modelData.availableModes || []
                                        currentIndex: Math.max(0, model.findIndex(mode => mode.startsWith(displayOutput.modelData.width + "x" + displayOutput.modelData.height)))
                                        contentItem: Text { leftPadding: root.theme.spacingLarge; text: modeSelector.currentText || "Preferred mode"; color: root.theme.text; font.family: root.theme.fontFamily; font.pixelSize: root.theme.fontSize; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
                                        background: Rectangle { radius: root.theme.radius; color: root.theme.surface; border.width: 1; border.color: root.theme.border }
                                        delegate: ItemDelegate {
                                            id: displayModeDelegate
                                            required property string modelData
                                            width: modeSelector.width
                                            contentItem: Text { text: displayModeDelegate.modelData; color: root.theme.text; font.family: root.theme.fontFamily; font.pixelSize: root.theme.fontSize; verticalAlignment: Text.AlignVCenter }
                                            background: Rectangle { color: displayModeDelegate.highlighted ? root.theme.surfaceRaised : root.theme.surface }
                                        }
                                        popup: Popup {
                                            y: modeSelector.height
                                            width: modeSelector.width
                                            implicitHeight: Math.min(contentItem.implicitHeight, 320)
                                            padding: 2
                                            contentItem: ListView {
                                                clip: true
                                                implicitHeight: contentHeight
                                                model: modeSelector.popup.visible ? modeSelector.delegateModel : null
                                                currentIndex: modeSelector.highlightedIndex
                                                ScrollIndicator.vertical: ScrollIndicator {}
                                            }
                                            background: Rectangle { color: root.theme.background; radius: root.theme.radius; border.width: 1; border.color: root.theme.border }
                                        }
                                        onActivated: root.run(["python3", root.settings.scriptsRoot + "/hardware/display-manager.py", "--set-mode", displayOutput.modelData.name, currentText])
                                    }
                                    RowLayout {
                                        visible: !displayOutput.modelData.internal && root.displayOutputs.some(item => item.internal)
                                        Layout.fillWidth: true
                                        TextField { id: extWorkspace; Layout.fillWidth: true; text: root.displayWorkspace; placeholderText: "External display workspace"; color: root.theme.text; onTextChanged: root.displayWorkspace = text }
                                        HubButton { theme: root.theme; text: "Extend"; onClicked: root.run(["python3", root.settings.scriptsRoot + "/hardware/display-manager.py", "--preset", "extend", displayOutput.modelData.name, root.displayWorkspace, "right"]) }
                                        HubButton { theme: root.theme; text: "Mirror"; onClicked: root.run(["python3", root.settings.scriptsRoot + "/hardware/display-manager.py", "--preset", "mirror", displayOutput.modelData.name]) }
                                    }
                                }
                            }
                        }

                        // Idle manager exposes validated, non-interactive operations.
                        ColumnLayout {
                            visible: root.settings.controlCenterPage === "idle"
                            Layout.fillWidth: true
                            Text { text: "Timeout profiles"; color: root.theme.textMuted; font.family: root.theme.fontFamily; font.pixelSize: root.theme.fontSize }
                            Repeater {
                                model: ["Never", "Balanced", "Power Saving", "Security Focused", "Relaxed"]
                                delegate: HubButton {
                                    theme: root.theme
                                    required property string modelData
                                    Layout.fillWidth: true
                                    text: modelData
                                    onClicked: root.run(["python3", root.settings.scriptsRoot + "/session/idle-manager.py", "--preset", modelData])
                                }
                            }
                            HubButton {
                                    theme: root.theme
                                    text: "Toggle idle management"; onClicked: root.run(["python3", root.settings.scriptsRoot + "/session/idle-manager.py", "--master", "toggle"]) }
                            HubButton {
                                    theme: root.theme
                                    text: "Toggle keep-awake"; onClicked: root.run(["python3", root.settings.scriptsRoot + "/session/idle-manager.py", "--keep-awake"]) }
                        }

                        // Screenshot capture operations retain the existing grim/slurp backend.
                        ColumnLayout {
                            visible: root.settings.controlCenterPage === "capture"
                            Layout.fillWidth: true
                            Repeater {
                                model: [
                                    { label: "Select region", mode: "region" },
                                    { label: "Active window", mode: "window" },
                                    { label: "Full screen", mode: "full" },
                                    { label: "Full screen after 5 seconds", mode: "delayed" }
                                ]
                                delegate: HubButton {
                                    theme: root.theme
                                    required property var modelData
                                    Layout.fillWidth: true
                                    text: modelData.label
                                    onClicked: {
                                        root.run([root.settings.scriptsRoot + "/session/screenshot.sh", modelData.mode]);
                                        root.settings.controlCenterOpen = false;
                                    }
                                }
                            }
                        }

                        ColumnLayout {
                            visible: root.settings.controlCenterPage === "security"
                            Layout.fillWidth: true
                            Text { Layout.fillWidth: true; text: root.securityStatus || "Loading HyprSec status…"; color: root.theme.textMuted; font.family: root.theme.fontFamily; font.pixelSize: root.theme.fontSize; wrapMode: Text.WordWrap }
                            HubButton {
                                    theme: root.theme
                                    text: "Refresh status"; onClicked: securityProcess.running = true }
                            RowLayout {
                                Layout.fillWidth: true
                                HubButton {
                                    theme: root.theme
                                    Layout.fillWidth: true; text: "Create container"; onClicked: root.run([root.settings.scriptsRoot + "/security/hyprsec-box.sh", "create"]) }
                                HubButton {
                                    theme: root.theme
                                    Layout.fillWidth: true; text: "Start"; onClicked: root.run([root.settings.scriptsRoot + "/security/hyprsec-box.sh", "start"]) }
                                HubButton {
                                    theme: root.theme
                                    Layout.fillWidth: true; text: "Restart"; onClicked: root.run([root.settings.scriptsRoot + "/security/hyprsec-box.sh", "restart"]) }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                HubButton {
                                    theme: root.theme
                                    Layout.fillWidth: true
                                    text: root.pendingPower === "hyprsec-stop" ? "Confirm stop" : "Stop container"
                                    onClicked: {
                                        if (root.pendingPower !== "hyprsec-stop") root.pendingPower = "hyprsec-stop";
                                        else { root.run([root.settings.scriptsRoot + "/security/hyprsec-box.sh", "stop", "--yes"]); root.pendingPower = ""; }
                                    }
                                }
                                HubButton {
                                    theme: root.theme
                                    Layout.fillWidth: true; text: "Open terminal"; onClicked: root.run([root.settings.scriptsRoot + "/security/hyprsec-box.sh", "shell"]) }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                HubButton {
                                    theme: root.theme
                                    Layout.fillWidth: true; text: "Enable network"; onClicked: root.run([root.settings.scriptsRoot + "/security/hyprsec-box.sh", "network-enable"]) }
                                HubButton {
                                    theme: root.theme
                                    Layout.fillWidth: true; text: "Disable network"; onClicked: root.run([root.settings.scriptsRoot + "/security/hyprsec-box.sh", "network-disable"]) }
                            }
                        }

                        ColumnLayout {
                            visible: root.settings.controlCenterPage === "system"
                            Layout.fillWidth: true
                            Repeater {
                                model: [
                                    { label: "Process monitor", args: ["kitty", "--class", "btop", "--title", "btop", "-e", "btop"] },
                                    { label: "Disk usage", args: ["kitty", "-e", "sh", "-lc", "df -hT --exclude-type=tmpfs --exclude-type=devtmpfs; read -r -p 'Press Enter to close…'"] },
                                    { label: "Open Hypr config folder", args: ["thunar", root.settings.configRoot] },
                                    { label: "Restart bar", args: [root.settings.scriptsRoot + "/desktop/restart-bar.sh"] },
                                    { label: "Reload Hyprland", args: ["hyprctl", "reload"] },
                                    { label: "Lock screen", args: ["hyprlock", "-c", root.settings.configRoot + "/hyprlock/hyprlock.conf"] },
                                    { label: "Application launcher", args: [] }
                                ]
                                delegate: HubButton {
                                    theme: root.theme
                                    required property var modelData
                                    Layout.fillWidth: true
                                    text: modelData.label
                                    onClicked: {
                                        if (modelData.label === "Application launcher") root.settings.launcherOpen = true;
                                        else root.run(modelData.args);
                                    }
                                }
                            }
                        }

                        ColumnLayout {
                            visible: root.settings.controlCenterPage === "maintenance"
                            Layout.fillWidth: true
                            Repeater {
                                model: [
                                    { label: "Rice health diagnostics", args: ["doctor"] },
                                    { label: "Validate configuration", args: ["validate"] },
                                    { label: "Create configuration snapshot", args: ["snapshot", "create"] },
                                    { label: "List configuration snapshots", args: ["snapshot", "list"] },
                                    { label: "View activity logs", args: ["logs", "--limit", "100"] },
                                    { label: "Check dependencies", args: ["dependencies", "--full"] },
                                    { label: "Run project tests", args: ["test"] }
                                ]
                                delegate: HubButton {
                                    theme: root.theme
                                    required property var modelData
                                    Layout.fillWidth: true
                                    text: modelData.label
                                    onClicked: root.run(["kitty", "--config", root.settings.configRoot + "/kitty/kitty.conf", "-e", root.settings.scriptsRoot + "/rice"].concat(modelData.args))
                                }
                            }
                        }

                        ColumnLayout {
                            visible: root.settings.controlCenterPage === "developer"
                            Layout.fillWidth: true
                            Repeater {
                                model: [
                                    { label: "Terminal", args: ["kitty"] }, { label: "Firefox", args: ["firefox"] },
                                    { label: "VS Code", args: ["code"] }, { label: "Lazygit", args: ["kitty", "-e", "lazygit"] },
                                    { label: "Thunar", args: ["thunar"] }, { label: "CMatrix", args: [root.settings.scriptsRoot + "/desktop/cmatrix.sh"] },
                                    { label: "HyprSec Box", page: "security" }, { label: "Security tools folder", args: ["thunar", root.settings.configRoot + "/../../tools"] }
                                ]
                                delegate: HubButton {
                                    theme: root.theme
                                    required property var modelData
                                    Layout.fillWidth: true
                                    text: modelData.label
                                    onClicked: {
                                        if (modelData.page) root.open(modelData.page);
                                        else root.run(modelData.args);
                                    }
                                }
                            }
                        }

                        ColumnLayout {
                            visible: root.settings.controlCenterPage === "presets"
                            Layout.fillWidth: true
                            Text { Layout.fillWidth: true; visible: root.pendingPower.startsWith("preset-"); text: "Confirm this change: " + root.pendingPower.replace("preset-", ""); color: root.theme.warning; font.family: root.theme.fontFamily; font.pixelSize: root.theme.fontSize; wrapMode: Text.WordWrap }
                            RowLayout {
                                Layout.fillWidth: true
                                HubButton {
                                    theme: root.theme
                                    Layout.fillWidth: true
                                    text: root.pendingPower === "preset-save" ? "Confirm overwrite and save" : "Save current session"
                                    onClicked: {
                                        const exists = root.sessionPresets.some(item => item.name === root.presetName);
                                        if (!root.presetName.trim()) return;
                                        if (exists && root.pendingPower !== "preset-save") { root.pendingPower = "preset-save"; return; }
                                        root.run(["python3", root.settings.scriptsRoot + "/session/session-presets.py", "--save", root.presetName.trim()].concat(exists ? ["--replace"] : []));
                                        root.pendingPower = "";
                                        presetProcess.running = true;
                                    }
                                }
                                HubButton {
                                    theme: root.theme
                                    Layout.fillWidth: true; text: "Restore previous session"; onClicked: { root.pendingPower = "preset-restore"; root.run(["python3", root.settings.scriptsRoot + "/session/session-presets.py", "--restore"]); root.pendingPower = "" } }
                            }
                            Repeater {
                                model: root.sessionPresets
                                delegate: Rectangle {
                                    id: presetRow
                                    required property var modelData
                                    Layout.fillWidth: true; implicitHeight: 82; radius: root.theme.radius; color: root.theme.surface
                                    RowLayout {
                                        anchors.fill: parent; anchors.margins: root.theme.spacingLarge
                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            Text { text: presetRow.modelData.name; color: root.theme.text; font.family: root.theme.fontFamily; font.pixelSize: root.theme.fontSizeLarge }
                                            Text { Layout.fillWidth: true; text: presetRow.modelData.summary; color: root.theme.textMuted; font.family: root.theme.fontFamily; font.pixelSize: root.theme.fontSizeSmall; wrapMode: Text.WordWrap }
                                        }
                                        HubButton {
                                    theme: root.theme
                                    text: "Apply"; onClicked: root.run(["python3", root.settings.scriptsRoot + "/session/session-presets.py", "--apply", presetRow.modelData.name]) }
                                        HubButton {
                                    theme: root.theme
                                            text: root.pendingPower === "preset-delete-" + presetRow.modelData.name ? "Confirm delete" : "Delete"
                                            onClicked: {
                                                if (root.pendingPower !== "preset-delete-" + presetRow.modelData.name) root.pendingPower = "preset-delete-" + presetRow.modelData.name;
                                                else { root.run(["python3", root.settings.scriptsRoot + "/session/session-presets.py", "--delete", presetRow.modelData.name, "--yes"]); root.pendingPower = ""; presetProcess.running = true; }
                                            }
                                        }
                                    }
                                }
                            }
                            Text { visible: root.sessionPresets.length === 0; text: "No saved session presets"; color: root.theme.textMuted; font.family: root.theme.fontFamily }
                        }

                        // Existing settings panel is available from its own native QML surface.
                        ColumnLayout {
                            visible: root.settings.controlCenterPage === "settings"
                            Layout.fillWidth: true
                            Text { text: "Shell settings are available in the native settings panel."; color: root.theme.textMuted; font.family: root.theme.fontFamily; font.pixelSize: root.theme.fontSize; wrapMode: Text.WordWrap }
                            HubButton {
                                    theme: root.theme
                                    text: "Open shell settings"; onClicked: { root.settings.controlCenterOpen = false; root.settings.settingsOpen = true } }
                        }
                    }
                }
            }
        }
    }
}
