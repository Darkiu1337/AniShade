"""Background workers so downloads and installs never freeze the window."""

from __future__ import annotations

import traceback
from collections.abc import Callable

from PySide6.QtCore import QThread, Signal

TaskBody = Callable[[Callable[[str], None], Callable[[int, int], None]], object]


class Task(QThread):
    log = Signal(str)
    progress = Signal(int, int)
    result = Signal(object)
    error = Signal(str, str, object)

    def __init__(self, body: TaskBody, parent=None) -> None:
        super().__init__(parent)
        self._body = body

    def run(self) -> None:
        try:
            value = self._body(self.log.emit, self.progress.emit)
        except Exception as exc:  # noqa: BLE001 - surfaced in the UI
            self.error.emit(str(exc) or exc.__class__.__name__, traceback.format_exc(), exc)
            return
        self.result.emit(value)


def run_task(body: TaskBody, on_log, on_progress, on_result, on_error) -> Task:
    task = Task(body)
    task.log.connect(on_log)
    task.progress.connect(on_progress)
    task.result.connect(on_result)
    task.error.connect(on_error)
    task.finished.connect(task.deleteLater)
    task.start()
    return task
