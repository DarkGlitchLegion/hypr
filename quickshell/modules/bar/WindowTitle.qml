import QtQuick
import "../../config"
import "../../services"

Item {
    required property Theme theme
    required property HyprlandService hyprlandService
    implicitWidth: 0

    Text {
        id: title
        anchors.centerIn: parent
        width: parent.width
        text: {
            const active = parent.hyprlandService.activeTitle;
            return active.length > 0 ? active.slice(0, 45) : "Arch Linux — Hyprland";
        }
        color: parent.theme.textMuted
        font.family: parent.theme.fontFamily
        font.pixelSize: parent.theme.fontSize
        elide: Text.ElideRight
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
}
