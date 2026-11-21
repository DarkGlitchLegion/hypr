pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../config"

Button {
    id: root

    required property string pageId
    required property var pageData
    required property Theme theme
    required property bool active
    signal navigate()

    implicitHeight: 36
    hoverEnabled: true
    padding: 0
    onClicked: navigate()

    background: Rectangle {
        color: root.active ? root.theme.surfaceRaised
                : root.hovered ? root.theme.surface : "transparent"
        radius: root.theme.radiusSmall
        Behavior on color { ColorAnimation { duration: root.theme.animationFast } }

        Rectangle {
            width: 3
            height: parent.height
            color: root.active ? root.theme.accent : "transparent"
            Behavior on color { ColorAnimation { duration: root.theme.animationFast } }
        }
    }

    contentItem: RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 10
        anchors.rightMargin: root.theme.spacing
        spacing: root.theme.spacing

        Text {
            text: root.pageData.icon || ""
            color: root.active ? root.theme.accent : root.theme.textMuted
            font.pixelSize: 16
            Behavior on color { ColorAnimation { duration: root.theme.animationFast } }
        }
        Text {
            text: root.pageData.label || root.pageId
            color: root.active ? root.theme.text : root.theme.textMuted
            font.family: root.theme.fontFamily
            font.pixelSize: root.theme.fontSize
            Layout.fillWidth: true
            elide: Text.ElideRight
            Behavior on color { ColorAnimation { duration: root.theme.animationFast } }
        }
    }
}
