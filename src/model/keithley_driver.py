import atexit
from threading import Lock
from typing import Literal, Optional

import serial

import src.helpers.helpers as h


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
        return config_data.get('COMPORT', 'keithley')

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

    ###################################################################################
    ################################ SCPI Commmands ###################################
    ###################################################################################

    def _get_device_data(self) -> tuple:
        """
        GETTER: Reads the device model and serial number
        """
        command = '*IDN?'
        response = self.send_query(command).split(',')
        model = response[1].replace('MODEL ', '')
        sn = response[2]
        return (model, sn)

    def local_enable(self) -> None:
        """
        Take the Model 6482 out of remote

        Normally, during RS-232 communications, front-panel keys are operational.
        However, the user may wish to lock out front-panel keys during RS-232
        communications. See RWLock.

        This action command is used to remove the Model 6482 from the remote state
        and enables the operation of front-panel keys in a manner similar to the GPIB GTL
        command.
        """
        command = 'SYST:LOC'
        self.send_command(command)

    def remote_enable(self) -> None:
        """
        Place the Model 6482 in remote.

        You must address the instrument to listen after setting REN true before it goes
        into the remote operation.

        The Model 6482 must be in remote mode to use the following commands to
        trigger and acquire readings:

            ":INITiate and then :FETCh?"
            ":READ?"
            ":MEASure?"
        """
        command = 'SYST:REM'
        self.send_command(command)

    def reset_event_reg(self) -> None:
        """
        Clear all messages from Error Queue and reset all bits of the following event registers to 0:
            Standard Event Register
            Operation Event Register
            Measurement Event Register
            Questionable Event Register

        Note 1:
            The Standard Event Enable Register is not reset by STATus:PRESet or *CLS. Send the *ESE command
            with a zero (0) parameter value to reset all bits of that enable register to 0. See “Status byte and service
            request commands,” page Section 13-8.

        Note 2:
            STATus:PRESet has no effect on the error queue.
        """
        command = '*CLS'
        self.send_command(command)

    def reset_enable_reg(self) -> None:
        """
        Reset all bits of the following enable registers to 0:
            Operation Event Enable Register
            Measurement Event Enable Register
            Questionable Event Enable Register

        Note:
            The Standard Event Enable Register is not reset by STATus:PRESet or *CLS. Send the *ESE command
            with a zero (0) parameter value to reset all bits of that enable register to 0. See “Status byte and service
            request commands,” page Section 13-8.
        """
        command = 'STAT:PRES'
        self.send_command(command)

    def clear_error_queue(self, which: Literal[1, 2] = 2) -> None:
        """
        Clear all messages from the Error Queue

        Note:
            Use either of the two clear commands to clear the error queue.
        """
        if which == 1:
            command = 'STAT:QUE:CLE'
        else:
            command = 'SYST:ERR:CLE'
        self.send_command(command)

    def format_reg(self, name: Literal['ASC', 'HEX', 'OCT', 'BIN']) -> None:
        """
        Select data format for reading status registers. The device's default is ASCII:

        Note:
            For nondecimal formats, one of the following headers will accompany the returned value to
            indicate which format is selected:
                #B = Header for binary values
                #H = Header for hexadecimal values
                #Q = Header for octal values
        Args:
            name (str): The data format where:
                ASC=ASCII Decimal, (default)
                HEX=Hexadecimal,
                OCT= Octal format,
                BIN=Binary format,
        """
        command = f'FORM:SREG {name}'
        self.send_command(command)

    def get_status_byte_reg(self) -> str:
        """
        GETTER: Read the status byte register
        """
        command = '*STB?'
        response = self.send_query(command)
        return response

    def get_service_request_enable_reg(self) -> str:
        """
        GETTER: Read the service request enable register.
        """
        command = '*SRE?'
        response = self.send_query(command)
        return response

    def enable_output(self, bit: Literal[0, 1], channel: Literal[0, 1, 2] = 0) -> None:
        """
        Turn on or off the channel 2 output

        Args:
            channel (int): the output to command where:
                1=Output 1
                2=Output 2
            bit (int): the output state where:
                0=Off
                1=On
        """
        if channel == 0:
            command = f'OUTP1:STAT {bit}; :OUTP2:STAT {bit}'
        else:
            command = f'OUTP{channel}:STAT {bit}'
        self.send_command(command)

    def set_voltage(self, voltage: float, channel: Literal[0, 1, 2] = 0) -> None:
        """
        Set the voltage of a channel's output.

        Args:
            channel (int): the output to command where
                1=Output 1
                2=Output 2
            voltage (float): the voltage level (-30 to 30)
        """
        if channel == 0:
            command = f'SOUR1:VOLT {voltage}; :SOUR2:VOLT {voltage}'
        else:
            command = f'SOUR{channel}:VOLT {voltage}'

        self.send_command(command)

    def set_voltage_range(self, voltage: float, channel: Literal[0, 1, 2] = 0) -> None:
        if channel == 0:
            command = f'SOUR1:VOLT:RANG {voltage}; :SOUR2:VOLT:RANG {voltage}'
        else:
            command = f'SOUR{channel}:VOLT:RANG {voltage}'
        self.send_command(command)

    def get_voltage(self, channel: Literal[1, 2]) -> float:
        command = f'SOUR{channel}:VOLT?'
        response = self.send_query(command)
        voltage = float(response)
        if voltage.is_integer():
            return int(voltage)
        return voltage

    ###################################################################################
    ############################## Gemini Generated ###################################
    ###################################################################################

    def set_curr_range(self, channel: int, range_val: float) -> None:
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
        """Disables zero check and returns the current reading of the active channel."""
        # Ensure Zero Check is off before reading
        self.set_zero_check(False)
        raw_response = self.send_query('READ?')
        # The 6482 returns a string like '+1.2345E-09A, +0.0000E+00, ...'
        # We split by comma and convert the first element to float
        return float(raw_response.split(',')[0].replace('A', ''))

    def setup_dual_channel(self) -> None:
        """Configures the instrument to return data for both channels."""
        # Set data elements: Current, Timestamp, and Status
        self.send_command('FORM:ELEM CURR, TIME, STAT')
        # Turn off Zero Check for both (Note: 6482 ZCH is often global or per-channel)
        self.send_command('SYST:ZCH OFF')

    def get_curr_readings(self) -> dict[str, float]:
        """
        Triggers a reading and returns a dictionary with Ch1 and Ch2 values.
        The 6482 returns: [Ch1_Curr, Ch1_Time, Ch1_Stat, Ch2_Curr, Ch2_Time, Ch2_Stat]
        """
        raw_data = self.send_query('READ?')

        # Split the comma-separated string
        parts = raw_data.split(',')

        # Safety check: Ensure we have enough parts for two channels
        if len(parts) < 2:
            raise ValueError(f'Unexpected response format: {raw_data}')

        # Parse and clean strings (removing 'A' suffix if present)
        ch1_value = float(parts[0].replace('A', ''))
        ch2_value = float(parts[1].replace('A', ''))

        return {'ch1': ch1_value, 'ch2': ch2_value}


if __name__ == '__main__':
    import time

    # connect to the Keithley picoammeter
    k = Keithley()

    # clear all the registers
    k.reset_event_reg()

    # enable remote control
    k.remote_enable()

    # get the model and serial number of the device
    print(f'Keithley Model = {k.model}')
    print(f'Serial Number = {k.sn}')

    # set the voltage range of both channels to 30 V
    k.set_voltage_range(30)

    # set the voltage of both channels to 30 V
    k.set_voltage(30)

    # enable the output of the voltage
    k.enable_output(1)
    time.sleep(2)

    # take a current reading on both channels
    print(k.get_curr_readings())

    # set the voltage to 0 V
    k.set_voltage(voltage=0)

    # disable the output voltage
    k.enable_output(0)

    # disable the remote control
    k.local_enable()
