from .controller import controller, mode, system_status
from .profile import profile_status
from enum import Enum

class PID_table(Enum):
    """Enums for PID table selection.
    """
    HEATING_HNC = 0     # Heating in Heating & Cooling (HNC) Mode
    COOLING_HNC = 1     # Cooling in Heating & Cooling (HNC) Mode
    HEATING_HO = 2      # Heating in Heating Only (HO) Mode
    COOLING_CO = 3      # Cooling in Cooling Only (CO) Mode


class temperature_mode(Enum):
    """Enums for temperature mode selection.
    """
    HEATING_ONLY = 0
    HEATING_AND_COOLING = 1
    COOLING_ONLY = 2


class unit(Enum):
    """Enums for controller unit usage.
    """
    CELCIUS = 1
    KELVIN = 2
    FAHRENHEIT = 3
    RELATIVE_HUMIDITY = 4
    PASCAL = 5
    BAR = 6
    POUND_PER_SQUARE_INCH = 7
    TORR = 8
    KILOPASCAL = 9
    VOLT = 10
    NEWTON = 11

class temperature:
    def __init__(self, mode=mode.USB, baudrate=38400, port='COM3'):
        self._controller = controller(mode, baudrate, port)
    
    def get_system_information(self):
        """Information about the system:
        company (str): Company name
        model (str): Model number
        serial (str): Serial number
        firmware (str): firmware version

        Returns:
            (str, str, str, str): Tuple of system information.
        """
        data = self._controller._send_command('*IDN?').strip().split(',')
        company = data[0]
        model = data[1]
        serial = data[2]
        firmware = data[3]
        return company, model, serial, firmware

    def get_runtime_information(self):
        """Return runtime information, such as temperatures, execution
        statuses, and error codes. Refer to the SCPI manual for a more
        detailed description on return values. Here is a short description
        of all returned values:
        sx (int):           Active slave number
        pv (float):         Process Variable (PV) – Current temperature of
                            the Stage/Plate/Chuck (°C)
        mv (float):         Monitor Value (MV) – Value used to measure
                            monitor temperature (°C)
        tsp (float):        Target Set Point (TSP) – Final target temperature
                            for Hold or Ramp command (°C)
        csp (float):        Current Set Point (CSP) – Current target
                            temperature (°C)
        rt (float):         Ramp Rate (RT) – Rate of PV change during Ramp
                            command (°C/minute)
        pp (float):         Percent Power (PP) – Percentage of total output
                            power being applied to Stage/Plate/Chuck (%)
        s_status (system_status):     Current system status code
        p_status (profile_status):    Current profile execution status code
        p (int):            Active profile number
        i (int):            Current index of profile during execution
        error_status (int): Error code status ID

        Returns:
            (int, float, float, float, float, float, float, system_status,
            profile_status, int, int, int): Tuple with information about the
            controller at runtime.
        """
        rtin_raw = self._controller._send_command('TEMP:RTIN?')
        rtin = (rtin_raw.split('MK')[1]).split(':')
        sx = int(rtin[1])
        pv = float(rtin[2])
        mv = float(rtin[3])
        tsp = float(rtin[4])
        csp = float(rtin[5])
        rt = float(rtin[6])
        pp = float(rtin[7])
        s_status = system_status(int(rtin[8]))
        profile = rtin[9].split(',')
        p_status = profile_status(int(profile[0]))
        p = int(profile[1])
        i = int(profile[2])
        error_status = int(rtin[10])

        return (sx, pv, mv, tsp, csp, rt, pp, s_status, p_status,
                p, i, error_status)

    def get_process_variables(self):
        """Return process variable values for connected slaves.

        Returns:
            (float tuple):  Process Variable (PV) – Current temperature of
                            all connected slaves
        """
        pv_raw = self._controller._send_command('TEMP:CTEM?')
        pv = eval(f'({pv_raw},)')
        return pv

    def get_monitor_values(self):
        """Return monitor values for connected slaves.

        Returns:
            (float tuple):  Monitor Value (MV) – Monitor temperature of all
                            connected slaves
        """
        mv_raw = self._controller._send_command('TEMP:MTEM?')
        mv = eval(f'({mv_raw},)')
        return mv

    def get_protection_sensors(self):
        """Return protection sensor values for connected slaves.

        Returns:
            (float tuple): Protection sensor value of all connected slaves.
        """
        ps_raw = self._controller._send_command('TEMP:PTEM?')
        ps = eval(f'({ps_raw},)')
        return ps

    def hold(self, tsp):
        """Takes the desired setpoint (tsp) as a parameter, and will attempt
        to reach the TSP as fast as possible, and hold that value until
        directed otherwise. Passing a value outside of the controller's range
        will trigger Error Code 4 on the device.

        Args:
            tsp (float):    Target Set Point (TSP) – Final target temperature
                            for Hold or Ramp command (°C)

        Raises:
            ValueError: If tsp is out of range
        """
        max, min = self.get_operation_range()
        if tsp >= min and tsp <= max:
            error = int(self._controller._send_command(f'TEMP:HOLD {tsp}; ERR?'))
            if error == 4:
                self.stop()
                raise ValueError('Set point value is out of range')
        else:
            raise ValueError('Set point value is out of range')

    def ramp(self, tsp, rt):
        """Takes the desired setpoint (tsp) and ramp rate (rt) as parameters,
        and will attempt to reach the current setpoint value according to the
        specified ramp rate until it reaches the setpoint. Once it reaches the
        target, it will maintain that value until directed otherwise. Passing a
        value outside of the controller's range will trigger Error Code 4 on
        the device.

        Args:
            tsp (float):    Target Set Point (TSP) – Final target temperature
                            for Hold or Ramp command (°C)
            rt (float):     Ramp Rate (RT) – Rate of PV change during Ramp
                            command (°C/minute)

        Raises:
            ValueError: If tsp is out of range
        """
        max, min = self.get_operation_range()
        if tsp >= min and tsp <= max:
            error = int(self._controller._send_command(f'TEMP:RAMP {tsp},{rt}; ERR?'))
            if error == 4:
                self.stop()
                raise ValueError('Set point value is out of range')
        else:
            raise ValueError('Set point value is out of range')

    def rpp(self, pp=0.0):
        """Takes the desired power level (PP) as a parameter, and will
        attempt to reach the PP level as fast as possible, and hold that value
        until directed otherwise.

        Args:
            pp (float, optional): Value between -1.0 and 1.0. Defaults to 0.0.

        Raises:
            ValueError: If pp is out of range.
        """
        if (pp >= -1.0 and pp <= 1.0):
            self._controller._send_command(f'TEMP:RPP {pp}', False)
        else:
            raise ValueError('Power percentage is out of range')

    def stop(self):
        """Stops all currently running commands.
        """
        self._controller._send_command('TEMP:STOP', False)

    def get_current_pid(self):
        """Get the current PID value.
        p (float): The proportional value
        i (float): The integral value
        d (float): The derivative value

        Returns:
            (float, float, float): PID tuple
        """
        pid = self._controller._send_command('TEMP:PID?').split(',')
        p = float(pid[0])
        i = float(pid[1])
        d = float(pid[2])
        return p, i, d

    def get_pid(self, state, index):
        """Get the PID value from PID table. Returns:
        state (PID_table):  The selected PID table
        index (int):        The selected table index
        p (float):          The proportional value
        i (float):          The integral value
        d (float):          The derivative value

        Args:
            state (PID_table): The PID table state (0-3)
            index (int): The table index (0-7)

        Raises:
            ValueError: If index is out of range
            ValueError: If state is invalid

        Returns:
            (int, int, float, float, float): PID tuple
        """
        if isinstance(state, PID_table):
            if index >= 0 and index < 8:
                pid = self._controller._send_command(
                    f'TEMP:GPID {state.value},{int(index)}').split(',')
                state = PID_table(int(pid[0]))
                index = int(pid[1])
                temp = float(pid[2])
                p = float(pid[3])
                i = float(pid[4])
                d = float(pid[5])
                return state, index, temp, p, i, d
            else:
                raise ValueError('Index is out of range')
        else:
            raise ValueError('State is invalid')

    def set_pid(self, state, index, temp, p, i, d):
        """Set the PID value in the specified PID table

        Args:
            state (PID_table):  The selected PID table
            index (int):        The selected table index
            p (float):          The proportional value
            i (float):          The integral value
            d (float):          The derivative value

        Raises:
            ValueError: If PID values are invalid
            ValueError: If temperature value is out of range
            ValueError: If index is out of range
            ValueError: If state is invalid
        """
        if isinstance(state, PID_table):
            if index >= 0 and index < 8:
                max, min = self.get_operation_range()
                if temp >= min and temp <= max:
                    if p > 0 and i >= 0 and d >= 0:
                        self._controller._send_command(
                            f'TEMP:SPID {state.value},{int(index)},'
                            f'{temp},{p},{i},{d}',
                            False)
                    else:
                        raise ValueError('PID value(s) are invalid')
                else:
                    raise ValueError('Temperature value is out of range')
            else:
                raise ValueError('Index is out of range')
        else:
            raise ValueError('State is invalid')

    def get_cooling_heating_status(self):
        """Return the temperature control mode of the controller.

        Returns:
            (temperature_mode): Enum that corresponds to the selected
                                temperature mode.
        """
        status = self._controller._send_command('TEMP:CHSW?')
        return temperature_mode(int(status))

    def set_cooling_heating_status(self, status):
        """Set the temperature control mode of the controller.

        Args:
            status (temperature_mode, optional): Enum that corresponds to the
                                                 selected temperature mode.

        Raises:
            ValueError: If temperature mode is invalid.
        """
        if isinstance(status, temperature_mode):
            self._controller._send_command(f'TEMP:CHSW {status.value}', False)
        else:
            raise ValueError('Temperature mode is invalid')

    def get_ramp_rate_range(self):
        """Get the range of the ramp rate for the controller:
        max (float): Maximum rt value (°C/minute).
        min (float): Minimum rt value (°C/minute).
        limit_value (float): Limit value for alternate rt range (°C/minute).
        limit_max (float): Maximum rt value at limit (°C/minute).
        limit_min (float): Minimum rt value at limit (°C/minute).

        Returns:
            (float, float, float, float, float):    Tuple about the ramp rate
                                                    range of the controller.
        """
        range_raw = self._controller._send_command('TEMP:RTR?')
        range = range_raw.split(',')
        max = float(range[0])
        min = float(range[1])
        limit_value = float(range[2])
        limit_max = float(range[3])
        limit_min = float(range[4])
        return max, min, limit_value, limit_max, limit_min

    def get_stage_range(self):
        """Get the stage temperature range.

        Returns:
            (float, float): Tuple of max and min stage temperatures.
        """
        max, min = self._controller._send_command('TEMP:SRAN?').split(',')
        return float(max), float(min)

    def get_operation_range(self):
        """Get the operation temperature range.
        max (float): The maximum stage operation temperature.
        min (float): The minimum stage operation temperature.

        Returns:
            (float, float): Tuple of max and min operation temperatures.
        """
        max, min = self._controller._send_command('TEMP:RANG?').split(',')
        return float(max), float(min)

    def set_operation_range(self, max, min):
        """Set the operation temperature range.

        Args:
            max (float): The maximum stage operation temperature.
            min (float): The minimum stage operation temperature.

        Raises:
            ValueError: If provided range is out of stage temperature range
            ValueError: If the max value is smaller than the min value
        """
        if min <= max:
            smax, smin = self.get_stage_range()
            if min >= smin and max <= smax:
                self._controller._send_command(f'TEMP:RANG {max},{min}', False)
            else:
                raise ValueError('Operation temperature range is out of '
                                 'stage temperature range')
        else:
            raise ValueError('max is smaller than min')

    def get_default_operation_range(self):
        """Get the default operation temperature range.

        Returns:
            (float, float): Tuple of max and min default
                            operation temperatures.
        """
        max, min = self._controller._send_command('TEMP:DRAN?').split(',')
        return float(max), float(min)

    def get_system_status(self):
        """Get the current system status.

        Returns:
            system_status: The current system status.
        """
        return system_status(int(self._controller._send_command('TEMP:STAT?')))

    def get_serial_number(self):
        """Get the serial number.

        Returns:
            str: The serial number of the device.
        """
        return self._controller._send_command('TEMP:SNUM?').strip()

    def get_set_point_temperature(self):
        """Get the Target Set Point (TSP) temperature.

        Returns:
            float: The set point temperature in °C.
        """
        return float(self._controller._send_command('TEMP:SPO?'))

    def get_ramp_rate(self):
        """Get the Ramp Rate (RT).

        Returns:
            float: The ramp rate in °C/minute.
        """
        return float(self._controller._send_command('TEMP:RAT?'))

    def get_power(self):
        """Get the current Power Percent (PP).

        Returns:
            float: The power percent.
        """
        return float(self._controller._send_command('TEMP:POW?'))

    def get_powerboard_temperature(self):
        """Get the temperature of the powerboard RTD.

        Returns:
            float: The RTD temperature in °C.
        """
        return float(self._controller._send_command('TEMP:TP?'))

    def get_error(self):
        """Get the current error (see SCPI manual for more details).

        Returns:
            int: The current error code.
        """
        return int(self._controller._send_command('TEMP:ERR?'))

    def get_operating_slave(self):
        """Get the current operating slave.
        Operating slaves are 1 indexed, up to a maximum of 4.

        Returns:
            int: The number of the current operating slave.
        """
        return int(self._controller._send_command('TEMP:OPSL?'))

    def set_operating_slave(self, slave):
        """Set the current operating slave.
        Operating slaves are 1 indexed, up to a maximum of 4.

        Args:
            slave (int): The number of the operating slave.

        Raises:
            ValueError: If invalid number provided based on slave count.
        """
        if slave >= 1 and slave <= self.get_slave_count():
            self._controller._send_command(f'TEMP:OPSL {int(slave)}', False)
        else:
            raise ValueError('Invalid operating slave number')

    def get_slave_count(self):
        """Get the number of slaves connected to the current controller.

        Returns:
            int: The number of slaves connected.
        """
        return int(self._controller._send_command('TEMP:SLAV?'))

    def purge(self, delay, hold):
        """Complete a gas purge on the device.

        Args:
            delay (float):  Amount of time to delay before performing the
                            purge in seconds.
            hold (float):   Amount of time to hold the gas purge in seconds.

        Raises:
            ValueError: If hold value is not greater than 0
            ValueError: If delay value is not greater than or equal to 0
        """
        if delay >= 0:
            if hold > 0:
                self._controller._send_command(f'TEMP:PURG {delay},{hold}', False)
            else:
                raise ValueError('Hold must be greater than 0')
        else:
            raise ValueError('Delay is less than 0')

    def get_pv_unit_type(self):
        """Get the unit type of the Process Variable (PV).

        Returns:
            unit: Enum representing the unit type.
        """
        return unit(int(self._controller._send_command('TEMP:TCUN?')))

    def get_mv_unit_type(self):
        """Get the unit type of the Monitor Value (MV).

        Returns:
            unit: Enum representing the unit type.
        """
        return unit(int(self._controller._send_command('TEMP:TMUN?')))

    def get_precision(self):
        """Get the decimal precision of the Process Variable (PV)
        and Monitor Value (MV). Returns a tuple of both values:
        pv_precision (int): decimal precision of PV
        mv_precision (int): decimal precision of MV

        Returns:
            (int, int): Tuple of PV and MV precision
        """
        precision = self._controller._send_command('TEMP:PREC?').split(',')
        pv_precision = precision[0]
        mv_precision = precision[1]
        return pv_precision, mv_precision