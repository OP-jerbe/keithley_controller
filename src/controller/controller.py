from PySide6.QtCore import QObject

from src.model.keithley_driver import Keithley
from src.view.main_window import MainWindow


class Controller(QObject):
    def __init__(self, keithley: Keithley, view: MainWindow) -> None:
        super().__init__()
        self.keithley = keithley
        self.mw = view
        self._init_keithley()

    def _init_keithley(self) -> None:
        self.keithley.reset_event_reg()
        self.keithley.remote_enable()
        self.keithley.set_voltage_range(30)
        self.keithley.set_voltage(30)
        self.keithley.enable_output(1)
        self.mw.set_ch1_voltage_le.setText(str(self.keithley.get_voltage(1)))
        self.mw.set_ch2_voltage_le.setText(str(self.keithley.get_voltage(2)))
