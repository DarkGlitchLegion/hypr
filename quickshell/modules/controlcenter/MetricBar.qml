pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../config"

Item {
    id: root

    required property Theme theme

    property string label: "CPU"
    property real value: 0.0           // 0.0 – 1.0
    property color barColor: root.theme.accent

    implicitHeight: 28
    implicitWidth: 160

    RowLayout {
        anchors.fill: parent
        spacing: root.theme.spacing

        // Label
        Text {
            text: root.label
            font.family: root.theme.fontFamily
            font.pixelSize: root.theme.fontSizeSmall
            color: root.theme.textMuted
            Layout.preferredWidth: 32
            verticalAlignment: Text.AlignVCenter
        }

        // Progress bar track
        Item {
            Layout.fillWidth: true
            implicitHeight: 6

            Rectangle {
                anchors.fill: parent
                radius: height / 2
                color: root.theme.border

                Behavior on color { ColorAnimation { duration: root.theme.animationFast } }

                Rectangle {
                    width: parent.width * root.value
                    height: parent.height
                    radius: parent.radius
                    color: root.barColor

                    Behavior on width { NumberAnimation { duration: root.theme.animation; easing.type: Easing.OutCubic } }
                    Behavior on color { ColorAnimation { duration: root.theme.animationFast } }
                }
            }
        }

        // Percentage label
        Text {
            text: Math.round(root.value * 100) + "%"
            font.family: root.theme.fontFamily
            font.pixelSize: root.theme.fontSizeSmall
            color: root.theme.textMuted
            Layout.preferredWidth: 30
            horizontalAlignment: Text.AlignRight
            verticalAlignment: Text.AlignVCenter

            Behavior on color { ColorAnimation { duration: root.theme.animationFast } }
        }
    }
}
