# A more involved qml example with slots and signals
from __future__ import annotations # to use decorators
from PySide6.QtCore import QObject, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QmlElement
from PySide6.QtQuickControls2 import QQuickStyle
import sys

# To be used on the @QmlElement decorator
# (QML_IMPORT_MINOR_VERSION is optional)
# both below are necessary to enable qml to use the @QmlElement
QML_IMPORT_NAME = "io.qt.textproperties" # name by which to import the class defined in this python file into a qml file.
QML_IMPORT_MAJOR_VERSION = 1 

# new element
# Define several slots
@QmlElement
class Bridge(QObject):
    @Slot(str, result=str)
    def getColor(self, s):
        if s.lower() == "red":
            return "#ef9a9a"
        if s.lower() == "green":
            return "#a5d6a7"
        if s.lower() == "blue":
            return "#90caf9"
        return "white"

    @Slot(float, result=int)
    def getSize(self, s):
        size = int(s * 34)
        return max(1, size)

    @Slot(str, result=bool)
    def getItalic(self, s):
        return s.lower() == "italic"

    @Slot(str, result=bool)
    def getBold(self, s):
        return s.lower() == "bold"

    @Slot(str, result=bool)
    def getUnderline(self, s):
        return s.lower() == "underline"


if __name__ == '__main__':
    app = QGuiApplication(sys.argv)
    QQuickStyle.setStyle("Material")
    engine = QQmlApplicationEngine()
    # Add the current directory to the import paths and load the main module.
    engine.addImportPath(sys.path[0])
    engine.loadFromModule("QmlIntegration", "Main")

    if not engine.rootObjects():
        sys.exit(-1)

    exit_code = app.exec()
    del engine
    sys.exit(exit_code)