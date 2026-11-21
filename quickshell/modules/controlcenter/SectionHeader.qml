import QtQuick
import "../../config"

Text {
    required property Theme theme
    color: "#555560"
    font.family: theme.fontFamily
    font.pixelSize: theme.fontSizeSmall
    font.bold: true
    font.letterSpacing: 1
}
