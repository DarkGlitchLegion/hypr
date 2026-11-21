import Quickshell
import Quickshell.Wayland
import QtQuick

PanelWindow {
    id: panel

    required property var targetScreen
    property bool wantsKeyboardFocus: false

    color: "transparent"
    exclusiveZone: 0
    exclusionMode: ExclusionMode.Ignore

    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: panel.visible && panel.wantsKeyboardFocus
            ? WlrKeyboardFocus.OnDemand
            : WlrKeyboardFocus.None

    onTargetScreenChanged: {
        if (targetScreen)
            screen = targetScreen;
    }

    Component.onCompleted: {
        if (targetScreen)
            screen = targetScreen;
    }
}
