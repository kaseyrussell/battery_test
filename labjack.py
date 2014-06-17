import u12


class Labjack(object):
    """ labjack class provides methods for using the LabJack USB device.
    """
    def __init__(self):
        self.device = u12.U12()
        print "Loaded a LabJack U12. Remember to close() it when you're done."

    def get_v(self, analog_in_port):
        """ Get the voltage (in volts) at the specified analog input port. """
        return self.device.eAnalogIn(analog_in_port)['voltage']

    def set_v(self, volts_AO0, volts_AO1):
        """ Set the voltage (in volts) at both of the analog output ports. """
        self.device.eAnalogOut(volts_AO0, volts_AO1)

    def close(self):
        """ Disconnects from the device. """
        self.device.close()
        print "Closed LabJack."


class BatteryTest(object):
    """ Parameters for transistor-based current sinks and sources. 
    Required parameters: sink_params, source_params, labjack
    Optional parameters:
        v_supply    : default 5.0
        outp_sink   : default 0
        outp_src    : default 1
        inp_battery : default 0
        inp_src_v   : default 1
    """
    def __init__(self, sink_params, source_params, labjack,
            v_supply=5.0, outp_sink=0, outp_src=1, inp_battery=0, inp_src_v=1):
        assert type(sink_params)   == dict
        assert type(source_params) == dict
        assert type(labjack)       == Labjack

        self.labjack     = labjack
        self.outp_sink   = outp_sink
        self.outp_src    = outp_src
        self.inp_battery = inp_battery
        self.inp_src_v   = inp_src_v

        self.sink_current    = sink_params['current']
        self.sink_resistance = sink_params['resistance']
        sink_diode           = 0.78
        self.sink_v_on       = self.sink_current*self.sink_resistance + sink_diode
        self.sink_v_off      = 0.0

        if "current" in source_params.keys():
            self.source_current    = source_params['current']
            self.source_resistance = source_params['resistance']
            source_diode           = 0.6
            self.source_v_on       = v_supply - self.source_current*self.source_resistance - source_diode
            self.source_v_off      = v_supply
        elif "voltage" in source_params.keys():
            self.source_v_on       = source_params['voltage']
            self.source_v_off      = v_supply
        else:
            raise ValueError("Need to specify proper source_params parameters.")


    def _set_voltages(self, sink, source):
        """ Set voltages of the two analog output ports """
        v1, v2 = (sink, source) if self.outp_sink == 0 else (source, sink)
        self.labjack.set_v(v1, v2)

    def off(self):
        """ Turn both sink and source off. """
        self._set_voltages(self.sink_v_off, self.source_v_off)

    def sink_on(self):
        """ Turn the current sink on and source off. """
        self._set_voltages(self.sink_v_on, self.source_v_off)

    def source_on(self, source_v=None):
        """ Turn the current source on and sink off. """
        if source_v is None: source_v = self.source_v_on
        self._set_voltages(self.sink_v_off, source_v)

    def charge(self):
        self.source_on()

    def discharge(self):
        self.sink_on()

    def get_voltage(self):
        return self.labjack.get_v(self.inp_battery)

    def get_source_voltage(self):
        return self.labjack.get_v(self.inp_src_v)


if __name__ == "__main__":
    d = Labjack()
    print "Voltage measured on ADC input 0 is {0} V.".format(d.get_v(0))
    d.close()
