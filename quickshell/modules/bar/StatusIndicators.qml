pragma ComponentBehavior: Bound

import Quickshell
import Quickshell.Io
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../config"

Item {
    id: root

    required property Theme theme
    required property Settings settings
    property var status: ({
            "text": "󰂲",
            "tooltip": "Status unavailable",
            "class": "unavailable"
        })

    implicitWidth: statusCluster.implicitWidth
    implicitHeight: settings.barHeight - theme.spacingSmall

    function refreshStatus() {
        if (!statusProcess.running)
            statusProcess.running = true;
    }

    Process {
        id: statusProcess
        command: ["python3", root.settings.scriptsRoot + "/desktop/quick-settings-status.py"]
        stdout: StdioCollector {
            id: statusOutput

            onStreamFinished: {
                try {
                    root.status = JSON.parse(statusOutput.text);
                } catch (error) {
                    root.status = ({
                            "text": "󰂲",
                            "tooltip": "Status could not be parsed",
                            "class": "unavailable"
                        });
                    console.warn("Quickshell status provider returned invalid JSON:", error);
                }
            }
        }
        onExited: function (exitCode, exitStatus) {
            if (exitCode !== 0)
                console.warn("Quickshell status provider exited with code", exitCode, exitStatus);
        }
    }

    Timer {
        interval: root.settings.statusRefreshInterval
        running: true
        repeat: true
        onTriggered: root.refreshStatus()
    }

    Component.onCompleted: refreshStatus()

    RowLayout {
        id: statusCluster
        anchors.fill: parent
        spacing: root.theme.spacingSmall

        Rectangle {
            id: statusButton
            color: statusMouse.containsMouse ? root.theme.surfaceRaised : root.theme.surface
            radius: root.theme.radius
            border.width: 1
            border.color: root.theme.border
            implicitWidth: statusLabel.implicitWidth + root.theme.spacingLarge * 2
            Layout.fillHeight: true

            Text {
                id: statusLabel
                anchors.centerIn: parent
                text: root.status.text || "󰂲"
                color: root.theme.text
                font.family: root.theme.fontFamily
                font.pixelSize: root.theme.fontSizeLarge
            }

            MouseArea {
                id: statusMouse
                anchors.fill: parent
                hoverEnabled: true
                onClicked: Quickshell.execDetached(["python3", root.settings.scriptsRoot + "/desktop/quick-settings.py"])
                ToolTip.visible: containsMouse
                ToolTip.text: root.status.tooltip || "Control Center"
            }
        }

        Rectangle {
            id: notificationButton
            color: notificationMouse.containsMouse ? root.theme.surfaceRaised : root.theme.surface
            radius: root.theme.radius
            border.width: 1
            border.color: root.theme.border
            implicitWidth: notificationLabel.implicitWidth + root.theme.spacingLarge * 2
            Layout.fillHeight: true

            Text {
                id: notificationLabel
                anchors.centerIn: parent
                text: "󰂚" + (Number(root.status.notifications || 0) > 0 ? " " + root.status.notifications : "")
                color: root.theme.text
                opacity: Number(root.status.notifications || 0) > 0 ? 1 : 0.6
                font.family: root.theme.fontFamily
                font.pixelSize: root.theme.fontSizeLarge
            }

            MouseArea {
                id: notificationMouse
                anchors.fill: parent
                hoverEnabled: true
                onClicked: root.settings.notificationOpen = true
                ToolTip.visible: containsMouse
                ToolTip.text: "Notifications: " + Number(root.status.notifications || 0) + " displayed"
            }
        }
    }
}
