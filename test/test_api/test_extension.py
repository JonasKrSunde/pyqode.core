# -*- coding: utf-8 -*-
"""
This module tests the classes: Mode an Panels
"""
from pyqode.core.qt.QtTest import QTest

import pytest
from ..helpers import editor_open
from ..helpers import log_test_name
from ..helpers import preserve_editor_config


@editor_open(__file__)
@preserve_editor_config
@log_test_name
def test_modes(editor):
    """
    Test to install, retrieve and remove a mode.

    """
    from pyqode.core.modes import CaseConverterMode
    editor.modes.clear()
    mode = CaseConverterMode()
    editor.modes.append(mode)
    m = editor.modes.get(CaseConverterMode)
    assert len(editor.modes) == 1
    assert m == mode
    m = editor.modes.remove(CaseConverterMode)
    assert m == mode
    with pytest.raises(KeyError):
        editor.modes.remove(CaseConverterMode)

@editor_open(__file__)
@log_test_name
@preserve_editor_config
def test_panels(editor):
    """
    Test to install, retrieve and remove a panel

    """
    from pyqode.core.panels import LineNumberPanel
    panel = LineNumberPanel()
    editor.panels.append(panel, panel.Position.LEFT)
    QTest.qWait(1000)
    p = editor.panels.get(LineNumberPanel)
    assert p
    assert p.position == panel.Position.LEFT
    for i in range(4):
        p.enabled = not p.enabled
    p = editor.panels.remove(LineNumberPanel)
    assert p == panel
    with pytest.raises(KeyError):
        editor.panels.remove(LineNumberPanel)


@editor_open(__file__)
@log_test_name
@preserve_editor_config
def test_uninstall_all(editor):
    assert len(editor.modes) != 0
    assert len(editor.panels) != 0
    editor.panels.clear()
    editor.modes.clear()
    assert len(editor.modes) == 0
    assert len(editor.panels) == 0
    from pyqode.core.modes import CaseConverterMode
    from pyqode.core.panels import LineNumberPanel
    editor.modes.append(CaseConverterMode())
    editor.panels.append(LineNumberPanel(), LineNumberPanel.Position.LEFT)
    assert len(editor.modes) == 1
    assert len(editor.panels) == 1
