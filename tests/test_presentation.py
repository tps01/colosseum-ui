import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path

from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication, QLabel

from colosseum_ui.app import Inspector
from colosseum_ui.artifacts import RunBrowserRow, RunBrowserSnapshot, RunDirectoryEntry


def test_themes_and_large_history(tmp_path):
    app = QApplication.instance() or QApplication([])
    window = Inspector(tmp_path)
    window.show()
    window.log.setPlainText("unchanged raw text")
    window.appearance.setCurrentText("Dark")
    dark = window.palette().color(QPalette.ColorRole.Base).lightness()
    window.appearance.setCurrentText("Light")
    assert window.palette().color(QPalette.ColorRole.Base).lightness() > dark
    assert window.log.toPlainText() == "unchanged raw text"
    window.wrap.setChecked(True)
    assert window.log.lineWrapMode() == window.log.LineWrapMode.WidgetWidth
    window.resize(960, 640)
    app.processEvents()
    assert window.centralWidget().geometry().width() <= window.width()
    window.generation += 1
    root = Path(tmp_path / "outputs")
    rows = [RunBrowserRow(RunDirectoryEntry(root / str(i), root), "PASS", float(i)) for i in range(10000)]
    window.populate(RunBrowserSnapshot(rows))
    assert window.model.item(0).rowCount() == 1
    window.tree.expand(window.model.item(0).index())
    for _ in range(500):
        app.processEvents()
        if window.model.item(0).rowCount() == 10000:
            break
    assert window.model.item(0).rowCount() == 10000
    window.close()


def test_console_preserves_paged_unicode_and_history():
    from colosseum_ui.console import _PAGE_CHARS, Console
    app = QApplication.instance() or QApplication([])
    console = Console()
    raw = ("a\u2603\U0001f600\n" * _PAGE_CHARS) + "final text"
    console.append_live(raw)
    assert len(console.toPlainText()) <= _PAGE_CHARS
    pieces = []
    for i in range(len(console.live.offsets)):
        pieces.append(console.live.page(i))
    assert "".join(pieces) == raw
    console.setPlainText("historical log")
    console.append_live("new output")
    assert console.toPlainText() == "historical log"
    console.show_live()
    assert console.toPlainText().endswith("final textnew output")
    console.release()
    app.processEvents()


def test_additional_fields_collapse_without_losing_values(tmp_path):
    app = QApplication.instance() or QApplication([])
    window = Inspector(tmp_path)
    assert window.additional_widget.isHidden()
    window.fields["Parameters"].setText("params.toml")
    window.fields["Metadata"].setText("meta.toml")
    window.additional_button.setChecked(True)
    app.processEvents()
    assert not window.additional_widget.isHidden()
    assert window.fields["Parameters"].text() == "params.toml"
    window.additional_button.setChecked(False)
    app.processEvents()
    assert window.additional_widget.isHidden()
    assert window.fields["Metadata"].text() == "meta.toml"
    window.close()


def test_page_controls_live_inside_log_and_only_show_for_multiple_pages(tmp_path):
    from colosseum_ui.console import _PAGE_CHARS
    app = QApplication.instance() or QApplication([])
    window = Inspector(tmp_path)
    assert window.tabs.widget(0).layout().indexOf(window.log) >= 0
    assert not window.previous_page.isVisible()
    window.log.setPlainText("x" * (_PAGE_CHARS + 2))
    app.processEvents()
    assert not window.previous_page.isHidden()
    assert not window.next_page.isHidden()
    assert not window.page_label.isHidden()
    window.log.turn_page(1)
    assert "Page 2 of 2" == window.page_label.text()
    window.log.setPlainText("one page")
    app.processEvents()
    assert not window.previous_page.isVisible()
    window.close()


def test_file_actions_live_in_files_pane(tmp_path):
    QApplication.instance() or QApplication([])
    window = Inspector(tmp_path)
    assert window.right_tabs.widget(1) is window.files_page
    header = window.files_page.layout().itemAt(0).layout()
    for button in (window.refresh_button, window.expand_button, window.collapse_button):
        assert header.indexOf(button) >= 0
        assert button.isEnabled()
    assert window.tree.isHeaderHidden()
    window.close()


def test_status_words_are_colored_and_other_text_is_normal(tmp_path):
    QApplication.instance() or QApplication([])
    window = Inspector(tmp_path)
    assert window.display_status("PASS") == "Pass"
    assert window.display_status("FAIL") == "Fail"
    assert window.display_status("ERROR") == "Error"
    assert window.display_status("incomplete") == "Incomplete"
    assert window.status_color("PASS") != window.status_color("FAIL")
    assert window.status_color("ERROR") != window.status_color("INCOMPLETE")
    assert window.status_color("NO TEST") == window.palette().color(window.palette().ColorRole.Text)
    window.close()


def test_files_expand_and_collapse_actions(tmp_path):
    from colosseum_ui.artifacts import RunBrowserRow, RunBrowserSnapshot, RunDirectoryEntry
    app = QApplication.instance() or QApplication([])
    window = Inspector(tmp_path)
    root = tmp_path / "outputs"
    rows = [RunBrowserRow(RunDirectoryEntry(root / str(i), root), "PASS", float(i)) for i in range(3)]
    window.populate(RunBrowserSnapshot(rows))
    group = window.model.item(0)
    assert group.rowCount() == 1
    window.right_tabs.setCurrentWidget(window.files_page)
    window.expand_button.click()
    for _ in range(50):
        app.processEvents()
    assert window.tree.isExpanded(group.index())
    assert group.rowCount() == 3
    window.collapse_button.click()
    app.processEvents()
    assert not window.tree.isExpanded(group.index())
    window.close()


def test_recent_rows_reserve_height_for_name_and_timestamp(tmp_path):
    from colosseum_ui.artifacts import RunBrowserRow, RunBrowserSnapshot, RunDirectoryEntry
    QApplication.instance() or QApplication([])
    window = Inspector(tmp_path)
    root = tmp_path / "outputs"
    rows = [RunBrowserRow(RunDirectoryEntry(root / "long_named_run", root), "PASS", 1.0)]
    window.populate(RunBrowserSnapshot(rows))
    item = window.recent.item(0)
    row_widget = window.recent.itemWidget(item)
    assert item.sizeHint().height() >= row_widget.sizeHint().height()
    labels = row_widget.findChildren(QLabel)
    assert len(labels) == 3
    assert all(not label.wordWrap() for label in labels)
    window.close()
