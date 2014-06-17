import u12
import datetime
import time
import h5py


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
    Required parameters: 
        labjack    : labjack.Labjack instance
        battery_id : (string) battery id; this will be the name of the hdf5 output file of test data
    Optional parameters:
        v_supply            : default 5.0
        ljport_Vbatt        : default 0
        ljport_Isrc_monitor : default 1
        sink_params         : default dict( Von=2.19, Voff=0.0, ljport=0 ) # gives 3 mA, 0.2 C current on my setup
        source_params       : default dict( Von=4.1, Voff=None, ljport=1 ) # gives 7 mA, 0.5 C current on my setup
        battery_limits      : default dict(Vmin=2.9, Vmax=4.2)             # Li-poly
        sample_interval     : default 10 seconds
    """
    def __init__(self, labjack, battery_id, v_supply=5.0, ljport_Vbatt=0, ljport_Isrc_monitor=1,
            sink_params  =dict( Von=2.19, Voff=0.0, ljport=0 ),
            source_params=dict( Von=4.1, Voff=None, ljport=1 ),
            battery_limits=dict(Vmin=2.9, Vmax=4.2, num_cycles=300),
            sample_interval=10.0
            ):
        assert type(labjack)       == Labjack

        self.labjack               = labjack
        self.battery_id            = battery_id
        self.fname                 = "testdata_"+battery_id+".hdf5"
        self.ljport_Isink          = sink_params['ljport']
        self.ljport_Isrc           = source_params['ljport']
        self.ljport_Vbatt          = ljport_Vbatt
        self.ljport_Isrc_monitor   = ljport_Isrc_monitor
        self.sample_interval       = sample_interval

        self.sink_v_on             = sink_params['Von']
        self.sink_v_off            = sink_params['Voff']
        self.source_v_on_max       = source_params['Von']
        self.source_v_on           = self.source_v_on_max
        self.source_v_off          = v_supply if source_params['Voff'] is None else source_params['Voff']

        self.voltage_min           = battery_limits['Vmin']
        self.voltage_max           = battery_limits['Vmax']
        self.max_cycles            = battery_limits['num_cycles']
        self.cycle                 = 1

        # I know I shouldn't hard code this...
        self.charge_resistor       = 40.6
        self.power_source_voltage  = 5.029
        self.source_voltage_cutoff = self.power_source_voltage-0.03*15e-3*self.charge_resistor
        self.test_start_date       = datetime.datetime.now()
        self.test_start_time       = time.time()
        self.test_time             = [0.0]
        self.test_voltage          = [self.get_voltage()]

        self.init_file()


    def constant_current(self):
        while self.get_voltage() < self.voltage_max:
            self.dt = time.time()-test_start_time
            v  = self.get_voltage()
            self.test_time.append(dt)
            self.test_voltage.append(v)
            self.save("charging")
            print "charging, battery {0}: {1} V and current source: {2} V".format(self.battery_id,v,self.labjack.get_v(1))
            time.sleep(self.sample_interval)

    def _set_voltages(self, sink, source):
        """ Set voltages of the two analog output ports """
        v1, v2 = (sink, source) if self.ljport_Isink == 0 else (source, sink)
        self.labjack.set_v(v1, v2)

    def off(self):
        """ Turn both sink and source off. """
        self._set_voltages(self.sink_v_off, self.source_v_off)

    def sink_on(self):
        """ Turn the current sink on and source off. """
        self._set_voltages(self.sink_v_on, self.source_v_off)

    def source_on(self, reset=True):
        """ Turn the current source on and sink off. """
        if reset: self.source_v_on = self.source_v_on_max
        self._set_voltages(self.sink_v_off, self.source_v_on)

    def source_reduce(self):
        """ Reduce the source current incrementally. """
        self.source_v_on += 0.005 # higher voltage means less current
        print "Source voltage changed to: {0} V".format(self.source_v_on)
        self.source_on(reset=False)

    def charge(self):
        """ Charge the battery using a PNP current source. """
        # first the constant-current portion
        self.source_on()
        self.constant_current()

        # then the "constant voltage" section, which is actually a sequence
        # of constant current sections of decreasing current
        while self.get_source_voltage() < self.source_voltage_cutoff:
            self.source_reduce()
            self.constant_current()

    def discharge(self):
        """ Discharge the battery using a NPN current sink. """
        self.sink_on()
        while self.get_voltage() > self.voltage_min:
            dt = time.time()-self.test_start_time
            v  = self.get_voltage()
            self.test_time.append(dt)
            self.test_voltage.append(v)

            self.save("discharging")
            print "discharging, battery voltage is: {0}".format(v)
            time.sleep(self.sample_interval)

    def get_voltage(self):
        return self.labjack.get_v(self.ljport_Vbatt)

    def get_source_voltage(self):
        return self.labjack.get_v(self.ljport_Isrc_monitor)

    def save(self, description):
        num_points = len(self.test_voltage)
        with h5py.File(self.fname) as f:
            dset_time     = f['time']
            dset_type     = f['type']
            dset_cycle    = f['cycle']
            dset_voltage  = f['voltage']
            dset_time.resize((num_points,))
            dset_type.resize((num_points,))
            dset_cycle.resize((num_points,))
            dset_voltage.resize((num_points,))
            dset_time[-1]     = self.test_time[-1]
            dset_type[-1]     = description
            dset_cycle[-1]    = self.cycle
            dset_voltage[-1]  = self.test_voltage[-1]

    def init_file(self):
        with h5py.File(self.fname) as f:
            dt = h5py.special_dtype(vlen=str)
            num_points      = 1
            dset_time       = f.create_dataset('time',    (num_points,), maxshape=(None,), dtype=dt, compression="gzip")
            dset_type       = f.create_dataset('type',    (num_points,), maxshape=(None,), dtype=dt, compression="gzip")
            dset_cycle      = f.create_dataset('cycle',   (num_points,), maxshape=(None,), compression="gzip")
            dset_voltage    = f.create_dataset('voltage', (num_points,), maxshape=(None,), compression="gzip")
            dset_time[:]    = self.test_time[-1]
            dset_type[:]    = "Starting test"
            dset_cycle[:]   = self.cycle
            dset_voltage[:] = self.test_voltage[-1]


    def run_test(self):
        print "battery voltage before load is: {0}".format(self.get_voltage())

        for i in range(self.max_cycles):
            self.discharge()
            self.charge()
            self.off()
            self.cycle += 1
            print "Done with cycle."

        print "Done with test."


if __name__ == "__main__":
    d = Labjack()
    print "Voltage measured on ADC input 0 is {0} V.".format(d.get_v(0))
    d.close()
