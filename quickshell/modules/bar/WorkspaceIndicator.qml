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
    implicitWidth: workspacePill.implicitWidth
    implicitHeight: settings.barHeight - 6

    Rectangle {
        id: workspacePill
        anchors.fill: parent
        color: root.theme.surface
        radius: 8
        border.width: 1
        border.color: root.theme.moduleBorder
        implicitWidth: workspaces.implicitWidth + 8

        RowLayout {
            id: workspaces
            anchors.fill: parent
            anchors.leftMargin: 4
            anchors.rightMargin: 4
            spacing: 0

            Repeater {
                model: root.hyprlandService.workspaces

                delegate: Rectangle {
                    id: workspaceButton

                    required property var modelData
                    readonly property bool occupied: workspaceButton.modelData.toplevels.values.length > 0

                    implicitWidth: workspaceLabel.implicitWidth + 16
                    Layout.fillHeight: true
                    Layout.topMargin: 2
                    Layout.bottomMargin: 2
                    radius: root.theme.radiusSmall
                    color: workspaceButton.modelData.active
                            ? root.theme.accent
                            : (workspaceMouse.containsMouse ? root.theme.surfaceRaised : "transparent")

                    Behavior on color {
                        ColorAnimation {
                            duration: root.theme.animationFast
                        }
                    }

                    Text {
                        id: workspaceLabel
                        anchors.centerIn: parent
                        text: workspaceButton.modelData.name.length > 0
                                ? workspaceButton.modelData.name
                                : String(workspaceButton.modelData.id)
                        color: workspaceButton.modelData.active ? root.theme.background : root.theme.textMuted
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
}
