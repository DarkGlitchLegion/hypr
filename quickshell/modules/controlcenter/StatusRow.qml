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
    property string detail: ""
    property Item rightItem: null    // optional slot: a Switch, Text, etc.

    implicitHeight: 40
    implicitWidth: 200

    RowLayout {
        anchors {
            fill: parent
            leftMargin: root.theme.spacingSmall
            rightMargin: root.theme.spacingSmall
        }
        spacing: root.theme.spacing

        // Icon
        Text {
            text: root.icon
            font.family: root.theme.fontFamily
            font.pixelSize: root.theme.fontSizeLarge
            color: root.theme.accent
            Layout.preferredWidth: 22
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            visible: root.icon !== ""

            Behavior on color { ColorAnimation { duration: root.theme.animationFast } }
        }

        // Label + detail
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 1

            Text {
                text: root.label
                font.family: root.theme.fontFamily
                font.pixelSize: root.theme.fontSize
                color: root.theme.text
                elide: Text.ElideRight
                Layout.fillWidth: true
            }

            Text {
                text: root.detail
                font.family: root.theme.fontFamily
                font.pixelSize: root.theme.fontSizeSmall
                color: root.theme.textMuted
                elide: Text.ElideRight
                visible: root.detail !== ""
                Layout.fillWidth: true
            }
        }

        // Right-side slot
        Item {
            id: rightSlot
            Layout.preferredWidth: root.rightItem ? root.rightItem.implicitWidth : 0
            Layout.preferredHeight: root.rightItem ? root.rightItem.implicitHeight : 0
            visible: root.rightItem !== null

            onChildrenChanged: {
                if (root.rightItem) {
                    root.rightItem.parent = rightSlot
                    root.rightItem.anchors.centerIn = rightSlot
                }
            }
        }
    }

    onRightItemChanged: {
        if (root.rightItem) {
            root.rightItem.parent = rightSlot
            root.rightItem.anchors.centerIn = rightSlot
        }
    }
}
