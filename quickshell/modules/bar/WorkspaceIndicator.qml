pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import "../../config"
import "../../services"

Item {
    id: root

    required property Theme theme
    required property Settings settings
    required property HyprlandService hyprlandService
    property string monitorName: ""
    implicitWidth: workspaces.implicitWidth + theme.spacing
    implicitHeight: settings.barHeight - theme.spacingSmall

    RowLayout {
        id: workspaces
        anchors.fill: parent
        spacing: root.theme.spacingSmall

        Repeater {
            model: root.hyprlandService.workspaces

            delegate: Rectangle {
                id: workspaceButton

                required property var modelData
                readonly property bool onThisMonitor: workspaceButton.modelData.monitor && workspaceButton.modelData.monitor.name === root.monitorName
                readonly property bool occupied: workspaceButton.modelData.toplevels.values.length > 0

                visible: onThisMonitor
                implicitWidth: workspaceLabel.implicitWidth + root.theme.spacingLarge * 2
                Layout.fillHeight: true
                radius: root.theme.radiusSmall
                color: workspaceButton.modelData.active ? root.theme.accent : (workspaceMouse.containsMouse ? root.theme.surfaceRaised : root.theme.surface)

                Behavior on color {
                    ColorAnimation {
                        duration: root.theme.animationFast
                    }
                }

                Text {
                    id: workspaceLabel
                    anchors.centerIn: parent
                    text: workspaceButton.modelData.name.length > 0 ? workspaceButton.modelData.name : String(workspaceButton.modelData.id)
                    color: workspaceButton.modelData.active ? root.theme.background : root.theme.text
                    opacity: workspaceButton.occupied || workspaceButton.modelData.active ? 1 : 0.55
                    font.family: root.theme.fontFamily
                    font.pixelSize: root.theme.fontSize
                    font.bold: workspaceButton.modelData.active
                }

                MouseArea {
                    id: workspaceMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: root.hyprlandService.activateWorkspace(workspaceButton.modelData)
                }
            }
        }
    }
}
