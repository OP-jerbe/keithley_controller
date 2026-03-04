import atexit
from threading import Lock
from typing import Optional

import serial

import src.helpers.helpers as h

# from src.model.keithley_driver import Keithley
# k = Keithley


class Keithley:
    ENCODING = 'utf-8'
    TERM_CHAR = '\r'

    def __init__(self, com_port: Optional[str] = None) -> None:
        self._lock = Lock()
        self._ser: Optional[serial.Serial] = None
        self._com_port = com_port or self._get_com_port()
        self.is_connected = False
        self.model: Optional[str] = None
        self.sn: Optional[str] = None
        atexit.register(self.close_conn)

        self.open_conn(self._com_port)
        if self.is_connected:
            self.model, self.sn = self._get_device_data()

    def __del__(self) -> None:
        self.close_conn()

    @staticmethod
    def _get_com_port() -> str:
        """
        Reads the comport from the ini file.
        """
        config_data = h.load_ini()
        return config_data.get('COMPORT', 'port')

    def open_conn(self, port: str, baudrate: int = 9600, timeout: float = 1.0) -> None:
        """
        Establishes a serial connection to the instrument at the specified COM port.

        Args:
            port (str): The COM port where the stage is connected (e.g., 'COM3' or '/dev/ttyUSB0').
                The port name is automatically converted to uppercase.
            baudrate (int): The serial communication baud rate in bits per second. Defaults to 9600.
            timeout (float): The read and write timeout in seconds. Defaults to 1.0.
        """
        try:
            self._ser = serial.Serial(
                port=port.upper(),
                baudrate=baudrate,
                timeout=timeout,
                write_timeout=timeout,
            )
            self.is_connected = True

        except Exception as e:
            print(f'Failed to make a serial connection to {port}.\n\n{str(e)}')
            self._ser = None
            self.is_connected = False

    def close_conn(self) -> None:
        """Closes an open serial port"""
        if self._ser and self._ser.is_open:
            self._ser.close()
            self._ser = None
            self.is_connected = False

    def send_command(
        self,
        command: str,
        term_char: Optional[str] = None,
        encoding: Optional[str] = None,
    ) -> None:
        """
        Sends a command string to the stage without expecting a response.

        Args:
            command (str): The command string to send to the instrument.
                The carriage return termination character is appended automatically.
        """
        term_char = term_char or self.TERM_CHAR
        encoding = encoding or self.ENCODING

        if not self._ser or not self._ser.is_open:
            raise RuntimeError('No serial connection or the connection is not open.')

        if not command.endswith(term_char):
            command += term_char

        with self._lock:
            try:
                self._ser.write(command.encode(encoding))
            except Exception as e:
                raise ConnectionError(f'Serial Communication Error\n\n{str(e)}')

        print(f'Command: "{command.strip()}"')

    def send_query(
        self,
        query: str,
        term_char: Optional[str] = None,
        encoding: Optional[str] = None,
    ) -> str:
        """
        Sends a query command to the stage, reads the response, and handles unsolicited output.

        Args:
            query (str): The query command string to send.
                The carriage return termination character is appended automatically.

        Returns:
            str: The decoded and stripped string response received from the instrument.
        """
        term_char = term_char or self.TERM_CHAR
        encoding = encoding or self.ENCODING

        if not self._ser or not self._ser.is_open:
            raise RuntimeError('No serial connection or the connection is not open.')
        if not query.endswith(term_char):
            query += term_char

        with self._lock:
            try:
                self._ser.reset_input_buffer()
                self._ser.write(query.encode(encoding))
                response = self._readline(term_char, encoding)
                # print(f'query {response = }')
            except Exception as e:
                raise ConnectionError(f'Serial Communication Error\n\n{str(e)}')

        return response

    def _readline(self, term_char: str, encoding: str) -> str:
        """
        Reads data from the serial port until the termination character is found.

        Returns:
            str: The decoded and stripped line of response data.
        """
        if not self._ser or not self._ser.is_open:
            raise RuntimeError('No serial connection or the connection is not open.')

        return self._ser.read_until(term_char.encode(encoding)).decode(encoding).strip()

    def _get_device_data(self) -> tuple:
        response = self.send_query('*IDN?').split(',')
        model = response[1].replace('MODEL ', '')
        sn = response[2]
        return (model, sn)

    def set_range(self, channel: int, range_val: float) -> None:
        """Sets a fixed current range. Use 0 for Auto-range."""
        if range_val == 0:
            self.send_command(f'SENS{channel}:CURR:RANG:AUTO ON')
        else:
            self.send_command(f'SENS{channel}:CURR:RANG {range_val}')

    def set_nplc(self, channel: int, nplc: float) -> None:
        """Sets integration time (0.1 is fast, 1 is balanced, 10 is high-res)."""
        self.send_command(f'SENS{channel}:CURR:NPLC {nplc}')

    def set_zero_check(self, state: bool) -> None:
        """Turns Zero Check ON or OFF."""
        val = 'ON' if state else 'OFF'
        self.send_command(f'SYST:ZCH {val}')

    def get_current(self) -> float:
        """Disables zero check and returns the current reading."""
        # Ensure Zero Check is off before reading
        self.set_zero_check(False)
        raw_response = self.send_query('READ?')
        # The 6482 returns a string like '+1.2345E-09A, +0.0000E+00, ...'
        # We split by comma and convert the first element to float
        return float(raw_response.split(',')[0].replace('A', ''))
