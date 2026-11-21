pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../config"

ColumnLayout {
    id: root

    required property Theme theme
    required property string icon
    required property string label
    required property string statusText
    required property bool powered
    property bool available: true
    property bool busy: false
    property bool expanded: false
    property Component detailsComponent

    signal toggleRequested(bool enabled)
    signal detailsRequested(bool expanded)

    spacing: root.theme.spacingSmall

    Rectangle {
        Layout.fillWidth: true
        implicitHeight: 48
        radius: root.theme.radius
        color: rowHover.hovered ? root.theme.surfaceRaised : root.theme.surface
        border.width: 1
        border.color: root.theme.border

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: root.theme.spacing
            anchors.rightMargin: root.theme.spacingSmall
            spacing: root.theme.spacing

            Text {
                text: root.icon
                color: root.powered ? root.theme.accent : root.theme.textMuted
                font.family: root.theme.fontFamily
                font.pixelSize: root.theme.fontSizeLarge
                Layout.preferredWidth: 22
                horizontalAlignment: Text.AlignHCenter
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
                    text: root.statusText
                    color: root.theme.textMuted
                    font.family: root.theme.fontFamily
                    font.pixelSize: root.theme.fontSizeSmall
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }

            Switch {
                checked: root.powered
                enabled: root.available && !root.busy
                onClicked: root.toggleRequested(checked)
                indicator: Rectangle {
                    implicitWidth: 36
                    implicitHeight: 18
                    x: parent.width - width - 2
                    y: parent.height / 2 - height / 2
                    radius: height / 2
                    color: root.powered ? root.theme.accent : root.theme.surfaceRaised
                    Rectangle {
                        width: 14
                        height: 14
                        x: root.powered ? parent.width - width - 2 : 2
                        y: 2
                        radius: width / 2
                        color: root.theme.text
                        Behavior on x { NumberAnimation { duration: root.theme.animationFast } }
                    }
                }
                contentItem: Item {}
            }

            Button {
                text: root.expanded ? "⌃" : "⌄"
                enabled: root.available
                implicitWidth: 28
                implicitHeight: 30
                padding: 0
                onClicked: {
                    root.expanded = !root.expanded;
                    root.detailsRequested(root.expanded);
                }
                background: Rectangle {
                    radius: root.theme.radiusSmall
                    color: parent.hovered ? root.theme.surfaceHover : "transparent"
                }
                contentItem: Text {
                    text: parent.text
                    color: root.theme.textMuted
                    font.family: root.theme.fontFamily
                    font.pixelSize: root.theme.fontSizeLarge
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }

        HoverHandler {
            id: rowHover
        }
    }

    Loader {
        visible: root.expanded
        active: root.expanded
        Layout.fillWidth: true
        sourceComponent: root.detailsComponent
    }
}
