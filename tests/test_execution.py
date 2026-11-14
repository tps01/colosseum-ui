import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication

from colosseum_extensions.ui.app import Inspector
from colosseum_extensions.ui.execution import Execution, RunRequest


def wait(app, condition):
    deadline = time.monotonic() + 20
    while not condition() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.01)
    assert condition()


def test_arguments():
    request = RunRequest("run-suite", "a b.toml", "c.toml", "p.toml", "m.toml", True, True)
    assert request.arguments()[3:] == ["run-suite", "a b.toml", "--config", "c.toml", "--parameters",
                                       "p.toml", "--metadata", "m.toml", "--debug", "--no-sleep"]


def test_process_lifecycle(tmp_path):
    app = QApplication.instance() or QApplication([])
    worker = Execution(tmp_path)
    output, results = [], []
    worker.output.connect(output.append)
    worker.completed.connect(results.append)
    script = tmp_path / "sample.py"
    script.write_text("def main():\n    print('live marker', flush=True)\n")
    request = RunRequest("run", str(script))
    assert worker.start(request)
    assert not worker.start(request)
    wait(app, lambda: bool(results))
    assert results[-1] == 0
    assert "live marker" in "".join(output)
    script.write_text("def main():\n    raise RuntimeError('intentional failure')\n")
    worker.start(request)
    wait(app, lambda: len(results) == 2)
    assert results[-1] != 0
    script.write_text("import time\ndef main():\n    print('slow marker', flush=True)\n    time.sleep(60)\n")
    worker.start(request)
    wait(app, lambda: "slow marker" in "".join(output))
    worker.stop()
    wait(app, lambda: len(results) == 3)
    assert worker.state == "Stopped"
    worker.start(request)
    worker.stop()
    wait(app, lambda: len(results) == 4)
    assert not worker.active


def test_window_controls(tmp_path):
    app = QApplication.instance() or QApplication([])
    window = Inspector(tmp_path)
    assert not window.run_button.isEnabled()
    script = tmp_path / "ok.py"
    script.write_text("def main():\n    print('window marker')\n")
    window.fields["Test / Suite"].setText(str(script))
    assert window.run_button.isEnabled()
    window.start_run("run", "Test / Suite")
    assert not window.run_button.isEnabled()
    wait(app, lambda: not window.execution.active)
    assert "window marker" in window.log.toPlainText()
    window.close()


def test_suite(tmp_path):
    app = QApplication.instance() or QApplication([])
    worker = Execution(tmp_path)
    results, output = [], []
    worker.completed.connect(results.append)
    worker.output.connect(output.append)
    script = tmp_path / "case.py"
    script.write_text("def main():\n    print('suite marker')\n")
    suite = tmp_path / "suite.toml"
    suite.write_text('name = "ui_suite"\ntests = ["case.py"]\n')
    worker.start(RunRequest("run-suite", str(suite)))
    wait(app, lambda: bool(results))
    assert results == [0]
    assert "suite marker" in "".join(output)
    logs = list((tmp_path / "outputs").glob("*/debug.log"))
    assert logs
    assert "Suite overall result: PASS" in logs[0].read_text(encoding="utf-8")


def test_dry_run_argument():
    for kind in ("run", "run-suite"):
        assert "--dry-run" in RunRequest(kind, "sample", dry_run=True).arguments()


def test_runner_accepts_prompt_input(tmp_path):
    app = QApplication.instance() or QApplication([])
    worker = Execution(tmp_path)
    output, results = [], []
    worker.output.connect(output.append)
    worker.completed.connect(results.append)
    script = tmp_path / "prompt_test.py"
    script.write_text("def main():\n    print('PROMPT READY', flush=True)\n    print('ANSWER=' + input(), flush=True)\n")
    worker.start(RunRequest("run", str(script)))
    wait(app, lambda: "PROMPT READY" in "".join(output) or bool(results))
    worker.send_input("response")
    wait(app, lambda: bool(results))
    assert results[-1] == 0
    assert "ANSWER=response" in "".join(output)
