"""
This module contains the base code editor widget.
"""
from __future__ import print_function
import sys

try:
    from future.builtins import str, super
except:
    pass
import logging
import platform
from pyqode.core.cache import Cache
from pyqode.core.api.utils import DelayJobRunner, TextHelper
from pyqode.core.dialogs.goto import DlgGotoLine
from pyqode.core.managers import BackendManager
from pyqode.core.managers import FileManager
from pyqode.core.managers import ModesManager
from pyqode.core.managers import TextDecorationsManager
from pyqode.core.managers import PanelsManager
# ensure pyqode resource have been imported and are ready to be used.
from pyqode.core._forms import pyqode_core_rc
from pyqode.qt import QtWidgets, QtCore, QtGui


def _logger():
    """ Returns module's logger """
    return logging.getLogger(__name__)


class CodeEdit(QtWidgets.QPlainTextEdit):
    """
    The editor widget is a simple extension to QPlainTextEdit.

    It adds a few utility signals/methods and introduces the concepts of
    **Managers, Modes and Panels**.

    A **mode/panel** is an editor extension that, once added to a CodeEdit
    instance, may modify its behaviour and appearance:

      * **Modes** are simple objects which connect to the editor signals to
        append new behaviours (such as automatic indentation, code completion,
        syntax checking,...)

      * **Panels** are the combination of a **Mode** and a **QWidget**.
        They are displayed in the CodeEdit's content margins.

        When you install a Panel on a CodeEdit, you can choose to install it in
        one of the four following zones:

            .. image:: _static/editor_widget.png
                :align: center
                :width: 600
                :height: 450

    A **manager** is an object that literally manage a specific aspect of
    :class:`pyqode.core.api.CodeEdit`. There are managers to manage the list of
    modes/panels, to open/save file and to control the backend:

        - :attr:`pyqode.core.api.CodeEdit.file`:
            File manager. Use it to open/save files or access the opened file
            attribute.
        - :attr:`pyqode.core.api.CodeEdit.backend`:
            Backend manager. Use it to start/stop the backend or send a work
            request.
        - :attr:`pyqode.core.api.CodeEdit.modes`:
            Modes manager. Use it to append/remove modes on the editor.
        - :attr:`pyqode.core.api.CodeEdit.panels`:
            Modes manager. Use it to append/remove panels on the editor.

    Starting from version 2.1, CodeEdit defines the
    :attr:`pyqode.core.api.CodeEdit.mimetypes` class attribute that can be used
    by IDE to determine which editor to use for a given mime type. This
    property is a list of supported mimetypes. An empty list means the
    CodeEdit is generic. **Code editors specialised for a specific language
    should define the mime types they support!**
    """
    #: Paint hook
    painted = QtCore.Signal(QtGui.QPaintEvent)
    #: Signal emitted when a new text is set on the widget
    new_text_set = QtCore.Signal()
    #: Signal emitted when the text is saved to file
    text_saved = QtCore.Signal(str)
    #: Signal emitted before the text is saved to file
    text_saving = QtCore.Signal(str)
    #: Signal emitted when the dirty state changed
    dirty_changed = QtCore.Signal(bool)
    #: Signal emitted when a key is pressed
    key_pressed = QtCore.Signal(QtGui.QKeyEvent)
    #: Signal emitted when a key is released
    key_released = QtCore.Signal(QtGui.QKeyEvent)
    #: Signal emitted when a mouse button is pressed
    mouse_pressed = QtCore.Signal(QtGui.QMouseEvent)
    #: Signal emitted when a mouse button is released
    mouse_released = QtCore.Signal(QtGui.QMouseEvent)
    #: Signal emitted when a mouse double click event occured
    mouse_double_clicked = QtCore.Signal(QtGui.QMouseEvent)
    #: Signal emitted on a wheel event
    mouse_wheel_activated = QtCore.Signal(QtGui.QWheelEvent)
    #: Signal emitted at the end of the key_pressed event
    post_key_pressed = QtCore.Signal(QtGui.QKeyEvent)
    #: Signal emitted when focusInEvent is is called
    focused_in = QtCore.Signal(QtGui.QFocusEvent)
    #: Signal emitted when the mouse_moved
    mouse_moved = QtCore.Signal(QtGui.QMouseEvent)
    #: Signal emitted when the user press the TAB key
    indent_requested = QtCore.Signal()
    #: Signal emitted when the user press the BACK-TAB (Shift+TAB) key
    unindent_requested = QtCore.Signal()

    #: Store the list of mimetypes associated with the editor, for
    #: specialised editors.
    mimetypes = []

    _DEFAULT_FONT = 'Source Code Pro' if sys.platform != 'darwin' else 'Monaco'

    @property
    def use_spaces_instead_of_tabs(self):
        """ Use spaces instead of tabulations. Default is True. """
        return self._use_spaces_instead_of_tabs

    @use_spaces_instead_of_tabs.setter
    def use_spaces_instead_of_tabs(self, value):
        self._use_spaces_instead_of_tabs = value
        for c in self.clones:
            c.use_spaces_instead_of_tabs = value

    @property
    def tab_length(self):
        """ Tab length, number of spaces. """
        return self._tab_length

    @tab_length.setter
    def tab_length(self, value):
        self._tab_length = value
        for c in self.clones:
            c.tab_length = value

    @property
    def min_indent_column(self):
        """
        Minimum indent column.

        Some languages such as cobol starts coding at column 7.
        """
        return self._min_indent_column

    @min_indent_column.setter
    def min_indent_column(self, value):
        self._min_indent_column = value
        for c in self.clones:
            c.min_indent_column = value

    @property
    def save_on_focus_out(self):
        """
        Automatically saves editor content on focus out.

        Default is False.
        """
        return self._save_on_focus_out

    @save_on_focus_out.setter
    def save_on_focus_out(self, value):
        self._save_on_focus_out = value
        for c in self.clones:
            c.save_on_focus_out = value

    @property
    def show_whitespaces(self):
        """
        Shows/Hides virtual white spaces.
        """
        return self._show_whitespaces

    @show_whitespaces.setter
    def show_whitespaces(self, value):
        self._show_whitespaces = value
        self._set_whitespaces_flags(value)
        for c in self.clones:
            c.show_whitespaces = value

    @property
    def font_name(self):
        """
        The editor font family name.
        """
        return self._font_family

    @font_name.setter
    def font_name(self, value):
        if value == "":
            value = self._DEFAULT_FONT
        self._font_family = value
        self._reset_stylesheet()
        for c in self.clones:
            c.font_name = value

    @property
    def zoom_level(self):
        """
        Gets/Sets the editor zoom level.

        The zoom level is a value that is added to the current editor font
        size. Negative values are used to zoom out the editor, positive values
        are used to zoom in the editor.
        """
        return self._zoom_level

    @zoom_level.setter
    def zoom_level(self, value):
        self._zoom_level = value

    @property
    def font_size(self):
        """
        The font point size.

        .. note:: Please, **never use setFontPointSize/setFontFamily functions
            directly** as the values you define there will be overwritten as
            soon as the user zoom the editor or as soon as a stylesheet
            property has changed.
        """
        return self._font_size

    @font_size.setter
    def font_size(self, value):
        self._font_size = value
        self._reset_stylesheet()
        for c in self.clones:
            c.font_size = value

    @property
    def background(self):
        """
        The editor background color (QColor)
        """
        return self._background

    @background.setter
    def background(self, value):
        self._background = value
        self._reset_stylesheet()
        for c in self.clones:
            c.background = value

    @property
    def foreground(self):
        """
        The editor foreground color (QColor)
        """
        return self._foreground

    @foreground.setter
    def foreground(self, value):
        self._foreground = value
        self._reset_stylesheet()
        for c in self.clones:
            c.foreground = value

    @property
    def whitespaces_foreground(self):
        """
        The editor white spaces' foreground color. White spaces are highlighted
        by the syntax highlighter. You should call rehighlight to update their
        color. This is not done automatically to prevent multiple, useless
        call to ``rehighlight`` which can take some time on big files.
        """
        return self._whitespaces_foreground

    @whitespaces_foreground.setter
    def whitespaces_foreground(self, value):
        self._whitespaces_foreground = value
        for c in self.clones:
            c.whitespaces_foreground = value

    @property
    def selection_background(self):
        """
        The editor selection's background color.
        """
        return self._sel_background

    @selection_background.setter
    def selection_background(self, value):
        self._sel_background = value
        self._reset_stylesheet()
        for c in self.clones:
            c.selection_background = value

    @property
    def selection_foreground(self):
        """
        The editor selection's foreground color.
        """
        return self._sel_foreground

    @selection_foreground.setter
    def selection_foreground(self, value):
        self._sel_foreground = value
        for c in self.clones:
            c.selection_foreground = value

    @property
    def word_separators(self):
        """
        The list of word separators used by the code completion mode
        and the word clicked mode.
        """
        return self._word_separators

    @word_separators.setter
    def word_separators(self, value):
        self._word_separators = value
        for c in self.clones:
            c._word_separators = value

    @property
    def dirty(self):
        """
        Tells whethere the content of editor has been modified.

        (this is just a shortcut to QTextDocument.isModified

        :type: bool
        """
        return self.document().isModified()

    @property
    def visible_blocks(self):
        """
        Returns the list of visible blocks.

        Each element in the list is a tuple made up of the line top position,
        the line number and the QTextBlock itself.

        :return: A list of tuple(top_position, line_number, block)
        :rtype: List of tuple(int, int, QtWidgets.QTextBlock)
        """
        return self._visible_blocks

    @property
    def file(self):
        """
        Returns a reference to the :class:`pyqode.core.managers.FileManager`
        used to open/save file on the editor
        """
        return self._file

    @file.setter
    def file(self, file_manager):
        """
        Sets a custom file manager.

        :param file_manager: custom file manager instance.
        """
        self._file = file_manager

    @property
    def backend(self):
        """
        Returns a reference to the :class:`pyqode.core.managers.BackendManager`
        used to control the backend process.
        """
        return self._backend

    @property
    def modes(self):
        """
        Returns a reference to the :class:`pyqode.core.managers.ModesManager`
        used to manage the collection of installed modes.
        """
        return self._modes

    @property
    def panels(self):
        """
        Returns a reference to the :class:`pyqode.core.managers.PanelsManager`
        used to manage the collection of installed panels
        """
        return self._panels

    @property
    def decorations(self):
        """
        Returns a reference to the
        :class:`pyqode.core.managers.TextDecorationManager` used to manage the
        list of :class:`pyqode.core.api.TextDecoration`
        """
        return self._decorations

    @property
    def syntax_highlighter(self):
        """
        Returns a reference to the syntax highlighter mode currently used to
        highlight the editor content.

        :return: :class:`pyqode.core.api.SyntaxHighlighter`
        """
        for mode in self.modes:
            if hasattr(mode, 'highlightBlock'):
                return mode
        return None

    def __init__(self, parent=None, create_default_actions=True):
        """
        :param parent: Parent widget

        :param create_default_actions: True to create the default context
            menu actions (copy, paste, edit)
        """
        super(CodeEdit, self).__init__(parent)
        self.clones = []
        self._default_font_size = 10
        self._backend = BackendManager(self)
        self._file = FileManager(self)
        self._modes = ModesManager(self)
        self._panels = PanelsManager(self)
        self._decorations = TextDecorationsManager(self)
        self.document().modificationChanged.connect(self._emit_dirty_changed)

        self._word_separators = [
            '~', '!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '+', '{',
            '}', '|', ':', '"', "'", "<", ">", "?", ",", ".", "/", ";", '[',
            ']', '\\', '\n', '\t', '=', '-', ' '
        ]
        self._min_indent_column = 0
        self._save_on_focus_out = False
        self._use_spaces_instead_of_tabs = True
        self._whitespaces_foreground = None
        self._sel_background = None
        self._show_whitespaces = False
        self._foreground = None
        self._sel_foreground = None
        self._tab_length = 4
        self._zoom_level = 0
        self._font_size = 10
        self._background = None
        QtGui.QFontDatabase.addApplicationFont(
            ':/fonts/rc/SourceCodePro-Regular.ttf')
        QtGui.QFontDatabase.addApplicationFont(
            ':/fonts/rc/SourceCodePro-Bold.ttf')
        self._font_family = self._DEFAULT_FONT
        self._mimetypes = []

        # Flags/Working variables
        self._last_mouse_pos = QtCore.QPoint(0, 0)
        self._modified_lines = set()
        self._cleaning = False
        self._visible_blocks = []
        self._tooltips_runner = DelayJobRunner(delay=700)
        self._prev_tooltip_block_nbr = -1
        self._original_text = ""

        self._dirty = False

        # setup context menu
        self._actions = []
        self._menus = []
        if create_default_actions:
            self._init_actions()
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self._mnu = None  # bug with PySide (github #63)

        # init settings and styles from global settings/style modules
        self._init_settings()
        self._init_style()

        # connect slots
        self.textChanged.connect(self._on_text_changed)
        self.blockCountChanged.connect(self.update)
        self.cursorPositionChanged.connect(self.update)
        self.selectionChanged.connect(self.update)

        self.setMouseTracking(True)
        self.setCenterOnScroll(True)
        self.setLineWrapMode(self.NoWrap)

    def split(self):
        """
        Split the code editor widget, return a clone of the widget ready to
        be used (and synchronised with its original).

        Splitting the widget is done in 2 steps:
            - first we clone the widget, you can override ``clone`` if your
              widget needs additional arguments.

            - then we link the two text document and disable some modes on the
                cloned instance (such as the watcher mode).
        """
        # cache cursor position so that the clone open at the current cursor
        # pos
        l, c = TextHelper(self).cursor_position()
        clone = self.clone()
        self.link(clone)
        TextHelper(clone).goto_line(l, c)
        self.clones.append(clone)
        return clone

    def clone(self):
        """
        Clone ourselves, return an instance of the same class, using the
        default QWidget constructor.
        """
        clone = self.__class__(parent=self.parent())
        return clone

    def link(self, clone):
        """
        Links the clone with its original. We copy the file manager infos
        (path, mimetype, ...) and setup the clone text document as reference
        to our text document.

        :param clone: clone to link.
        """
        clone.file._path = self.file.path
        clone.file._encoding = self.file.encoding
        clone.file._mimetype = self.file.mimetype
        clone.setDocument(self.document())
        for original_mode, mode in zip(list(self.modes), list(clone.modes)):
            mode.enabled = original_mode.enabled
            mode.clone_settings(original_mode)
        for original_panel, panel in zip(
                list(self.panels), list(clone.panels)):
            panel.enabled = original_panel.isEnabled()
            panel.clone_settings(original_panel)
        clone.use_spaces_instead_of_tabs = self.use_spaces_instead_of_tabs
        clone.tab_length = self.tab_length
        clone.min_indent_column = self.min_indent_column
        clone.save_on_focus_out = self.save_on_focus_out
        clone.show_whitespaces = self.show_whitespaces
        clone.font_name = self.font_name
        clone.font_size = self.font_size
        clone.zoom_level = self.zoom_level
        clone.background = self.background
        clone.foreground = self.foreground
        clone.whitespaces_foreground = self.whitespaces_foreground
        clone.selection_background = self.selection_background
        clone.selection_foreground = self.selection_foreground
        clone.word_separators = self.word_separators
        clone.file.clone_settings(self.file)

    def close(self, clear=True):
        """
        Closes the editor, stops the backend and removes any installed
        mode/panel.

        This is also where we cache the cursor position.

        :param clear: True to clear the editor content before closing.
        """
        self.decorations.clear()
        self.modes.clear()
        self.panels.clear()
        self.backend.stop()
        Cache().set_cursor_position(
            self.file.path, TextHelper(self).cursor_position())
        super(CodeEdit, self).close()
        _logger().info('closed')

    def set_mouse_cursor(self, cursor):
        """
        Changes the viewport's cursor

        :param cursor: the mouse cursor to set.
        :type cursor: QtWidgets.QCursor
        """
        self.viewport().setCursor(cursor)

    def show_tooltip(self, pos, tooltip, _sender_deco=None):
        """
        Show a tool tip at the specified position

        :param pos: Tooltip position
        :param tooltip: Tooltip text

        :param _sender_deco: TextDecoration which is the sender of the show
            tooltip request. (for internal use only).
        """
        if _sender_deco is not None and _sender_deco not in self.decorations:
            return
        QtWidgets.QToolTip.showText(pos, tooltip[0: 1024], self)

    def setPlainText(self, txt, mime_type, encoding):
        """
        Extends setPlainText to force the user to setup an encoding and a
        mime type.

        Emits the new_text_set signal.

        :param txt: The new text to set.
        :param mime_type: Associated mimetype. Setting the mime will update the
                          pygments lexer.
        :param encoding: text encoding
        """
        self.file.mimetype = mime_type
        self.file._encoding = encoding
        self._original_text = txt
        self._modified_lines.clear()
        import time
        t = time.time()
        super(CodeEdit, self).setPlainText(txt)
        _logger().info('setPlainText duration: %fs' % (time.time() - t))
        self.new_text_set.emit()
        self.redoAvailable.emit(False)
        self.undoAvailable.emit(False)

    def add_action(self, action):
        """
        Adds an action to the editor's context menu.

        :param action: QtWidgets.QAction
        """
        self._actions.append(action)
        action.setShortcutContext(QtCore.Qt.WidgetShortcut)
        super(CodeEdit, self).addAction(action)

    def insert_action(self, action, prev_action):
        """
        Inserts an action to the editor's context menu

        :param action: action to insert
        :param prev_action: the action after which the new action must be
            inserted
        """
        index = self._actions.index(prev_action)
        action.setShortcutContext(QtCore.Qt.WidgetShortcut)
        self._actions.insert(index, action)

    def actions(self):
        """
        Returns the list of actions/sepqrators of the context menu.

        """
        return self._actions

    def add_separator(self):
        """
        Adds a sepqrator to the editor's context menu.

        :return: The sepator that has been added.
        :rtype: QtWidgets.QAction
        """
        action = QtWidgets.QAction(self)
        action.setSeparator(True)
        self._actions.append(action)
        self.addAction(action)
        return action

    def remove_action(self, action):
        """
        Removes an action/separator from the editor's context menu.

        :param action: Action/seprator to remove.
        """
        self._actions.remove(action)
        self.removeAction(action)

    def add_menu(self, menu):
        """
        Adds a sub-menu to the editor context menu.

        Menu are put at the bottom of the context menu.

        .. note:: to add a menu in the middle of the context menu, you can
            always add its menuAction().

        :param menu: menu to add
        """
        self._menus.append(menu)
        for action in menu.actions():
            action.setShortcutContext(QtCore.Qt.WidgetShortcut)
        self.addActions(menu.actions())

    def remove_menu(self, menu):
        """
        Removes a sub-menu from the context menu.
        :param menu: Sub-menu to remove.
        """
        self._menus.remove(menu)
        for action in menu.actions():
            self.removeAction(action)

    @QtCore.Slot()
    def delete(self):
        """ Deletes the selected text """
        self.textCursor().removeSelectedText()

    @QtCore.Slot()
    def goto_line(self):
        """
        Shows the *go to line dialog* and go to the selected line.
        """
        helper = TextHelper(self)
        line, result = DlgGotoLine.get_line(
            self, helper.current_line_nbr(), helper.line_count())
        if not result:
            return
        return helper.goto_line(line, move=True)

    @QtCore.Slot()
    def rehighlight(self):
        """
        Calls ``rehighlight`` on the installed syntax highlighter mode.
        """
        if self.syntax_highlighter:
            self.syntax_highlighter.rehighlight()

    @QtCore.Slot()
    def reset_zoom(self):
        """
        Resets the zoom level.
        """
        self._zoom_level = 0
        self._reset_stylesheet()

    @QtCore.Slot()
    def zoom_in(self, increment=1):
        """
        Zooms in the editor (makes the font bigger).

        :param increment: zoom level increment. Default is 1.
        """
        self.zoom_level += increment
        TextHelper(self).mark_whole_doc_dirty()
        self._reset_stylesheet()

    @QtCore.Slot()
    def zoom_out(self, decrement=1):
        """
        Zooms out the editor (makes the font smaller).

        :param decrement: zoom level decrement. Default is 1. The value is
            given as an absolute value.
        """
        self.zoom_level -= decrement
        # make sure font size remains > 0
        if self.font_size + self.zoom_level <= 0:
            self.zoom_level = -self._font_size + 1
        TextHelper(self).mark_whole_doc_dirty()
        self._reset_stylesheet()

    @QtCore.Slot()
    def duplicate_line(self):
        """
        Duplicates the line under the cursor. If multiple lines are selected,
        only the last one is duplicated.
        """
        cursor = self.textCursor()
        assert isinstance(cursor, QtGui.QTextCursor)
        cursor.beginEditBlock()
        col = cursor.positionInBlock()
        cursor.select(cursor.LineUnderCursor)
        line = cursor.selectedText()
        cursor.movePosition(cursor.EndOfBlock)
        cursor.insertText('\n' + line)
        cursor.movePosition(cursor.StartOfBlock)
        cursor.movePosition(cursor.Right, cursor.MoveAnchor, col)
        self.setTextCursor(cursor)
        cursor.endEditBlock()

    @QtCore.Slot()
    def indent(self):
        """
        Indents the text cursor or the selection.

        Emits the :attr:`pyqode.core.api.CodeEdit.indent_requested`
        signal, the :class:`pyqode.core.modes.IndenterMode` will
        perform the actual indentation.
        """
        self.indent_requested.emit()

    @QtCore.Slot()
    def un_indent(self):
        """
        Un-indents the text cursor or the selection.

        Emits the :attr:`pyqode.core.api.CodeEdit.unindent_requested`
        signal, the :class:`pyqode.core.modes.IndenterMode` will
        perform the actual un-indentation.
        """
        self.unindent_requested.emit()

    def resizeEvent(self, e):
        """
        Overrides resize event to resize the editor's panels.

        :param e: resize event
        """
        super(CodeEdit, self).resizeEvent(e)
        self.panels.resize()

    def paintEvent(self, e):
        """
        Overrides paint event to update the list of visible blocks and emit
        the painted event.

        :param e: paint event
        """
        self._update_visible_blocks(e)
        super(CodeEdit, self).paintEvent(e)
        self.painted.emit(e)

    def keyPressEvent(self, event):
        """
        Overrides the keyPressEvent to emit the key_pressed signal.

        Also takes care of indenting and handling smarter home key.

        :param event: QKeyEvent
        """
        initial_state = event.isAccepted()
        event.ignore()
        self.key_pressed.emit(event)
        state = event.isAccepted()
        if not event.isAccepted():
            if event.key() == QtCore.Qt.Key_Tab:
                self.indent()
                event.accept()
            elif event.key() == QtCore.Qt.Key_Backtab:
                self.un_indent()
                event.accept()
            elif event.key() == QtCore.Qt.Key_Home:
                self._do_home_key(
                    event, int(event.modifiers()) & QtCore.Qt.ShiftModifier)
            if not event.isAccepted():
                event.setAccepted(initial_state)
                super(CodeEdit, self).keyPressEvent(event)
        new_state = event.isAccepted()
        event.setAccepted(state)
        self.post_key_pressed.emit(event)
        event.setAccepted(new_state)

    def keyReleaseEvent(self, event):
        """
        Overrides keyReleaseEvent to emit the key_released signal.

        :param event: QKeyEvent
        """
        initial_state = event.isAccepted()
        event.ignore()
        self.key_released.emit(event)
        if not event.isAccepted():
            event.setAccepted(initial_state)
            super(CodeEdit, self).keyReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        initial_state = event.isAccepted()
        event.ignore()
        self.mouse_double_clicked.emit(event)
        if not event.isAccepted():
            event.setAccepted(initial_state)
            super(CodeEdit, self).mouseDoubleClickEvent(event)

    def focusInEvent(self, event):
        """
        Overrides focusInEvent to emits the focused_in signal

        :param event: QFocusEvent
        """
        # fix a visual bug if the editor was resized while being hidden (
        # e.g. a dock # widget has been resized and some editors were in a
        # tab widget. Non visible editor have a visual bug where horizontal
        # scroll bar range
        #
        TextHelper(self).mark_whole_doc_dirty()
        s = self.size()
        s.setWidth(s.width() + 1)
        self.resizeEvent(QtGui.QResizeEvent(self.size(), s))

        self.focused_in.emit(event)
        super(CodeEdit, self).focusInEvent(event)
        self.repaint()

    def focusOutEvent(self, event):
        # Saves content if save_on_focus_out is True.
        if self.save_on_focus_out and self.dirty and self.file.path:
            self.file.save()
        super(CodeEdit, self).focusOutEvent(event)

    def mousePressEvent(self, event):
        """
        Overrides mousePressEvent to emits mouse_pressed signal

        :param event: QMouseEvent
        """
        initial_state = event.isAccepted()
        event.ignore()
        self.mouse_pressed.emit(event)
        if event.button() == QtCore.Qt.LeftButton:
            cursor = self.cursorForPosition(event.pos())
            for sel in self.decorations:
                if sel.cursor.blockNumber() == cursor.blockNumber():
                    if sel.contains_cursor(cursor):
                        sel.signals.clicked.emit(sel)
        if not event.isAccepted():
            event.setAccepted(initial_state)
            super(CodeEdit, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """
        Emits mouse_released signal.

        :param event: QMouseEvent
        """
        initial_state = event.isAccepted()
        event.ignore()
        self.mouse_released.emit(event)
        if not event.isAccepted():
            event.setAccepted(initial_state)
            super(CodeEdit, self).mouseReleaseEvent(event)

    def wheelEvent(self, event):
        """
        Emits the mouse_wheel_activated signal.

        :param event: QMouseEvent
        """
        initial_state = event.isAccepted()
        event.ignore()
        self.mouse_wheel_activated.emit(event)
        if not event.isAccepted():
            event.setAccepted(initial_state)
            super(CodeEdit, self).wheelEvent(event)

    def mouseMoveEvent(self, event):
        """
        Overrides mouseMovedEvent to display any decoration tooltip and emits
        the mouse_moved event.

        :param event: QMouseEvent
        """
        cursor = self.cursorForPosition(event.pos())
        self._last_mouse_pos = event.pos()
        block_found = False
        for sel in self.decorations:
            if sel.contains_cursor(cursor) and sel.tooltip:
                if (self._prev_tooltip_block_nbr != cursor.blockNumber() or
                        not QtWidgets.QToolTip.isVisible()):
                    pos = event.pos()
                    # add left margin
                    pos.setX(pos.x() + self.panels.margin_size())
                    # add top margin
                    pos.setY(pos.y() + self.panels.margin_size(0))
                    self._tooltips_runner.request_job(
                        self.show_tooltip,
                        self.mapToGlobal(pos), sel.tooltip[0: 1024], sel)
                    self._prev_tooltip_block_nbr = cursor.blockNumber()
                block_found = True
                break
        if not block_found and self._prev_tooltip_block_nbr != -1:
            QtWidgets.QToolTip.hideText()
            self._prev_tooltip_block_nbr = -1
            self._tooltips_runner.cancel_requests()
        self.mouse_moved.emit(event)
        super(CodeEdit, self).mouseMoveEvent(event)

    def showEvent(self, event):
        """ Overrides showEvent to update the viewport margins """
        super(CodeEdit, self).showEvent(event)
        _logger().debug('show event')

    def get_context_menu(self):
        """
        Gets the editor context menu.

        :return: QMenu
        """
        mnu = QtWidgets.QMenu()
        mnu.addActions(self._actions)
        mnu.addSeparator()
        for menu in self._menus:
            mnu.addMenu(menu)
        return mnu

    def _show_context_menu(self, point):
        """ Shows the context menu """
        self._mnu = self.get_context_menu()
        self._mnu.popup(self.mapToGlobal(point))

    def _set_whitespaces_flags(self, show):
        """ Sets show white spaces flag """
        doc = self.document()
        options = doc.defaultTextOption()
        if show:
            options.setFlags(options.flags() |
                             QtGui.QTextOption.ShowTabsAndSpaces)
        else:
            options.setFlags(options.flags() &
                             ~QtGui.QTextOption.ShowTabsAndSpaces)
        doc.setDefaultTextOption(options)

    def _init_actions(self):
        """ Init default QAction """
        def _icon(val):
            if isinstance(val, tuple):
                theme, icon = val
                return QtGui.QIcon.fromTheme(theme, QtGui.QIcon(icon))
            else:
                QtGui.QIcon(val)
        # Undo
        action = QtWidgets.QAction('Undo', self)
        action.setShortcut(QtGui.QKeySequence.Undo)
        action.setIcon(_icon(('edit-undo', ':/pyqode-icons/rc/edit-undo.png')))
        action.triggered.connect(self.undo)
        self.undoAvailable.connect(action.setEnabled)
        self.add_action(action)
        self.action_undo = action
        # Redo
        action = QtWidgets.QAction('Redo', self)
        action.setShortcut(QtGui.QKeySequence.Redo)
        action.setIcon(_icon(('edit-redo', ':/pyqode-icons/rc/edit-redo.png')))
        action.triggered.connect(self.redo)
        self.redoAvailable.connect(action.setEnabled)
        self.add_action(action)
        self.action_redo = action
        # separator
        self.add_separator()
        # Copy
        action = QtWidgets.QAction('Copy', self)
        action.setShortcut(QtGui.QKeySequence.Copy)
        action.setIcon(_icon(('edit-copy', ':/pyqode-icons/rc/edit-copy.png')))
        action.triggered.connect(self.copy)
        self.copyAvailable.connect(action.setEnabled)
        self.add_action(action)
        self.action_copy = action
        # cut
        action = QtWidgets.QAction('Cut', self)
        action.setShortcut(QtGui.QKeySequence.Cut)
        action.setIcon(_icon(('edit-cut', ':/pyqode-icons/rc/edit-cut.png')))
        action.triggered.connect(self.cut)
        self.copyAvailable.connect(action.setEnabled)
        self.add_action(action)
        self.action_cut = action
        # paste
        action = QtWidgets.QAction('Paste', self)
        action.setShortcut(QtGui.QKeySequence.Paste)
        action.setIcon(_icon(('edit-paste',
                              ':/pyqode-icons/rc/edit-paste.png')))
        action.triggered.connect(self.paste)
        self.add_action(action)
        self.action_paste = action
        # delete
        action = QtWidgets.QAction('Delete', self)
        action.setShortcut(QtGui.QKeySequence.Delete)
        action.setIcon(_icon(('edit-delete',
                              ':/pyqode-icons/rc/edit-delete.png')))
        action.triggered.connect(self.delete)
        self.add_action(action)
        self.action_delete = action
        # duplicate line
        action = QtWidgets.QAction('Duplicate line', self)
        action.setShortcut('Ctrl+D')
        action.triggered.connect(self.duplicate_line)
        self.add_action(action)
        self.action_duplicate_line = action
        # select all
        action = QtWidgets.QAction('Select all', self)
        action.setShortcut(QtGui.QKeySequence.SelectAll)
        action.setIcon(_icon(('edit-select-all',
                              ':/pyqode-icons/rc/edit-select-all.png')))
        action.triggered.connect(self.selectAll)
        self.add_action(action)
        self.action_select_all = action
        # separator
        self.add_separator()
        # indent
        action = QtWidgets.QAction('Indent', self)
        action.setShortcut('Tab')
        action.setIcon(_icon(('format-indent-more',
                              ':/pyqode-icons/rc/format-indent-more.png')))
        action.triggered.connect(self.indent)
        self.add_action(action)
        self.action_indent = action
        # unindent
        action = QtWidgets.QAction('Un-indent', self)
        action.setShortcut('Shift+Tab')
        action.setIcon(_icon(('format-indent-less',
                              ':/pyqode-icons/rc/format-indent-less.png')))
        action.triggered.connect(self.un_indent)
        self.add_action(action)
        self.action_un_indent = action
        # separator
        self.add_separator()
        # goto
        action = QtWidgets.QAction('Go to line', self)
        action.setShortcut('Ctrl+G')
        action.setIcon(_icon(('go-jump',
                              ':/pyqode-icons/rc/goto-line.png')))
        action.triggered.connect(self.goto_line)
        self.add_action(action)
        self.action_goto_line = action
        self.add_separator()

    def _init_settings(self):
        """ Init setting """
        self._show_whitespaces = False
        self._tab_length = 4
        self._use_spaces_instead_of_tabs = True
        self.setTabStopWidth(self._tab_length *
                             self.fontMetrics().width(" "))
        self._set_whitespaces_flags(self._show_whitespaces)

    def _init_style(self):
        """ Inits style options """
        self._background = QtGui.QColor('white')
        self._foreground = QtGui.QColor('black')
        self._whitespaces_foreground = QtGui.QColor('light gray')
        app = QtWidgets.QApplication.instance()
        self._sel_background = app.palette().highlight().color()
        self._sel_foreground = app.palette().highlightedText().color()
        self._font_size = 10
        self.font_name = ""

    def _update_visible_blocks(self, *args):
        """ Updates the list of visible blocks """
        self._visible_blocks[:] = []
        block = self.firstVisibleBlock()
        block_nbr = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(
            self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())
        ebottom_top = 0
        ebottom_bottom = self.height()
        while block.isValid():
            visible = (top >= ebottom_top and bottom <= ebottom_bottom)
            if not visible:
                break
            if block.isVisible():
                self._visible_blocks.append((top, block_nbr, block))
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_nbr = block.blockNumber()

    def _on_text_changed(self):
        """ Adjust dirty flag depending on editor's content """
        if not self._cleaning:
            ln = TextHelper(self).cursor_position()[0]
            self._modified_lines.add(ln)

    def _reset_stylesheet(self):
        """ Resets stylesheet"""
        self.setFont(QtGui.QFont(self._font_family,
                                 self._font_size + self._zoom_level))
        p = self.palette()
        p.setColor(QtGui.QPalette.Base, self.background)
        p.setColor(QtGui.QPalette.Text, self.foreground)
        p.setColor(QtGui.QPalette.Highlight, self.selection_background)
        p.setColor(QtGui.QPalette.HighlightedText, self.selection_foreground)
        if QtWidgets.QApplication.instance().styleSheet() or (
                hasattr(self, '_flg_stylesheet') and
                platform.system() == 'Windows'):
            # on windows, if the application once had a stylesheet, we must
            # keep on using a stylesheet otherwise strange colors appear
            # see https://github.com/OpenCobolIDE/OpenCobolIDE/issues/65
            self._flg_stylesheet = True
            self.setStyleSheet('''QPlainTextEdit
            {
                background-color: %s;
                color: %s;
            }
            ''' % (self.background.name(), self.foreground.name()))
        else:
            # on linux/osx we just have to set an empty stylesheet to cancel
            # any previous stylesheet and still keep a correct style for
            # scrollbars
            self.setStyleSheet('')
        self.setPalette(p)
        self.repaint()

    def _do_home_key(self, event=None, select=False):
        """ Performs home key action """
        # get nb char to first significative char
        delta = (self.textCursor().positionInBlock() -
                 TextHelper(self).line_indent())
        cursor = self.textCursor()
        move = QtGui.QTextCursor.MoveAnchor
        if select:
            move = QtGui.QTextCursor.KeepAnchor
        if delta:
            cursor.movePosition(QtGui.QTextCursor.Left, move, delta)
        else:
            cursor.movePosition(QtGui.QTextCursor.StartOfBlock, move)
        self.setTextCursor(cursor)
        if event:
            event.accept()

    def _emit_dirty_changed(self, state):
        self.dirty_changed.emit(state)
        for c in self.clones:
            c.dirty_changed.emit(state)
