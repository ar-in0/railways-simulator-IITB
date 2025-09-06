// Copyright (C) 2021 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR BSD-3-Clause


import QtQuick 2.0
import QtQuick.Layouts 1.11
import QtQuick.Controls 2.1
import QtQuick.Window 2.1
import QtQuick.Controls.Material 2.1

import io.qt.textproperties 1.0

ApplicationWindow {
    id: page
    width: 800
    height: 400
    visible: true
    Material.theme: Material.Dark
    Material.accent: Material.Red

    Bridge {
        id: bridge
    }

    GridLayout {
        id: grid
        columns: 2
        rows: 3

        ColumnLayout {
            spacing: 2
            Layout.columnSpan: 1
            Layout.preferredWidth: 400

            Text {
                id: leftlabel
                Layout.alignment: Qt.AlignHCenter
                color: "white"
                font.pointSize: 16
                text: "Qt for Python"
                Layout.preferredHeight: 100
                Material.accent: Material.Green
            }

            RadioButton {
                id: italic
                Layout.alignment: Qt.AlignLeft
                text: "Italic"
                onToggled: {
                    leftlabel.font.italic = bridge.getItalic(italic.text)
                    leftlabel.font.bold = bridge.getBold(italic.text)
                    leftlabel.font.underline = bridge.getUnderline(italic.text)

                }
            }
            RadioButton {
                id: bold
                Layout.alignment: Qt.AlignLeft
                text: "Bold"
                onToggled: {
                    leftlabel.font.italic = bridge.getItalic(bold.text)
                    leftlabel.font.bold = bridge.getBold(bold.text)
                    leftlabel.font.underline = bridge.getUnderline(bold.text)
                }
            }
            RadioButton {
                id: underline
                Layout.alignment: Qt.AlignLeft
                text: "Underline"
                onToggled: {
                    leftlabel.font.italic = bridge.getItalic(underline.text)
                    leftlabel.font.bold = bridge.getBold(underline.text)
                    leftlabel.font.underline = bridge.getUnderline(underline.text)
                }
            }
            RadioButton {
                id: noneradio
                Layout.alignment: Qt.AlignLeft
                text: "None"
                checked: true
                onToggled: {
                    leftlabel.font.italic = bridge.getItalic(noneradio.text)
                    leftlabel.font.bold = bridge.getBold(noneradio.text)
                    leftlabel.font.underline = bridge.getUnderline(noneradio.text)
                }
            }
        }

    }
}