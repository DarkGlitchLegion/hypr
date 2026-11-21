pragma ComponentBehavior: Bound

import Quickshell
import QtQuick
import QtQuick.Layouts
import "../../config"

Item {
    id: root

    required property Theme theme
    required property Settings settings
    property var panelWindow
    property date currentDate: new Date()
    property int displayMonth: currentDate.getMonth()
    property int displayYear: currentDate.getFullYear()
    property var calendarCells: []
    property bool calendarOpen: false
    property bool alternateFormat: false

    implicitWidth: clockLabel.implicitWidth + theme.spacingLarge * 2
    implicitHeight: settings.barHeight - theme.spacingSmall

    function updateCalendarCells() {
        const firstWeekday = new Date(displayYear, displayMonth, 1).getDay();
        const dayCount = new Date(displayYear, displayMonth + 1, 0).getDate();
        const cells = [];

        for (let index = 0; index < 42; index++) {
            const day = index - firstWeekday + 1;
            cells.push(day > 0 && day <= dayCount ? day : 0);
        }

        calendarCells = cells;
    }

    function moveMonth(offset) {
        const month = new Date(displayYear, displayMonth + offset, 1);
        displayMonth = month.getMonth();
        displayYear = month.getFullYear();
        updateCalendarCells();
    }

    Component.onCompleted: updateCalendarCells()

    Timer {
        interval: 1000
        running: true
        repeat: true
        onTriggered: {
            root.currentDate = new Date();
            if (root.displayMonth === root.currentDate.getMonth() && root.displayYear === root.currentDate.getFullYear()) {
                root.updateCalendarCells();
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        color: clockMouse.containsMouse ? root.theme.surfaceRaised : root.theme.surface
        radius: root.theme.radius
        border.width: 1
        border.color: root.theme.border

        Text {
            id: clockLabel
            anchors.centerIn: parent
            text: Qt.formatDateTime(root.currentDate, root.alternateFormat ? root.settings.clockFormatAlt : root.settings.clockFormat)
            color: root.theme.text
            font.family: root.theme.fontFamily
            font.pixelSize: root.theme.fontSize
        }

        MouseArea {
            id: clockMouse
            anchors.fill: parent
            hoverEnabled: true
            acceptedButtons: Qt.LeftButton | Qt.RightButton
            onClicked: function (mouse) {
                if (mouse.button === Qt.RightButton) {
                    root.alternateFormat = !root.alternateFormat;
                } else {
                    if (!root.calendarOpen) {
                        root.displayMonth = root.currentDate.getMonth();
                        root.displayYear = root.currentDate.getFullYear();
                        root.updateCalendarCells();
                    }
                    root.calendarOpen = !root.calendarOpen;
                }
            }
            onWheel: function (wheel) {
                if (!root.calendarOpen) {
                    root.displayMonth = root.currentDate.getMonth();
                    root.displayYear = root.currentDate.getFullYear();
                    root.updateCalendarCells();
                    root.calendarOpen = true;
                }
                root.moveMonth(wheel.angleDelta.y > 0 ? -1 : 1);
            }
        }
    }

    PopupWindow {
        id: calendarPopup
        anchor.item: root
        anchor.edges: root.settings.barPosition === "top" ? Edges.Bottom | Edges.Right : Edges.Top | Edges.Right
        anchor.gravity: root.settings.barPosition === "top" ? Edges.Bottom | Edges.Right : Edges.Top | Edges.Right
        anchor.margins.top: root.theme.spacingSmall
        visible: root.calendarOpen
        implicitWidth: root.theme.calendarWidth
        implicitHeight: root.theme.calendarHeight
        color: "transparent"
        onVisibleChanged: if (!calendarPopup.visible)
            root.calendarOpen = false

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
                        text: "‹"
                        color: root.theme.accent
                        font.pixelSize: root.theme.fontSizeLarge
                        MouseArea {
                            anchors.fill: parent
                            onClicked: root.moveMonth(-1)
                        }
                    }

                    Text {
                        Layout.fillWidth: true
                        text: Qt.formatDate(new Date(root.displayYear, root.displayMonth, 1), "MMMM yyyy")
                        color: root.theme.text
                        font.family: root.theme.fontFamily
                        font.pixelSize: root.theme.fontSize
                        horizontalAlignment: Text.AlignHCenter
                    }

                    Text {
                        text: "›"
                        color: root.theme.accent
                        font.pixelSize: root.theme.fontSizeLarge
                        MouseArea {
                            anchors.fill: parent
                            onClicked: root.moveMonth(1)
                        }
                    }
                }

                GridLayout {
                    columns: 7
                    rowSpacing: root.theme.spacingSmall
                    columnSpacing: root.theme.spacingSmall
                    Layout.fillWidth: true

                    Repeater {
                        model: ["S", "M", "T", "W", "T", "F", "S"]

                        Text {
                            required property string modelData
                            text: modelData
                            color: root.theme.textMuted
                            font.family: root.theme.fontFamily
                            font.pixelSize: root.theme.fontSizeSmall
                            horizontalAlignment: Text.AlignHCenter
                            Layout.fillWidth: true
                        }
                    }

                    Repeater {
                        model: root.calendarCells

                        Rectangle {
                            id: dayCell

                            required property int modelData
                            readonly property bool isToday: modelData > 0 && root.displayYear === root.currentDate.getFullYear() && root.displayMonth === root.currentDate.getMonth() && modelData === root.currentDate.getDate()

                            Layout.fillWidth: true
                            implicitHeight: 28
                            radius: root.theme.radiusSmall
                            color: isToday ? root.theme.accent : "transparent"

                            Text {
                                anchors.centerIn: parent
                                text: dayCell.modelData > 0 ? String(dayCell.modelData) : ""
                                color: parent.isToday ? root.theme.background : root.theme.text
                                font.family: root.theme.fontFamily
                                font.pixelSize: root.theme.fontSizeSmall
                            }
                        }
                    }
                }
            }
        }
    }
}
