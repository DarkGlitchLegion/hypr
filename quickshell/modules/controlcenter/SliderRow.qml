pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../config"

RowLayout {
    id: root

    required property Theme theme
    required property string icon
    required property real value
    property real to: 100
    property bool interactive: true
    readonly property real boundedValue: Math.max(0, Math.min(to, value))
    signal moved(real value)

    spacing: 8

    Text {
        text: root.icon
        color: root.theme.textMuted
        font.family: root.theme.fontFamily
        font.pixelSize: root.theme.fontSizeLarge
        horizontalAlignment: Text.AlignHCenter
        Layout.preferredWidth: 20
    }

    Slider {
        id: slider
        from: 0
        to: root.to
        value: root.boundedValue
        enabled: root.interactive
        Layout.fillWidth: true
        onMoved: root.moved(value)

        background: Rectangle {
            x: slider.leftPadding
            y: slider.topPadding + slider.availableHeight / 2 - height / 2
            width: slider.availableWidth
            height: 4
            radius: 4
            color: root.theme.surfaceRaised

            Rectangle {
                width: slider.visualPosition * parent.width
                height: parent.height
                radius: 4
                color: root.theme.accent
            }
        }

        handle: Rectangle {
            x: slider.leftPadding + slider.visualPosition * (slider.availableWidth - width)
            y: slider.topPadding + slider.availableHeight / 2 - height / 2
            width: 14
            height: 14
            radius: 7
            color: slider.pressed ? "#FFFFFF" : root.theme.text
            border.width: 0
        }
    }

    Text {
        text: Math.round(root.boundedValue) + "%"
        color: root.theme.textMuted
        font.family: root.theme.fontFamily
        font.pixelSize: root.theme.fontSizeSmall
        horizontalAlignment: Text.AlignRight
        Layout.preferredWidth: 34
    }
}
