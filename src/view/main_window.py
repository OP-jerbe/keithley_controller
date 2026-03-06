from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from qt_material import apply_stylesheet

import src.helpers.helpers as h
from src.model.keithley_driver import Keithley


class MainWindow(QMainWindow):
    def __init__(self, keithley: Keithley) -> None:
        super().__init__()
        self.keithley = keithley
        self._create_gui()

    def _create_keithley_tab(self) -> None:

        # --- Create the Keithely tab ---

        self.keithley_tab = QWidget()
        keithley_tab_layout = QVBoxLayout(self.keithley_tab)

        # --- Current Readings Section ---

        current_gb = QGroupBox('Current Readings')
        current_layout = QGridLayout(current_gb)

        self.ch1_label = QLabel('Screen Current (A)')
        self.ch1_current_label = QLabel('<CH1 Reading>')

        self.ch2_label = QLabel('Cup Current (A)')
        self.ch2_current_label = QLabel('<CH2 Reading>')

        current_layout.addWidget(
            self.ch1_label,
            0,
            0,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
        )
        current_layout.addWidget(
            self.ch2_label,
            0,
            1,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
        )
        current_layout.addWidget(
            self.ch1_current_label,
            1,
            0,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
        )
        current_layout.addWidget(
            self.ch2_current_label,
            1,
            1,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
        )

        # --- Voltage Output Section ---

        voltage_gb = QGroupBox('Voltage Output')
        voltage_layout = QGridLayout(voltage_gb)

        self.enable_output_btn = QPushButton('Enable Output')
        self.enable_output_btn.setCheckable(True)

        self.set_ch1_voltage_le = QLineEdit(placeholderText='Enter Voltage (V)')
        self.set_ch2_voltage_le = QLineEdit(placeholderText='Enter Voltage (V)')

        voltage_layout.addWidget(self.set_ch1_voltage_le, 0, 0)
        voltage_layout.addWidget(self.set_ch2_voltage_le, 0, 1)
        voltage_layout.addWidget(self.enable_output_btn, 1, 0, 1, 2)

        # --- Assemble the Keithley tab layout ---

        keithley_tab_layout.addWidget(current_gb)
        keithley_tab_layout.addWidget(voltage_gb)

        # --- Add tab to widget ---
        self.tabs.addTab(self.keithley_tab, 'Keithley')

    def _create_gui(self) -> None:
        ver = h.get_app_version()
        self.setWindowTitle(f'Stage Controller v{ver}')
        self.setWindowIcon(h.get_icon())
        self.resize(400, 250)
        apply_stylesheet(self, theme='dark_lightgreen.xml', invert_secondary=True)
        self.setStyleSheet(
            self.styleSheet()
            + """QLineEdit, QTextEdit, QComboBox {color: lightgreen;}"""
        )

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            self.styleSheet() + 'QLineEdit, QTextEdit, QComboBox {color: lightgreen;}'
        )

        self.setCentralWidget(self.tabs)
        self._create_keithley_tab()

    def update_current_reading_labels(self, currents: dict[str, float]) -> None:
        try:
            screen_current = str(currents['ch1'])
            cup_current = str(currents['ch2'])
            self.ch1_current_label.setText(screen_current)
            self.ch2_current_label.setText(cup_current)
        except:
            self.ch1_current_label.setText('ERROR')
            self.ch2_current_label.setText('ERROR')
