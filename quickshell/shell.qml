pragma ComponentBehavior: Bound

import Quickshell
import Quickshell.Io
import "config"
import "modules/bar"
import "services"

ShellRoot {
    Theme {
        id: shellTheme
        accent: shellSettings.accentColor
        animationScale: shellSettings.animationSpeed
    }

    Settings {
        id: shellSettings
    }

    HyprlandService {
        id: shellHyprland
    }

    IpcHandler {
        target: "hyprshell"

        function setEnabled(enabled: bool): void {
            shellSettings.shellEnabled = enabled;
            if (!enabled) {
                shellSettings.closeOverlays();
                shellSettings.osdOpen = false;
            }
        }

        function reload(): void {
            Quickshell.reload(true);
        }

        function toggleLauncher(): void {
            shellSettings.toggleOverlay("launcher");
        }

        function openLauncher(): void {
            shellSettings.openOverlay("launcher");
        }

        function toggleDashboard(): void {
            shellSettings.toggleOverlay("dashboard");
        }

        function toggleNotifications(): void {
            shellSettings.toggleOverlay("notifications");
        }

        function toggleSettings(): void {
            shellSettings.toggleOverlay("settings");
        }

        function openHub(page: string): void {
            shellSettings.controlCenterPage = page;
            shellSettings.openOverlay("controlCenter");
        }

        function toggleHub(): void {
            shellSettings.toggleOverlay("controlCenter");
            if (shellSettings.controlCenterOpen)
                shellSettings.controlCenterPage = "home";
        }

        function toggleQuickControls(): void {
            shellSettings.toggleQuickControls();
        }

        function closeFocusedOrOverlay(): void {
            if (shellSettings.activeOverlay.length > 0)
                shellSettings.closeOverlays();
            else
                Quickshell.execDetached(["hyprctl", "dispatch", "killactive"]);
        }

        function showOsd(title: string, value: int, detail: string): void {
            shellSettings.osdTitle = title;
            shellSettings.osdValue = Math.max(0, Math.min(100, value));
            shellSettings.osdDetail = detail;
            shellSettings.osdOpen = true;
            shellSettings.osdSerial += 1;
        }
    }

    Variants {
        model: Quickshell.screens

        Bar {
            theme: shellTheme
            settings: shellSettings
            hyprlandService: shellHyprland
            screen: modelData
        }
    }
}
