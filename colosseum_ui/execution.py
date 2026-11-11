"""Asynchronous CLI process ownership; Qt dependencies are never modified."""
import codecs
import sys
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, QTimer, Signal

_STOP_TIMEOUT_MS = 5000


@dataclass(frozen=True)
class RunRequest:
    kind: str
    path: str
    config: str = ""
    parameters: str = ""
    metadata: str = ""
    debug: bool = False
    no_sleep: bool = False

    def arguments(self):
        args = ["-u", "-m", "colosseum.runner.cli", self.kind, self.path]
        for flag, value in (("config", self.config), ("parameters", self.parameters), ("metadata", self.metadata)):
            if value.strip():
                args.extend(["--" + flag, value.strip()])
        if self.debug:
            args.append("--debug")
        if self.no_sleep:
            args.append("--no-sleep")
        return args


class Execution(QObject):
    output = Signal(str)
    state_changed = Signal(str)
    completed = Signal(int)

    def __init__(self, cwd, parent=None):
        super().__init__(parent)
        self.state = "Ready"
        self.process = QProcess(self)
        self.process.setWorkingDirectory(str(cwd))
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        environment = QProcessEnvironment.systemEnvironment()
        environment.insert("PYTHONIOENCODING", "utf-8")
        self.process.setProcessEnvironment(environment)
        self.process.readyReadStandardOutput.connect(self.read)
        self.process.started.connect(self.started)
        self.process.finished.connect(self.finished)
        self.process.errorOccurred.connect(self.error)
        self.deadline = QTimer(self)
        self.deadline.setSingleShot(True)
        self.deadline.timeout.connect(self.process.kill)
        self.decoder = codecs.getincrementaldecoder("utf-8")("replace")

    @property
    def active(self):
        return self.state in {"Starting", "Running", "Stopping"}

    def change_state(self, state):
        self.state = state
        self.state_changed.emit(state)

    def start(self, request):
        if self.active:
            return False
        self.decoder.reset()
        self.change_state("Starting")
        executable = Path(sys.executable)
        if executable.name.lower() == "pythonw.exe":
            executable = executable.with_name("python.exe")
        self.process.start(str(executable), request.arguments())
        return True

    def started(self):
        if self.state == "Stopping":
            self.stop()
        else:
            self.change_state("Running")

    def read(self):
        text = self.decoder.decode(bytes(self.process.readAllStandardOutput()))
        if text:
            self.output.emit(text)

    def stop(self):
        if not self.active:
            return
        self.change_state("Stopping")
        if self.process.state() == QProcess.ProcessState.Starting:
            return
        if sys.platform == "win32":
            self.process.kill()
        else:
            self.process.terminate()
        self.deadline.start(_STOP_TIMEOUT_MS)

    def error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.output.emit(self.process.errorString() + "\n")
            self.finished(-1)

    def finished(self, code, status=None):
        self.deadline.stop()
        self.read()
        tail = self.decoder.decode(b"", final=True)
        if tail:
            self.output.emit(tail)
        stopped = self.state == "Stopping"
        self.change_state("Stopped" if stopped else f"Finished (exit {code})")
        self.completed.emit(code)
