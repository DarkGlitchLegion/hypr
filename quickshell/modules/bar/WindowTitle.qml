import QtQuick
import "../../config"
import "../../services"

Item {
    required property Theme theme
    required property HyprlandService hyprlandService
    implicitWidth: title.implicitWidth

    Text {
        id: title
        anchors.centerIn: parent
        width: parent.width
        text: parent.hyprlandService.activeTitle
        color: parent.theme.textMuted
        font.family: parent.theme.fontFamily
        font.pixelSize: parent.theme.fontSize
        elide: Text.ElideRight
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
}
