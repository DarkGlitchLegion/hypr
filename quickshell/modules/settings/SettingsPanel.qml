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

    anchor.window: hostWindow
    anchor.rect.x: Math.round((hostWindow.width - 420) / 2)
    anchor.rect.y: settings.barPosition === "top" ? Math.round(targetScreen.height * 0.13) : Math.round(settings.barHeight + settings.barMarginBottom - targetScreen.height * 0.87)
    implicitWidth: 420
    implicitHeight: 500
    visible: settings.shellEnabled && settings.settingsOpen && targetScreen === Quickshell.screens[0]
    grabFocus: true
    color: "transparent"
    onVisibleChanged: if (!visible && settings.settingsOpen) settings.settingsOpen = false

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
                    text: "Shell settings"
                    color: root.theme.text
                    font.family: root.theme.fontFamily
                    font.pixelSize: root.theme.fontSizeLarge
                    font.bold: true
                }
                Text {
                    text: "×"
                    color: root.theme.textMuted
                    font.pixelSize: 22
                    MouseArea {
                        anchors.fill: parent
                        onClicked: root.settings.settingsOpen = false
                    }
                }
            }

            Text {
                text: "Bar position"
                color: root.theme.textMuted
                font.family: root.theme.fontFamily
                font.pixelSize: root.theme.fontSizeSmall
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: root.theme.spacingSmall
                Repeater {
                    model: ["top", "bottom"]
                    delegate: Rectangle {
                        id: positionOption
                        required property string modelData
                        Layout.fillWidth: true
                        implicitHeight: 34
                        radius: root.theme.radiusSmall
                        color: root.settings.barPosition === modelData ? root.theme.accent : root.theme.surface
                        Text {
                            anchors.centerIn: parent
                            text: positionOption.modelData === "top" ? "Top" : "Bottom"
                            color: root.settings.barPosition === positionOption.modelData ? root.theme.background : root.theme.text
                            font.family: root.theme.fontFamily
                            font.pixelSize: root.theme.fontSize
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: root.settings.barPosition = positionOption.modelData
                        }
                    }
                }
            }

            Text {
                text: "Visible modules"
                color: root.theme.textMuted
                font.family: root.theme.fontFamily
                font.pixelSize: root.theme.fontSizeSmall
            }
            GridLayout {
                Layout.fillWidth: true
                columns: 2
                rowSpacing: root.theme.spacingSmall
                columnSpacing: root.theme.spacingSmall
                Repeater {
                    model: [
                        { label: "Workspaces", key: "showWorkspaces" },
                        { label: "Window title", key: "showWindowTitle" },
                        { label: "System tray", key: "showSystemTray" },
                        { label: "Status & DND", key: "showStatusIndicators" },
                        { label: "Clock", key: "showClock" },
                        { label: "Power button", key: "showPowerButton" }
                    ]
                    delegate: Rectangle {
                        id: toggleCard
                        required property var modelData
                        Layout.fillWidth: true
                        implicitHeight: 34
                        radius: root.theme.radiusSmall
                        color: root.theme.surface
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: root.theme.spacing
                            anchors.rightMargin: root.theme.spacing
                            Text {
                                Layout.fillWidth: true
                                text: toggleCard.modelData.label
                                color: root.theme.text
                                font.family: root.theme.fontFamily
                                font.pixelSize: root.theme.fontSizeSmall
                            }
                            Switch {
                                checked: root.settings[toggleCard.modelData.key]
                                onToggled: root.settings[toggleCard.modelData.key] = checked
                                scale: 0.75
                            }
                        }
                    }
                }
            }

            Text {
                text: "Accent"
                color: root.theme.textMuted
                font.family: root.theme.fontFamily
                font.pixelSize: root.theme.fontSizeSmall
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: root.theme.spacing
                Repeater {
                    model: ["#B4B9D0", "#B8D7CA", "#E6B8AE", "#D8C99A", "#B8C8E8"]
                    delegate: Rectangle {
                        required property string modelData
                        width: 34
                        height: 26
                        radius: root.theme.radiusSmall
                        color: modelData
                        border.width: root.settings.accentColor === modelData ? 2 : 0
                        border.color: root.theme.text
                        MouseArea {
                            anchors.fill: parent
                            onClicked: root.settings.accentColor = parent.modelData
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Text {
                    Layout.fillWidth: true
                    text: "Animation speed"
                    color: root.theme.textMuted
                    font.family: root.theme.fontFamily
                    font.pixelSize: root.theme.fontSizeSmall
                }
                Text {
                    text: Math.round(root.settings.animationSpeed * 100) + "%"
                    color: root.theme.text
                    font.family: root.theme.fontFamily
                    font.pixelSize: root.theme.fontSizeSmall
                }
            }
            Slider {
                Layout.fillWidth: true
                from: 0.25
                to: 1.5
                stepSize: 0.05
                value: root.settings.animationSpeed
                onMoved: root.settings.animationSpeed = value
            }
            Text {
                Layout.fillWidth: true
                text: "Preferences save automatically. Additional device controls use the existing system managers."
                wrapMode: Text.WordWrap
                color: root.theme.textMuted
                font.family: root.theme.fontFamily
                font.pixelSize: root.theme.fontSizeSmall
            }
        }
    }
}
