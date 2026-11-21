pragma ComponentBehavior: Bound

import Quickshell.Io
import QtQuick
import QtQuick.Controls
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

    implicitWidth: statusLabel.implicitWidth + 24
    implicitHeight: settings.barHeight - 6

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

    Rectangle {
        id: statusButton
        anchors.fill: parent
        color: statusMouse.containsMouse ? root.theme.surfaceRaised : root.theme.surface
        radius: 8
        border.width: 1
        border.color: (root.status.class || "").includes("sec-running")
                ? Qt.rgba(163 / 255, 190 / 255, 140 / 255, 0.35)
                : root.theme.moduleBorder

        Text {
            id: statusLabel
            anchors.centerIn: parent
            text: root.status.text || "󰂲"
            color: root.theme.text
            font.family: root.theme.fontFamily
            font.pixelSize: root.theme.fontSizeLarge
            font.letterSpacing: 2
        }

        MouseArea {
            id: statusMouse
            anchors.fill: parent
            hoverEnabled: true
            onClicked: root.settings.toggleQuickControls()
            ToolTip.visible: containsMouse
            ToolTip.text: (root.status.tooltip || "Quick Settings")
                    + "\nNotifications: " + Number(root.status.notifications || 0) + " displayed"
        }
    }
}
