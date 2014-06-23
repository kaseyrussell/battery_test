""" Module for using a LabJack U12 to test Li-poly batteries.
    Copyright 2014 Kasey J. Russell, GoodLux Technology
    Released under MIT license. See file LICENSE in this package.
"""
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
            (these default voltages are not accurate; it's just what the LabJack thinks it is outputting)
        ljport_Vbatt        : default 0
        ljport_Isrc_monitor : default 1
        sink_params         : default dict( Von=0.76, Voff=0.0, ljport=0 ) # gives 3 mA, 0.2 C current on my setup
        source_params       : default dict( Von=4.08, Voff=5.0, Vcutoff=4.30, ljport=1 ) # gives ~7 mA, 0.5 C current on my setup
        battery_limits      : default dict(Vmin=2.9, Vmax=4.2)             # Li-poly
        sample_interval     : default 10 seconds
        pulse_params        : default dict( Vsink=1.3, sample_interval=5.0, pulse_duration=30.0 ) # gives ~15 mA, 1C 
    """
    def __init__(self, labjack, battery_id="noname", ljport_Vbatt=0, ljport_Isrc_monitor=1,
            sink_params  =dict( Von=0.76, Voff=0.0, ljport=0 ),
            source_params=dict( Von=4.08, Voff=5.0, Vcutoff=4.30, ljport=1 ),
            battery_limits=dict(Vmin=2.9, Vmax=4.2, num_cycles=300),
            sample_interval=30.0,
            pulse_params=dict( Vsink=1.3, sample_interval=10.0, pulse_duration=30.0 )
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
        self.source_v_off          = source_params['Voff']

        self.voltage_min           = battery_limits['Vmin']
        self.voltage_max           = battery_limits['Vmax']
        self.max_cycles            = battery_limits['num_cycles']
        self.cycle                 = 1

        self.source_voltage_cutoff = source_params['Vcutoff']
        self.test_start_date       = datetime.datetime.now()
        self.test_start_time       = time.time()
        self.test_time             = [0.0]
        self.test_voltage          = [self.get_voltage()]

        self.sink_v_pulse          = pulse_params['Vsink']
        self.pulse_duration        = pulse_params['pulse_duration']
        self.sample_interval_pulse = pulse_params['sample_interval']

    def constant_current(self):
        while self.get_voltage() < self.voltage_max:
            dt = time.time()-self.test_start_time
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

    def sink_on(self, pulse=False):
        """ Turn the current sink on and source off. """
        sink_v = self.sink_v_on if not pulse else self.sink_v_pulse
        self._set_voltages(sink_v, self.source_v_off)

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

    def discharge(self, pulse=False):
        """ Discharge the battery using a NPN current sink. 
        If pulse is True, pulse the current to a higher value (self.sink_v_pulse)
        for time self.pulse_duration (50 percent duty cycle),
        with sampling interval self.sample_interval_pulse during the pulse
        """
        self.sink_on()
        time_pulse = time.time()
        pulse_is_on   = False
        while self.get_voltage() > self.voltage_min:
            dt = time.time()-self.test_start_time
            v  = self.get_voltage()
            self.test_time.append(dt)
            self.test_voltage.append(v)

            print "discharging, battery voltage is: {0}".format(v)
            if pulse_is_on:
                self.save("discharging-pulsed")
            else:
                self.save("discharging")

            if pulse:
                if time.time() - time_pulse > self.pulse_duration:
                    time_pulse = time.time()
                    if pulse_is_on:
                        self.sink_on( pulse=False )
                        pulse_is_on = False
                    else:
                        self.sink_on( pulse=True )
                        pulse_is_on = True
                sleep_time = self.sample_interval_pulse if pulse_is_on else self.sample_interval
                time.sleep(sleep_time)
            else:
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
            dt              = h5py.special_dtype(vlen=str)
            num_points      = 1
            dset_time       = f.create_dataset('time',    (num_points,), maxshape=(None,), compression="gzip")
            dset_type       = f.create_dataset('type',    (num_points,), maxshape=(None,), dtype=dt, compression="gzip")
            dset_cycle      = f.create_dataset('cycle',   (num_points,), maxshape=(None,), compression="gzip")
            dset_voltage    = f.create_dataset('voltage', (num_points,), maxshape=(None,), compression="gzip")
            dset_time[:]    = self.test_time[-1]
            dset_type[:]    = "Starting test"
            dset_cycle[:]   = self.cycle
            dset_voltage[:] = self.test_voltage[-1]

    def run_test(self):
        print "battery voltage before load is: {0}".format(self.get_voltage())

        self.init_file()

        for i in range(self.max_cycles):
            pulse = True if i%2 == 0 else False # pulse on every other cycle, starting on first.
            print "pulse flag is set to {0}".format(pulse)
            self.discharge( pulse=pulse )
            self.off()
            self.charge()
            self.off()
            self.cycle += 1
            print "Done with cycle."

        print "Done with test."


class MUXTest(BatteryTest):
    """ Use a Labjack to set the proper output port of a MUX (HEF4067B) to
    select the desired battery.
    Required:
        labjack device instance
        battery_list : list of dicts with battery ids and mux ports like this:
            [dict( id="BBM04", mux=0 ), ...]
    Optional:
        ljports : default dict(A0=0, A1=1, A2=2, A3=3), dictionary associatng the 
            address inputs of the MUX (A0-A3) with the IO ports of the LabJack.
    """
    def __init__(self, labjack, battery_list, ljports=dict(A0=0, A1=1, A2=2, A3=3), **kwargs):
        self.labjack   = labjack
        self.batteries = battery_list
        self.ljports   = ljports
        self.dt        = 0.0
        self.make_tests()
        super(MUXTest, self).__init__(self.labjack, **kwargs)

    def make_tests(self):
        """ Make a separate test for each battery, but we won't run them
        individually, we'll run the MUXTest. """
        self.tests = []
        for battery in self.batteries:
            self.tests.append(BatteryTest(self.labjack, battery['id']))

    def select_battery(self, battery_id):
        """ Use the battery_id to get the right MUX port, then set it
        accordingly. """
        mux_outport = None
        for battery in self.batteries:
            if battery['id'] == battery_id:
                mux_outport = battery['mux']
        assert mux_outport is not None, "Couldn't identify the proper mux output port."

        # now find the MUX input combo to give us this mux output
        A3 = 0 if mux_outport <= 7 else 1
        A2 = 0 if (mux_outport <= 3) or (mux_outport in range(8,12)) else 1
        A1 = 0 if mux_outport in [0,1,4,5,8,9,12,13] else 1
        A0 = 0 if mux_outport % 2 == 0 else 1

        # now set the ljport sequence to give us that MUX input combo
        p = self.ljports
        self.labjack.device.eDigitalOut(channel=p['A3'], state=A3, writeD=0)
        self.labjack.device.eDigitalOut(channel=p['A2'], state=A2, writeD=0)
        self.labjack.device.eDigitalOut(channel=p['A1'], state=A1, writeD=0)
        self.labjack.device.eDigitalOut(channel=p['A0'], state=A0, writeD=0)
        time.sleep(0.05) # give it some time to settle. 50ms should be plenty.

    def measure_all_batteries(self):
        """ get test voltages from each battery """
        bv = []
        for b,t in zip(self.batteries,self.tests):
            self.select_battery(b['id'])
            t.test_time.append(self.dt)
            v = t.get_voltage()
            t.test_voltage.append(v)
            bv.append(v)
        print "Battery voltages: {0}".format(bv)

    def save(self, description):
        """ Save each file separately. """
        for test in self.tests:
            test.save(description)

    def init_file(self):
        """ Initialize separate files for the different batteries. """
        for test in self.tests:
            test.init_file()

    def get_voltage_least_charged(self):
        """ Get the voltage of the least-charged battery """
        v = []
        for b in self.batteries:
            self.select_battery(b['id'])
            v.append(self.get_voltage())
        return min(v)

    def get_voltage_most_charged(self):
        """ Get the voltage of the most-charged battery """
        v = []
        for b in self.batteries:
            self.select_battery(b['id'])
            v.append(self.get_voltage())
        return max(v)

    def constant_current(self):
        while self.get_voltage_least_charged() < self.voltage_max:
            self.dt = time.time()-self.test_start_time
            self.measure_all_batteries()
            self.save("charging")
            print "Charging, PNP voltage is: {0} V".format(self.get_source_voltage())
            time.sleep(self.sample_interval)

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

    def discharge(self, pulse=False):
        """ Discharge the battery using a NPN current sink. 
        If pulse is True, pulse the current to a higher value (self.sink_v_pulse)
        for time self.pulse_duration (50 percent duty cycle),
        with sampling interval self.sample_interval_pulse during the pulse
        """
        self.sink_on()
        time_pulse = time.time()
        pulse_is_on   = False
        while self.get_voltage_most_charged() > self.voltage_min:
            self.dt = time.time()-self.test_start_time
            self.measure_all_batteries()
            if pulse_is_on:
                self.save("discharging-pulsed")
                print "PULSING."
            else:
                self.save("discharging")
                print "NOT PULSING"

            if pulse:
                if time.time() - time_pulse > self.pulse_duration:
                    time_pulse = time.time()
                    if pulse_is_on:
                        self.sink_on( pulse=False )
                        pulse_is_on = False
                    else:
                        self.sink_on( pulse=True )
                        pulse_is_on = True
                sleep_time = self.sample_interval_pulse if pulse_is_on else self.sample_interval
                time.sleep(sleep_time)
            else:
                time.sleep(self.sample_interval)


if __name__ == "__main__":
    d = Labjack()
    print "Voltage measured on ADC input 0 is {0} V.".format(d.get_v(0))
    d.close()
