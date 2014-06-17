""" Test a single battery through repeated cycling.
This assumes:

1) Measuring battery voltage directly using the analog input ain_batt

2) A current sink attached to the battery controlled by the analog out outp_sink

3) A current source attached to the battery controlled by analog out outp_src

This uses the Labjack and BatteryTest classes from the labjack module.

KJR, GoodLux Tech., June 2014
"""
from __future__ import division
import labjack
import matplotlib.pyplot as plt
import datetime
import time
import sys

d   = labjack.Labjack()

if not "id=" in sys.argv[1]:
    raise ValueError("Need 'id=' argument to specify the ID number of the battery under test.")
battery_id = sys.argv[1].split("id=")[-1].strip()

def save(dt,v,date,cycle,charge_or_discharge):
    #TODO: implement hdf5 save
    pass
    payload = {
        "test_time": dt, 
        "voltage": v, 
        "battery_id": battery_id, 
        "time": "{0}".format(date),
        "cycle_number": cycle,
        "charge_or_discharge": charge_or_discharge}


def constant_current(test_time, test_voltage, cycle):
    while battery_test.get_voltage() < voltage_max:
        dt = time.time()-test_start_time
        v  = battery_test.get_voltage()
        test_time.append(dt)
        test_voltage.append(v)
        save(dt, v, datetime.datetime.now(), cycle, "charging")
        print "charging, battery: {0} V and current source: {1} V".format(v, d.get_v(1))
        time.sleep(10)

sink_params   = dict( current=3.0e-3, resistance=470.0 )
source_params = dict( voltage=4.1 ) # 7.5 mA, ~0.5C
battery_test  = labjack.BatteryTest(sink_params, source_params, d)
battery_test.off()

voltage_min = 2.9
voltage_max = 4.2
charge_resistor = 40.6
power_source_voltage  = 5.029
 # this is the voltage dropped across the 40 Ohm resistor going to Isrc
source_voltage_cutoff = power_source_voltage-0.03*15e-3*charge_resistor


test_start_date = datetime.datetime.now()
test_start_time = time.time()
test_time       = [0.0]
test_voltage    = [battery_test.get_voltage()]


print "battery voltage before load is: {0}".format(battery_test.get_voltage())
cycle = 0

while True:
    battery_test.sink_on()
    while battery_test.get_voltage() > voltage_min:
        dt = time.time()-test_start_time
        v  = battery_test.get_voltage()
        test_time.append(dt)
        test_voltage.append(v)

        save(dt, v, datetime.datetime.now(), cycle, "discharging")
        print "discharging, battery voltage is: {0}".format(v)
        time.sleep(10)

    save(dt, v, datetime.datetime.now(), cycle, "switching to charge")
    battery_test.source_on()

    # first the constant-current portion
    constant_current(test_time, test_voltage, cycle)

    # then the "constant voltage" section, which is actually a sequence
    # of constant current sections of decreasing current
    while battery_test.get_source_voltage() < source_voltage_cutoff:
        source_v += 0.005 # higher voltage means less current
        print "Source voltage changed to: {0} V".format(source_v)
        battery_test.source_on(source_v=source_v)
        constant_current(test_time, test_voltage)


    battery_test.off()

    cycle += 1

save(dt, v, datetime.datetime.now(), cycle, "Done with test.")

d.close()

