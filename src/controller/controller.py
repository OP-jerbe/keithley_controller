from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot

from src.controller.polling_worker import PollingWorker
from src.model.keithley_driver import Keithley
from src.view.main_window import MainWindow


class Controller(QObject):
    start_polling_sig = Signal()

    def __init__(self, keithley: Keithley, view: MainWindow) -> None:
        super().__init__()
        self.keithley = keithley
        self.mw = view
        self._init_keithley()
        self._init_polling()

    def __del__(self) -> None:
        self.polling_thread.quit()
        self.polling_thread.wait()

    def _init_keithley(self) -> None:
        self.keithley.reset_event_reg()
        self.keithley.remote_enable()
        self.keithley.set_voltage_range(30)
        self.keithley.set_voltage(30)
        self.keithley.enable_output(1)
        self.mw.set_ch1_voltage_le.setText(str(self.keithley.get_voltage(1)))
        self.mw.set_ch2_voltage_le.setText(str(self.keithley.get_voltage(2)))

    def _init_polling(self) -> None:
        # Initialize the polling thread
        self.polling_thread = QThread()
        self.polling_thread.setObjectName('PollingThread')

        # Initialize the polling worker
        self.polling_worker = PollingWorker(self.keithley)
        self.polling_worker.moveToThread(self.polling_thread)

        # When thread is finished, tell the polling worker to delete itself
        self.polling_thread.finished.connect(self.polling_worker.deleteLater)

        # Connect Controller signal to PollingWorker slot
        self.start_polling_sig.connect(self.polling_worker.do_work)

        # Connect the PollingWorker signal back to Controller slot
        self.polling_worker.result_ready_sig.connect(
            self.receive_polling_worker_result_ready_sig,
            Qt.ConnectionType.QueuedConnection,
        )
        # self.polling_worker.error_sig.connect(
        #     self.receive_polling_worker_error_sig, Qt.ConnectionType.QueuedConnection
        # )

        # Start the thread's event loop
        self.polling_thread.start()

        # Start polling the stage for motor position data
        self.start_polling_sig.emit()

    @Slot(dict)
    def receive_polling_worker_result_ready_sig(
        self, currents: dict[str, float]
    ) -> None:
        self.mw.update_current_reading_labels(currents)
