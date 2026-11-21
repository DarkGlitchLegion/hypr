pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../config"

Item {
    id: root

    required property Theme theme

    property string icon: ""
    property string label: ""
    property bool active: false

    signal clicked()

    implicitHeight: 32
    implicitWidth: contentRow.implicitWidth + root.theme.spacingLarge * 2

    Rectangle {
        id: pill
        anchors.fill: parent
        radius: height / 2

        color: {
            if (root.active)
                return root.theme.accent
            if (mouse.containsMouse)
                return root.theme.surfaceRaised
            return root.theme.surface
        }

        Behavior on color { ColorAnimation { duration: root.theme.animationFast } }

        border.color: root.active ? "transparent" : root.theme.border
        border.width: 1

        Behavior on border.color { ColorAnimation { duration: root.theme.animationFast } }

        RowLayout {
            id: contentRow
            anchors.centerIn: parent
            spacing: root.theme.spacingSmall

            Text {
                text: root.icon
                font.family: root.theme.fontFamily
                font.pixelSize: root.theme.fontSize
                color: root.active ? root.theme.background : root.theme.textMuted
                visible: root.icon !== ""

                Behavior on color { ColorAnimation { duration: root.theme.animationFast } }
            }

            Text {
                text: root.label
                font.family: root.theme.fontFamily
                font.pixelSize: root.theme.fontSize
                color: root.active ? root.theme.background : root.theme.text
                visible: root.label !== ""

                Behavior on color { ColorAnimation { duration: root.theme.animationFast } }
            }
        }

        MouseArea {
            id: mouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor

            onClicked: {
                root.active = !root.active
                root.clicked()
            }
        }
    }
}
