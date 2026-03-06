import sys
from typing import NoReturn

from PySide6.QtWidgets import QApplication

from src.controller.controller import Controller
from src.model.keithley_driver import Keithley
from src.view.main_window import MainWindow


def run_app() -> NoReturn:
    """
    Sets the version of application build, creates the app and main window, then
    executes the application event loop. `app.exec() == 0` when the event loop
    stops. `sys.exit(0)` terminates the application.
    """
    app = QApplication([])
    keithley = Keithley()
    view = MainWindow(keithley)
    _ = Controller(keithley, view)
    view.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    run_app()
