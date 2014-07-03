# -*- coding: utf-8 -*-
"""
Contains a case converter mode.
"""
from pyqode.core.api import TextHelper
from pyqode.core.api.mode import Mode
from pyqode.core.qt import QtCore, QtWidgets


class CaseConverterMode(Mode):
    """
    Converts selected text to lower case or UPPER case.

    It does so by adding two new menu entries to the editor's context menu:
      - *Convert to lower case*: ctrl-u
      - *Convert to UPPER CASE*: ctrl+shift+u
    """
    def __init__(self):
        Mode.__init__(self)
        self._actions_created = False
        self.action_to_lower = None
        self.action_to_upper = None
        self.separator = None

    @QtCore.Slot()
    def to_upper(self, *args):
        """
        Converts selected text to upper
        """
        # pylint: disable=unused-argument
        TextHelper(self.editor).selected_text_to_upper()

    @QtCore.Slot()
    def to_lower(self, *args):
        """
        Converts selected text to lower
        """
        # pylint: disable=unused-argument
        TextHelper(self.editor).selected_text_to_lower()

    def _create_actions(self):
        """ Create associated actions """
        self.action_to_lower = QtWidgets.QAction(self.editor)
        self.action_to_lower.triggered.connect(self.to_lower)
        self.action_to_upper = QtWidgets.QAction(self.editor)
        self.action_to_upper.triggered.connect(self.to_upper)
        self.action_to_lower.setText('Convert to lower case')
        self.action_to_lower.setShortcut('Ctrl+U')
        self.action_to_upper.setText('Convert to UPPER CASE')
        self.action_to_upper.setShortcut('Ctrl+Shift+U')
        self._actions_created = True

    def on_state_changed(self, state):
        if state:
            if not self._actions_created:
                self._create_actions()
            self.separator = self.editor.add_separator()
            self.editor.add_action(self.action_to_lower)
            self.editor.add_action(self.action_to_upper)
        else:
            self.editor.remove_action(self.action_to_lower)
            self.editor.remove_action(self.action_to_upper)
            self.editor.remove_action(self.separator)
