pragma ComponentBehavior: Bound

import Quickshell.Services.SystemTray as TrayService
import QtQuick
import QtQuick.Layouts
import "../../config"

Item {
    id: root

    required property Theme theme
    required property Settings settings
    property var panelWindow
    implicitWidth: trayItems.implicitWidth
    implicitHeight: settings.barHeight - theme.spacingSmall

    RowLayout {
        id: trayItems
        anchors.fill: parent
        spacing: root.theme.spacing

        Repeater {
            model: TrayService.SystemTray.items

            delegate: Item {
                id: trayIcon

                required property var modelData
                implicitWidth: root.theme.fontSizeLarge + root.theme.spacing
                Layout.fillHeight: true

                Image {
                    anchors.centerIn: parent
                    width: root.theme.fontSizeLarge
                    height: root.theme.fontSizeLarge
                    source: trayIcon.modelData.icon
                    fillMode: Image.PreserveAspectFit
                    smooth: true
                }

                MouseArea {
                    anchors.fill: parent
                    acceptedButtons: Qt.LeftButton | Qt.MiddleButton | Qt.RightButton
                    onClicked: function (mouse) {
                        if (mouse.button === Qt.LeftButton) {
                            trayIcon.modelData.activate();
                        } else if (mouse.button === Qt.MiddleButton) {
                            trayIcon.modelData.secondaryActivate();
                        } else {
                            const point = trayIcon.mapToItem(root.panelWindow.contentItem, mouse.x, mouse.y);
                            trayIcon.modelData.display(root.panelWindow, Math.round(point.x), Math.round(point.y));
                        }
                    }
                }
            }
        }
    }
}
