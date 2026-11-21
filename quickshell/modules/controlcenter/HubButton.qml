pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import "../../config"

Button {
    id: control
    required property Theme theme
    hoverEnabled: true
    implicitHeight: 38
    padding: control.theme.spacingLarge
    contentItem: Text {
        text: control.text
        color: control.enabled ? control.theme.text : control.theme.textMuted
        font.family: control.theme.fontFamily
        font.pixelSize: control.theme.fontSize
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        wrapMode: Text.WordWrap
        elide: Text.ElideRight
    }
    background: Rectangle {
        radius: control.theme.radius
        color: !control.enabled ? control.theme.surface : control.down ? control.theme.surfaceRaised : control.hovered ? control.theme.surfaceRaised : control.theme.surface
        border.width: 1
        border.color: control.visualFocus ? control.theme.accent : control.theme.border
        Behavior on color { ColorAnimation { duration: control.theme.animationFast } }
    }
}
