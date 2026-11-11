"""Paged raw-text storage keeps the visible log document bounded."""
import tempfile

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QPlainTextEdit

_PAGE_CHARS = 256 * 1024


class LogStore:
    def __init__(self):
        self.file = tempfile.TemporaryFile(mode="w+", encoding="utf-8", newline="")  # noqa: SIM115 - owned until close
        self.offsets = [0]
        self.tail_size = 0

    def append(self, text):
        self.file.seek(0, 2)
        while text:
            if self.tail_size == _PAGE_CHARS:
                self.offsets.append(self.file.tell())
                self.tail_size = 0
            part = text[:_PAGE_CHARS - self.tail_size]
            self.file.write(part)
            self.tail_size += len(part)
            text = text[len(part):]

    def page(self, index):
        self.file.seek(self.offsets[index])
        return self.file.read(_PAGE_CHARS)

    def close(self):
        self.file.close()


class Console(QPlainTextEdit):
    page_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self.live = LogStore()
        self.history = LogStore()
        self.store = self.live
        self.page_index = 0
        self.setReadOnly(True)

    def render(self):
        super().setPlainText(self.store.page(self.page_index))
        self.page_changed.emit(f"Page {self.page_index + 1} of {len(self.store.offsets)}")

    def turn_page(self, delta):
        self.page_index = max(0, min(len(self.store.offsets) - 1, self.page_index + delta))
        self.render()

    def setPlainText(self, text):
        self.history.close()
        self.history = LogStore()
        self.history.append(text)
        self.store = self.history
        self.page_index = 0
        self.render()

    def start_live(self):
        self.live.close()
        self.live = LogStore()
        self.show_live()

    def show_live(self):
        self.store = self.live
        self.page_index = len(self.live.offsets) - 1
        self.render()

    def append_live(self, text):
        visible = self.store is self.live
        last = self.page_index == len(self.live.offsets) - 1
        bar = self.verticalScrollBar()
        follow = visible and last and bar.value() == bar.maximum()
        old_pages = len(self.live.offsets)
        self.live.append(text)
        if not visible:
            return
        if follow and old_pages != len(self.live.offsets):
            self.page_index = len(self.live.offsets) - 1
            self.render()
        elif last:
            # Refresh only the bounded page when it changes; never discard stored text.
            position = bar.value()
            self.render()
            bar.setValue(position)
        else:
            self.page_changed.emit(f"Page {self.page_index + 1} of {len(self.live.offsets)}")
        if follow:
            bar.setValue(bar.maximum())

    def release(self):
        self.live.close()
        self.history.close()
