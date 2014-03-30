# -*- coding: utf-8 -*-
"""
This module contains the right margin mode.
"""
from pyqode.core.editor import Mode
from PyQt4 import QtGui
from pyqode.core.api import constants


class RightMarginMode(Mode):
    """
    Display a right margin at column 80 by default.

    """
    @property
    def color(self):
        return self.editor.style.value("margin")

    @color.setter
    def color(self, value):
        return self.editor.style.set_value("margin", value)

    @property
    def position(self):
        return self.editor.style.value("rightMarginPos")

    @position.setter
    def position(self, value):
        return self.editor.style.set_value("rightMarginPos", value)

    def __init__(self):
        Mode.__init__(self)
        self._margin_pos = constants.MARGIN_POS
        self._pen = QtGui.QPen()

    def _on_install(self, editor):
        """
        Installs the mode on the editor and setup drawing tools

        :param editor: The editor instance
        """
        Mode._on_install(self, editor)
        color = self.editor.style.add_property("margin", "#FF0000")
        self._pen = QtGui.QPen(QtGui.QColor(color))
        self._margin_pos = self.editor.settings.add_property(
            "rightMarginPos", "80")

    def _on_settings_changed(self, section, key):
        if key == "rightMarginPos" or not key:
            self._margin_pos = self.editor.settings.value("rightMarginPos")

    def _on_style_changed(self, section, key):
        """
        Changes the margin color

        :param section:
        :param key:
        :param value:
        """
        if key == "margin" or not key:
            self._pen = self.editor.style.value("margin")
            self.editor.mark_whole_doc_dirty()
            self.editor.repaint()

    def _on_state_changed(self, state):
        """
        Connects/Disconnects to the painted event of the editor

        :param state: Enable state
        """
        if state:
            self.editor.painted.connect(self._paint_margin)
            self.editor.repaint()
        else:
            self.editor.painted.disconnect(self._paint_margin)
            self.editor.repaint()

    def _paint_margin(self, event):
        """ Paints the right margin after editor paint event. """
        font = self.editor.currentCharFormat().font()
        fm = QtGui.QFontMetricsF(font)
        pos = self._margin_pos
        offset = self.editor.contentOffset().x() + \
            self.editor.document().documentMargin()
        x80 = round(fm.width(' ') * pos) + offset
        p = QtGui.QPainter(self.editor.viewport())
        p.setPen(self._pen)
        p.drawLine(x80, 0, x80, 2 ** 16)
