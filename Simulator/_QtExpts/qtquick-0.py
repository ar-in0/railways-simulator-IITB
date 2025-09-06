import sys
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickView
from PySide6.QtQuickControls2 import QQuickStyle

# basic hello world button
if __name__ == "__main__":
    app = QGuiApplication(sys.argv)
    QQuickStyle.setStyle("Material")
    
    # https://doc.qt.io/qtforpython-6/tutorials/basictutorial/qml.html#tutorial-qml
    # QQuickView does not support using a window as a root item
    # Use the engine instead.
    # view = QQuickView()
    # view.engine().addImportPath(sys.path[0])
    # view.loadFromModule("HelloQt", "Main")

    # https://doc.qt.io/qt-6/qtqml-modules-qmldir.html
    # Exactly one module identifier directive may exist in the qmldir file.
    # Zero or more object type declarations may exist in the qmldir file. 
    # Each must have a unique name, given a version
    # Main is a type
    engine = QQmlApplicationEngine()

    # Add the current directory to the import paths
    engine.addImportPath(sys.path[0])
    engine.loadFromModule("HelloQt", "Main") # 2nd attribute needs to be defined in qmldir

    exitCode = app.exec()
    del engine
    sys.exit(exitCode)
