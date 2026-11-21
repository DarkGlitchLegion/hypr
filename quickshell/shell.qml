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
                shellSettings.launcherOpen = false;
                shellSettings.settingsOpen = false;
                shellSettings.dashboardOpen = false;
                shellSettings.notificationOpen = false;
                shellSettings.osdOpen = false;
                shellSettings.controlCenterOpen = false;
            }
        }

        function reload(): void {
            Quickshell.reload(true);
        }

        function toggleLauncher(): void {
            shellSettings.launcherOpen = !shellSettings.launcherOpen;
        }

        function openLauncher(): void {
            shellSettings.launcherOpen = true;
        }

        function toggleDashboard(): void {
            shellSettings.dashboardOpen = !shellSettings.dashboardOpen;
        }

        function toggleNotifications(): void {
            shellSettings.notificationOpen = !shellSettings.notificationOpen;
        }

        function toggleSettings(): void {
            shellSettings.settingsOpen = !shellSettings.settingsOpen;
        }

        function openHub(page: string): void {
            shellSettings.controlCenterPage = page;
            shellSettings.controlCenterOpen = true;
        }

        function toggleHub(): void {
            shellSettings.controlCenterOpen = !shellSettings.controlCenterOpen;
            if (shellSettings.controlCenterOpen)
                shellSettings.controlCenterPage = "home";
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
