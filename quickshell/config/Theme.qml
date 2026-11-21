import QtQuick

QtObject {
    readonly property color background: "#0C0D10"
    readonly property color surface: "#17191F"
    readonly property color surfaceRaised: "#202126"
    readonly property color text: "#D5D5D5"
    readonly property color textMuted: "#888888"
    property color accent: "#B4B9D0"
    readonly property color border: "#333333"
    readonly property color success: "#A3BE8C"
    readonly property color warning: "#EBCB8B"
    readonly property color error: "#BF616A"

    readonly property string fontFamily: "JetBrainsMono Nerd Font"
    readonly property int fontSizeSmall: 10
    readonly property int fontSize: 11
    readonly property int fontSizeLarge: 13

    readonly property int spacingSmall: 4
    readonly property int spacing: 8
    readonly property int spacingLarge: 12
    readonly property int radiusSmall: 4
    readonly property int radius: 8
    readonly property int radiusLarge: 12
    readonly property int calendarWidth: 280
    readonly property int calendarHeight: 300
    readonly property real barOpacity: 0.94
    property real animationScale: 1.0
    readonly property int animationFast: Math.round(140 * animationScale)
    readonly property int animation: Math.round(200 * animationScale)
}
