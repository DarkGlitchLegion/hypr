import Quickshell
import Quickshell.Io
import QtQuick

QtObject {
    readonly property string configRoot: Quickshell.shellDir + "/.."
    readonly property string scriptsRoot: configRoot + "/scripts"
    property bool shellEnabled: true
    property bool launcherOpen: false
    property bool settingsOpen: false
    property bool dashboardOpen: false
    property bool notificationOpen: false
    property bool osdOpen: false
    property bool controlCenterOpen: false
    property string controlCenterPage: "home"
    property bool wallpaperFavoritesOnly: false
    property int osdSerial: 0
    property int osdValue: 0
    property string osdTitle: ""
    property string osdDetail: ""

    property alias barPosition: preferences.barPosition
    property alias barHeight: preferences.barHeight
    property alias barMarginTop: preferences.barMarginTop
    property alias barMarginBottom: preferences.barMarginBottom
    property alias barMarginHorizontal: preferences.barMarginHorizontal
    property alias barSpacing: preferences.barSpacing
    property alias statusRefreshInterval: preferences.statusRefreshInterval
    property alias overlayWidth: preferences.overlayWidth
    property alias overlayMaxHeight: preferences.overlayMaxHeight
    property alias searchLimit: preferences.searchLimit
    property alias showWorkspaces: preferences.showWorkspaces
    property alias showWindowTitle: preferences.showWindowTitle
    property alias showSystemTray: preferences.showSystemTray
    property alias showStatusIndicators: preferences.showStatusIndicators
    property alias showClock: preferences.showClock
    property alias showPowerButton: preferences.showPowerButton
    property alias clockFormat: preferences.clockFormat
    property alias clockFormatAlt: preferences.clockFormatAlt
    property alias accentColor: preferences.accentColor
    property alias animationSpeed: preferences.animationSpeed
    property alias favoriteAppIds: preferences.favoriteAppIds
    property alias searchHistory: preferences.searchHistory
    property alias browserCommand: preferences.browserCommand
    property alias wallpaperFavorites: preferences.wallpaperFavorites
    property alias wallpaperHistory: preferences.wallpaperHistory

    property var settingsFile: FileView {
        path: Quickshell.statePath("settings.json")
        watchChanges: true
        onAdapterUpdated: writeAdapter()
        JsonAdapter {
            id: preferences
            property string barPosition: "top"
            property int barHeight: 38
            property int barMarginTop: 7
            property int barMarginBottom: 7
            property int barMarginHorizontal: 10
            property int barSpacing: 8
            property int statusRefreshInterval: 5000
            property int overlayWidth: 620
            property int overlayMaxHeight: 680
            property int searchLimit: 12
            property bool showWorkspaces: true
            property bool showWindowTitle: true
            property bool showSystemTray: true
            property bool showStatusIndicators: true
            property bool showClock: true
            property bool showPowerButton: true
            property string clockFormat: "ddd MMM d  HH:mm"
            property string clockFormatAlt: "HH:mm:ss"
            property string accentColor: "#B4B9D0"
            property real animationSpeed: 1.0
            property list<string> favoriteAppIds: []
            property list<string> searchHistory: []
            property string browserCommand: "xdg-open"
            property list<string> wallpaperFavorites: []
            property list<string> wallpaperHistory: []
        }
    }
}
