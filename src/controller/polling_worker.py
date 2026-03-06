import traceback

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from src.model.keithley_driver import Keithley


class PollingWorker(QObject):
    result_ready_sig = Signal(dict)
    error_sig = Signal(str, str)

    def __init__(self, keithley: Keithley) -> None:
        super().__init__()
        self.keithley = keithley
        self.timer = QTimer(self, interval=500)
        self.timer.timeout.connect(self.get_readings)

    @Slot()
    def do_work(self) -> None:
        self.timer.start()

    def get_readings(self) -> None:
        try:
            currents = self.keithley.get_curr_readings()
            self.result_ready_sig.emit(currents)
        except Exception as e:
            self.timer.stop()
            tb = traceback.format_exc()
            self.error_sig.emit(str(e), tb)
