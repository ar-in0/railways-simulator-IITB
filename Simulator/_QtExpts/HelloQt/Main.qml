import QtQuick // QML standard library
import QtQuick.Controls // For object ApplicationWindow

// Any new objects {} defined inside the window will all
// be rendered.
// Default positioning for any element on the canvas is top left corner.
// Elements (object) are rendered in the order they are defined in the Window{}
Window {
    id: root
    visible: true
    width: 640
    height: 480
    title: qsTr("Hello QtQuick")
    Rectangle {
        id: main
        width: 200
        height: 200
        color: "gray"

        Text {
            text: "Hello World"
            anchors.centerIn: main // positioning the text to center
        }
    }
    Button {
        id: button
        text: "Test Button"
    }

}