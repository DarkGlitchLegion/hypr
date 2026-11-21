import Quickshell.Hyprland
import QtQuick

QtObject {
    readonly property var workspaces: Hyprland.workspaces
    readonly property var activeToplevel: Hyprland.activeToplevel
    readonly property string activeTitle: activeToplevel && activeToplevel.title.length > 0 ? activeToplevel.title : "Arch Linux — Hyprland"

    function monitorFor(screen) {
        return Hyprland.monitorFor(screen);
    }

    function activateWorkspace(workspace) {
        if (workspace)
            workspace.activate();
    }
}
