import Quickshell
import QtQuick
import QtQuick.Layouts
import "../../config"

PopupWindow {
    id: root

    required property Theme theme
    required property Settings settings
    required property var hostWindow
    required property var targetScreen
    property int shownSerial: 0

    anchor.window: hostWindow
    anchor.rect.x: Math.round((hostWindow.width - 300) / 2)
    anchor.rect.y: settings.barPosition === "top" ? settings.barHeight + 20 : -104
    implicitWidth: 300
    implicitHeight: 82
    visible: settings.shellEnabled && settings.osdOpen && targetScreen === Quickshell.screens[0]
    color: "transparent"

    Timer {
        id: dismissTimer
        interval: 1350
        repeat: false
        running: root.visible
        onTriggered: root.settings.osdOpen = false
    }

    Connections {
        target: root.settings
        function onOsdSerialChanged() {
            if (root.settings.osdSerial !== root.shownSerial) {
                root.shownSerial = root.settings.osdSerial;
                dismissTimer.restart();
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        color: root.theme.background
        radius: root.theme.radiusLarge
        border.width: 1
        border.color: root.theme.border

        RowLayout {
            anchors.fill: parent
            anchors.margins: root.theme.spacingLarge
            spacing: root.theme.spacingLarge
            Text {
                text: root.settings.osdTitle === "Brightness" ? "󰃠" : "󰕾"
                color: root.theme.accent
                font.family: root.theme.fontFamily
                font.pixelSize: 28
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: root.theme.spacingSmall
                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        Layout.fillWidth: true
                        text: root.settings.osdTitle
                        color: root.theme.text
                        font.family: root.theme.fontFamily
                        font.pixelSize: root.theme.fontSize
                    }
                    Text {
                        text: root.settings.osdDetail
                        color: root.theme.textMuted
                        font.family: root.theme.fontFamily
                        font.pixelSize: root.theme.fontSizeSmall
                    }
                }
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 6
                    radius: 3
                    color: root.theme.surfaceRaised
                    Rectangle {
                        width: parent.width * root.settings.osdValue / 100
                        height: parent.height
                        radius: parent.radius
                        color: root.theme.accent
                    }
                }
            }
        }
    }
}
