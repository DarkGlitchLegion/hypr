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
    property var metrics: []
    readonly property string statsCommand: "import json,psutil; m=psutil.virtual_memory(); d=psutil.disk_usage('/'); b=psutil.sensors_battery(); print(json.dumps([{'label':'Processor','value':psutil.cpu_percent(interval=0.15),'detail':str(psutil.cpu_count(logical=True))+' logical cores'},{'label':'Memory','value':m.percent,'detail':f'{m.used/1073741824:.1f} / {m.total/1073741824:.1f} GiB'},{'label':'Storage','value':d.percent,'detail':f'{d.used/1000000000000:.2f} / {d.total/1000000000000:.2f} TB'},{'label':'Battery','value':b.percent if b else -1,'detail':('Charging' if b.power_plugged else 'On battery') if b else 'No battery detected'}]))"

    implicitWidth: 560
    implicitHeight: 430
    visible: settings.shellEnabled && settings.dashboardOpen && targetScreen === Quickshell.screens[0]
    wantsKeyboardFocus: visible
    anchors {
        top: true
        left: true
    }
    margins {
        top: settings.barPosition === "top"
                ? Math.round(targetScreen.height * 0.1)
                : Math.round(settings.barHeight + settings.barMarginBottom - targetScreen.height * 0.9)
        left: Math.round((targetScreen.width - implicitWidth) / 2)
    }
    onVisibleChanged: {
        if (visible)
            refreshStats();
        else if (settings.dashboardOpen)
            settings.closeOverlay("dashboard");
    }

    function refreshStats() {
        if (!statsProcess.running)
            statsProcess.running = true;
    }

    Process {
        id: statsProcess
        command: ["python3", "-c", root.statsCommand]
        stdout: StdioCollector {
            id: statsOutput
            onStreamFinished: {
                try {
                    root.metrics = JSON.parse(statsOutput.text);
                } catch (error) {
                    root.metrics = [];
                    console.warn("Dashboard metrics could not be read:", error);
                }
            }
        }
        onExited: function (exitCode) {
            if (exitCode !== 0)
                root.metrics = [];
        }
    }

    Timer {
        interval: 5000
        running: root.visible
        repeat: true
        onTriggered: root.refreshStats()
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
                    text: Qt.formatDateTime(new Date(), "dddd, MMMM d")
                    color: root.theme.text
                    font.family: root.theme.fontFamily
                    font.pixelSize: root.theme.fontSizeLarge
                    font.bold: true
                }
                Text {
                    text: Qt.formatDateTime(new Date(), "HH:mm")
                    color: root.theme.accent
                    font.family: root.theme.fontFamily
                    font.pixelSize: root.theme.fontSizeLarge
                }
                Text {
                    text: "×"
                    color: root.theme.textMuted
                    font.pixelSize: 22
                    MouseArea {
                        anchors.fill: parent
                        onClicked: root.settings.closeOverlay("dashboard")
                    }
                }
            }

            GridLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                columns: 2
                rowSpacing: root.theme.spacing
                columnSpacing: root.theme.spacing
                Repeater {
                    model: root.metrics
                    delegate: Rectangle {
                        id: metricCard
                        required property var modelData
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        implicitHeight: 130
                        radius: root.theme.radius
                        color: root.theme.surface
                        border.width: 1
                        border.color: root.theme.border
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: root.theme.spacingLarge
                            spacing: root.theme.spacingSmall
                            Text {
                                text: metricCard.modelData.label
                                color: root.theme.textMuted
                                font.family: root.theme.fontFamily
                                font.pixelSize: root.theme.fontSize
                            }
                            Text {
                                Layout.fillWidth: true
                                text: Number(metricCard.modelData.value) < 0 ? "—" : Math.round(metricCard.modelData.value) + "%"
                                color: root.theme.text
                                font.family: root.theme.fontFamily
                                font.pixelSize: 24
                                font.bold: true
                            }
                            Rectangle {
                                Layout.fillWidth: true
                                implicitHeight: 4
                                radius: 2
                                color: root.theme.surfaceRaised
                                Rectangle {
                                    width: parent.width * Math.max(0, Math.min(100, Number(metricCard.modelData.value))) / 100
                                    height: parent.height
                                    radius: parent.radius
                                    color: root.theme.accent
                                }
                            }
                            Text {
                                Layout.fillWidth: true
                                text: metricCard.modelData.detail
                                color: root.theme.textMuted
                                font.family: root.theme.fontFamily
                                font.pixelSize: root.theme.fontSizeSmall
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
                Text {
                    Layout.columnSpan: 2
                    Layout.alignment: Qt.AlignHCenter
                    visible: root.metrics.length === 0
                    text: "System metrics will appear here"
                    color: root.theme.textMuted
                    font.family: root.theme.fontFamily
                    font.pixelSize: root.theme.fontSize
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Text {
                    Layout.fillWidth: true
                    text: "Updated every 5 seconds while open"
                    color: root.theme.textMuted
                    font.family: root.theme.fontFamily
                    font.pixelSize: root.theme.fontSizeSmall
                }
                Text {
                    text: "Refresh"
                    color: root.theme.accent
                    font.family: root.theme.fontFamily
                    font.pixelSize: root.theme.fontSizeSmall
                    MouseArea {
                        anchors.fill: parent
                        onClicked: root.refreshStats()
                    }
                }
            }
        }
    }
}
