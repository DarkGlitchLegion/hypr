pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../config"

Item {
    id: root

    required property Theme theme

    property string icon: ""
    property real value: 0.5          // 0.0 – 1.0
    property bool muted: false
    property string muteIcon: "󰖁"
    property string unmuteIcon: "󰕾"
    property bool showMuteButton: true

    signal valueChanged(real newValue)
    signal muteToggled(bool muted)

    implicitHeight: 36
    implicitWidth: 200

    RowLayout {
        anchors.fill: parent
        spacing: root.theme.spacingSmall

        // Leading icon
        Text {
            text: root.icon
            font.family: root.theme.fontFamily
            font.pixelSize: root.theme.fontSizeLarge
            color: root.theme.textMuted
            visible: root.icon !== ""
            Layout.preferredWidth: 18
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }

        // Slider track + fill
        Item {
            Layout.fillWidth: true
            implicitHeight: 6

            Rectangle {
                id: track
                anchors.fill: parent
                radius: height / 2
                color: root.theme.border

                Behavior on color { ColorAnimation { duration: root.theme.animationFast } }

                // Filled portion
                Rectangle {
                    id: fill
                    width: parent.width * root.value
                    height: parent.height
                    radius: parent.radius
                    color: root.muted ? root.theme.textMuted : root.theme.accent
                    clip: true

                    Behavior on width  { NumberAnimation  { duration: root.theme.animationFast; easing.type: Easing.OutCubic } }
                    Behavior on color  { ColorAnimation   { duration: root.theme.animationFast } }
                }

                // Invisible MouseArea spanning the whole track
                MouseArea {
                    id: trackMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor

                    onPositionChanged: (mouse) => {
                        if (pressed) {
                            let v = Math.max(0, Math.min(1, mouse.x / width))
                            root.value = v
                            root.valueChanged(v)
                        }
                    }
                    onClicked: (mouse) => {
                        let v = Math.max(0, Math.min(1, mouse.x / width))
                        root.value = v
                        root.valueChanged(v)
                    }
                }

                // Thumb
                Rectangle {
                    x: root.value * (parent.width - width)
                    y: (parent.height - height) / 2
                    width: trackMouse.containsMouse || trackMouse.pressed ? 14 : 10
                    height: width
                    radius: width / 2
                    color: root.theme.text
                    visible: trackMouse.containsMouse || trackMouse.pressed

                    Behavior on width { NumberAnimation { duration: root.theme.animationFast; easing.type: Easing.OutBack } }
                    Behavior on color { ColorAnimation   { duration: root.theme.animationFast } }
                }
            }
        }

        // Percentage label
        Text {
            text: Math.round(root.value * 100) + "%"
            font.family: root.theme.fontFamily
            font.pixelSize: root.theme.fontSizeSmall
            color: root.theme.textMuted
            Layout.preferredWidth: 28
            horizontalAlignment: Text.AlignRight
            verticalAlignment: Text.AlignVCenter

            Behavior on color { ColorAnimation { duration: root.theme.animationFast } }
        }

        // Mute button
        Item {
            visible: root.showMuteButton
            Layout.preferredWidth: 24
            Layout.preferredHeight: 24

            Rectangle {
                id: muteBg
                anchors.fill: parent
                radius: root.theme.radiusSmall
                color: muteMouse.containsMouse ? root.theme.border : "transparent"

                Behavior on color { ColorAnimation { duration: root.theme.animationFast } }

                Text {
                    anchors.centerIn: parent
                    text: root.muted ? root.muteIcon : root.unmuteIcon
                    font.family: root.theme.fontFamily
                    font.pixelSize: root.theme.fontSize
                    color: root.muted ? root.theme.error : root.theme.textMuted

                    Behavior on color { ColorAnimation { duration: root.theme.animationFast } }
                }

                MouseArea {
                    id: muteMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        root.muted = !root.muted
                        root.muteToggled(root.muted)
                    }
                }
            }
        }
    }
}
