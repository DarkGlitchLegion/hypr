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

    Rectangle {
        anchors.fill: parent
        color: panel.theme.background
        opacity: panel.theme.barOpacity
        radius: panel.theme.radius
        border.width: 1
        border.color: panel.theme.border

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: panel.theme.spacing
            anchors.rightMargin: panel.theme.spacing
            spacing: panel.settings.barSpacing

            WorkspaceIndicator {
                theme: panel.theme
                settings: panel.settings
                hyprlandService: panel.hyprlandService
                visible: panel.settings.showWorkspaces
                monitorName: panel.hyprlandService.monitorFor(panel.screen) ? panel.hyprlandService.monitorFor(panel.screen).name : ""
                Layout.fillHeight: true
            }

            WindowTitle {
                theme: panel.theme
                hyprlandService: panel.hyprlandService
                visible: panel.settings.showWindowTitle
                Layout.fillWidth: true
                Layout.fillHeight: true
            }

            RowLayout {
                spacing: panel.settings.barSpacing
                Layout.fillHeight: true

                SystemTray {
                    theme: panel.theme
                    settings: panel.settings
                    visible: panel.settings.showSystemTray
                    panelWindow: panel
                    Layout.fillHeight: true
                }

                StatusIndicators {
                    theme: panel.theme
                    settings: panel.settings
                    visible: panel.settings.showStatusIndicators
                    Layout.fillHeight: true
                }

                Clock {
                    theme: panel.theme
                    settings: panel.settings
                    visible: panel.settings.showClock
                    panelWindow: panel
                    Layout.fillHeight: true
                }

                Rectangle {
                    visible: panel.settings.showPowerButton
                    color: powerMouse.containsMouse ? panel.theme.surfaceRaised : panel.theme.surface
                    radius: panel.theme.radius
                    border.width: 1
                    border.color: panel.theme.border
                    implicitWidth: powerLabel.implicitWidth + panel.theme.spacingLarge * 2
                    Layout.fillHeight: true

                    Behavior on color {
                        ColorAnimation {
                            duration: panel.theme.animationFast
                        }
                    }

                    Text {
                        id: powerLabel
                        anchors.centerIn: parent
                        text: "󰐥"
                        color: panel.theme.accent
                        font.family: panel.theme.fontFamily
                        font.pixelSize: panel.theme.fontSizeLarge
                    }

                    MouseArea {
                        id: powerMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: Quickshell.execDetached([panel.settings.scriptsRoot + "/session/power-menu.sh"])
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
