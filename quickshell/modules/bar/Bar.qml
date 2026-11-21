import Quickshell
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../config"
import "../../services"
import "../launcher"
import "../settings"
import "../dashboard"
import "../osd"
import "../notifications"
import "../controlcenter"

PanelWindow {
    id: panel

    required property var modelData
    required property Theme theme
    required property Settings settings
    required property HyprlandService hyprlandService
    screen: modelData
    visible: settings.shellEnabled
    color: "transparent"
    implicitHeight: settings.barHeight
    exclusiveZone: settings.barHeight + (settings.barPosition === "top" ? settings.barMarginTop : settings.barMarginBottom)

    anchors {
        top: settings.barPosition === "top"
        bottom: settings.barPosition === "bottom"
        left: true
        right: true
    }

    margins {
        top: settings.barPosition === "top" ? settings.barMarginTop : 0
        bottom: settings.barPosition === "bottom" ? settings.barMarginBottom : 0
        left: settings.barMarginHorizontal
        right: settings.barMarginHorizontal
    }

    Item {
        anchors.fill: parent
        Rectangle {
            anchors.fill: parent
            color: Qt.rgba(12 / 255, 13 / 255, 16 / 255, panel.theme.barOpacity)
            radius: 8
            border.width: 1
            border.color: panel.theme.border
        }

        RowLayout {
            anchors.left: parent.left
            anchors.leftMargin: 4
            anchors.verticalCenter: parent.verticalCenter
            height: 26
            spacing: 4

            Rectangle {
                color: launcherMouse.containsMouse ? panel.theme.surfaceRaised : panel.theme.surface
                radius: 8
                border.width: 1
                border.color: panel.theme.moduleBorder
                implicitWidth: launcherIcon.implicitWidth + 16
                Layout.fillHeight: true

                Text {
                    id: launcherIcon
                    anchors.centerIn: parent
                    text: "󰣇"
                    color: panel.theme.accent
                    font.family: panel.theme.fontFamily
                    font.pixelSize: panel.theme.fontSizeLarge
                }

                MouseArea {
                    id: launcherMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: panel.settings.toggleOverlay("launcher")
                    ToolTip.visible: containsMouse
                    ToolTip.text: "Applications (Super + Space)"
                }
            }

            WorkspaceIndicator {
                theme: panel.theme
                settings: panel.settings
                hyprlandService: panel.hyprlandService
                visible: panel.settings.showWorkspaces
                monitorName: panel.hyprlandService.monitorFor(panel.screen) ? panel.hyprlandService.monitorFor(panel.screen).name : ""
                Layout.fillHeight: true
            }
        }

        WindowTitle {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width * 0.4
            height: parent.height
            visible: panel.settings.showWindowTitle
            theme: panel.theme
            hyprlandService: panel.hyprlandService
        }

        RowLayout {
            anchors.right: parent.right
            anchors.rightMargin: 2
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            spacing: 2

            SystemTray {
                theme: panel.theme
                settings: panel.settings
                visible: panel.settings.showSystemTray
                panelWindow: panel
                Layout.fillHeight: true
                Layout.topMargin: 3
                Layout.bottomMargin: 3
            }

            StatusIndicators {
                theme: panel.theme
                settings: panel.settings
                visible: panel.settings.showStatusIndicators
                Layout.fillHeight: true
                Layout.topMargin: 3
                Layout.bottomMargin: 3
            }

            Clock {
                theme: panel.theme
                settings: panel.settings
                visible: panel.settings.showClock
                panelWindow: panel
                Layout.fillHeight: true
                Layout.topMargin: 3
                Layout.bottomMargin: 3
            }

            Rectangle {
                visible: panel.settings.showPowerButton
                color: powerMouse.containsMouse ? panel.theme.surfaceRaised : panel.theme.surface
                radius: 8
                border.width: 1
                border.color: panel.theme.moduleBorder
                implicitWidth: powerLabel.implicitWidth + 20
                Layout.fillHeight: true
                Layout.topMargin: 3
                Layout.bottomMargin: 3

                Behavior on color {
                    ColorAnimation {
                        duration: panel.theme.animationFast
                    }
                }

                Text {
                    id: powerLabel
                    anchors.centerIn: parent
                    text: "󰐥"
                    color: powerMouse.containsMouse ? "#FFFFFF" : panel.theme.accent
                    font.family: panel.theme.fontFamily
                    font.pixelSize: panel.theme.fontSizeLarge
                    font.bold: true
                }

                MouseArea {
                    id: powerMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: {
                        panel.settings.controlCenterPage = "power";
                        panel.settings.openOverlay("controlCenter");
                    }
                }
            }
        }
    }

    Launcher {
        theme: panel.theme
        settings: panel.settings
        hostWindow: panel
        targetScreen: panel.screen
    }

    ControlCenter {
        theme: panel.theme
        settings: panel.settings
        hostWindow: panel
        targetScreen: panel.screen
    }

    SettingsPanel {
        theme: panel.theme
        settings: panel.settings
        hostWindow: panel
        targetScreen: panel.screen
    }

    Dashboard {
        theme: panel.theme
        settings: panel.settings
        hostWindow: panel
        targetScreen: panel.screen
    }

    OSD {
        theme: panel.theme
        settings: panel.settings
        hostWindow: panel
        targetScreen: panel.screen
    }

    NotificationCenter {
        theme: panel.theme
        settings: panel.settings
        hostWindow: panel
        targetScreen: panel.screen
    }
}
