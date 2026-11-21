pragma ComponentBehavior: Bound

import Quickshell
import Quickshell.Io
import QtQuick
import QtQuick.Layouts
import "../../config"
import "../window"

OverlayPanel {
    id: root

    required property Theme theme
    required property Settings settings
    required property var hostWindow
    property var notifications: []

    implicitWidth: 460
    implicitHeight: Math.min(560, Math.max(220, notificationList.contentHeight + 120))
    visible: settings.shellEnabled && settings.notificationOpen && targetScreen === Quickshell.screens[0]
    wantsKeyboardFocus: visible
    anchors {
        top: true
        left: true
    }
    margins {
        top: settings.barPosition === "top"
                ? settings.barMarginTop + settings.barHeight + 16
                : Math.round(targetScreen.height * 0.1)
        left: Math.round((targetScreen.width - implicitWidth) / 2)
    }
    onVisibleChanged: {
        if (visible)
            loadHistory();
        else if (settings.notificationOpen)
            settings.closeOverlay("notifications");
    }

    function valueFor(item, key, fallback) {
        const field = item ? item[key] : null;
        return field && field.data !== undefined ? field.data : fallback;
    }

    function loadHistory() {
        if (!historyProcess.running)
            historyProcess.running = true;
    }

    Process {
        id: historyProcess
        command: ["dunstctl", "history"]
        stdout: StdioCollector {
            id: historyOutput
            onStreamFinished: {
                try {
                    const parsed = JSON.parse(historyOutput.text);
                    const entries = parsed.data && parsed.data.length > 0 ? parsed.data[0] : [];
                    root.notifications = entries.map(item => ({
                        id: root.valueFor(item, "id", 0),
                        app: root.valueFor(item, "appname", "System"),
                        summary: root.valueFor(item, "summary", "Notification"),
                        body: root.valueFor(item, "body", ""),
                        icon: root.valueFor(item, "icon", "dialog-information"),
                        urgency: root.valueFor(item, "urgency", 1)
                    }));
                } catch (error) {
                    root.notifications = [];
                    console.warn("Dunst notification history could not be read:", error);
                }
            }
        }
        onExited: function (exitCode) {
            if (exitCode !== 0)
                root.notifications = [];
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

            RowLayout {
                Layout.fillWidth: true
                Text {
                    Layout.fillWidth: true
                    text: "Notifications"
                    color: root.theme.text
                    font.family: root.theme.fontFamily
                    font.pixelSize: root.theme.fontSizeLarge
                    font.bold: true
                }
                Text {
                    text: "DND"
                    color: root.theme.textMuted
                    font.family: root.theme.fontFamily
                    font.pixelSize: root.theme.fontSizeSmall
                    MouseArea {
                        anchors.fill: parent
                        onClicked: Quickshell.execDetached([root.settings.scriptsRoot + "/session/notification-toggle.sh"])
                    }
                }
                Text {
                    text: "Clear"
                    color: root.theme.accent
                    font.family: root.theme.fontFamily
                    font.pixelSize: root.theme.fontSizeSmall
                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            Quickshell.execDetached(["dunstctl", "history-clear"]);
                            root.notifications = [];
                        }
                    }
                }
                Text {
                    text: "×"
                    color: root.theme.textMuted
                    font.pixelSize: 22
                    MouseArea {
                        anchors.fill: parent
                        onClicked: root.settings.closeOverlay("notifications")
                    }
                }
            }

            ListView {
                id: notificationList
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                model: root.notifications
                spacing: root.theme.spacingSmall
                delegate: Rectangle {
                    id: notificationCard
                    required property var modelData
                    width: notificationList.width
                    implicitHeight: notificationBody.implicitHeight + 26
                    radius: root.theme.radius
                    color: root.theme.surface
                    border.width: 1
                    border.color: Number(modelData.urgency) >= 2 ? root.theme.warning : root.theme.border
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: root.theme.spacing
                        spacing: root.theme.spacing
                        Image {
                            source: Quickshell.iconPath(notificationCard.modelData.icon || "dialog-information", "dialog-information")
                            sourceSize.width: 24
                            sourceSize.height: 24
                            Layout.preferredWidth: 24
                            Layout.preferredHeight: 24
                        }
                        ColumnLayout {
                            id: notificationBody
                            Layout.fillWidth: true
                            spacing: 2
                            Text {
                                text: notificationCard.modelData.app + " · " + notificationCard.modelData.summary
                                color: root.theme.text
                                font.family: root.theme.fontFamily
                                font.pixelSize: root.theme.fontSize
                                font.bold: true
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }
                            Text {
                                text: notificationCard.modelData.body
                                color: root.theme.textMuted
                                font.family: root.theme.fontFamily
                                font.pixelSize: root.theme.fontSizeSmall
                                wrapMode: Text.WordWrap
                                maximumLineCount: 3
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }
                        }
                        Text {
                            text: "×"
                            color: root.theme.textMuted
                            font.pixelSize: 18
                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    Quickshell.execDetached(["dunstctl", "history-pop", String(notificationCard.modelData.id)]);
                                    root.loadHistory();
                                }
                            }
                        }
                    }
                }
                Text {
                    anchors.centerIn: parent
                    visible: root.notifications.length === 0
                    text: "Notification history is empty"
                    color: root.theme.textMuted
                    font.family: root.theme.fontFamily
                    font.pixelSize: root.theme.fontSize
                }
            }

            Text {
                Layout.fillWidth: true
                text: "History is provided by Dunst"
                color: root.theme.textMuted
                font.family: root.theme.fontFamily
                font.pixelSize: root.theme.fontSizeSmall
            }
        }
    }
}
