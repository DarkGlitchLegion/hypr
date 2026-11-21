pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../config"

Rectangle {
    id: root

    required property Theme theme
    required property string icon
    required property string label
    property string detail: ""
    property bool checked: false
    property bool busy: false
    property bool available: true
    signal activated(bool enabled)

    implicitHeight: 48
    radius: theme.radius
    color: interactionArea.containsMouse ? theme.surfaceRaised : theme.surface
    border.width: 1
    border.color: theme.surfaceRaised
    activeFocusOnTab: true

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 10
        anchors.rightMargin: 10
        spacing: 10

        Text {
            text: root.icon
            color: root.theme.accent
            font.family: root.theme.fontFamily
            font.pixelSize: root.theme.fontSizeLarge
            horizontalAlignment: Text.AlignHCenter
            Layout.preferredWidth: 22
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 1

            Text {
                text: root.label
                color: root.theme.text
                font.family: root.theme.fontFamily
                font.pixelSize: root.theme.fontSize
            }

            Text {
                visible: root.detail.length > 0
                text: root.detail
                color: root.theme.textMuted
                font.family: root.theme.fontFamily
                font.pixelSize: root.theme.fontSizeSmall
                elide: Text.ElideRight
                Layout.fillWidth: true
            }
        }

        Rectangle {
            implicitWidth: 36
            implicitHeight: 18
            radius: 9
            color: root.checked ? root.theme.accent : "#333340"
            opacity: root.busy ? 0.55 : 1
            Behavior on color { ColorAnimation { duration: root.theme.animationFast } }

            Rectangle {
                width: 14
                height: 14
                x: root.checked ? parent.width - width - 2 : 2
                y: 2
                radius: 7
                color: root.checked ? root.theme.background : root.theme.text
                Behavior on x { NumberAnimation { duration: root.theme.animationFast } }
            }
        }
    }

    MouseArea {
        id: interactionArea
        anchors.fill: parent
        hoverEnabled: true
        enabled: root.available && !root.busy
        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: root.activated(!root.checked)
    }

    Keys.onSpacePressed: {
        if (root.available && !root.busy)
            root.activated(!root.checked);
    }
    Keys.onReturnPressed: {
        if (root.available && !root.busy)
            root.activated(!root.checked);
    }

    ToolTip.visible: interactionArea.containsMouse
    ToolTip.text: !root.available ? "This control is unavailable" : root.busy ? "Applying…" : root.detail
}
